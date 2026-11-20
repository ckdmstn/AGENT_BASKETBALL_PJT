"""Measure Task 14 paths without calling the unpublished KBL endpoints."""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from fastapi.testclient import TestClient

from backend.agent.graph import AgentRunner
from backend.agent.llm import JsonLLM
from backend.agent.logging import LoggingAgent
from backend.agent.sessions import SQLiteSessions
from backend.config import KST, Settings, load_settings
from backend.database import Database, get_database
from backend.main import app, get_agent_runner
from backend.tools.registry import invoke
from tests.test_agent import FakeLLM, FakeTools, analysis


def timed(metrics, key, function, *args):
    start = perf_counter()
    try:
        return function(*args)
    finally:
        metrics[key].append(round((perf_counter() - start) * 1000, 2))


class MeasuredLLM:
    def __init__(self, adapter, metrics):
        self.adapter = adapter
        self.metrics = metrics

    def complete(self, stage, payload, output_model):
        return timed(self.metrics, stage, self.adapter.complete, stage, payload, output_model)


def measure(client, database, settings, llm, tool, name, message):
    llm_ms, tool_ms = defaultdict(list), defaultdict(list)
    logging_ms = defaultdict(list)
    logging_agent = LoggingAgent(database, settings)

    def tools(tool_name, args, config):
        return timed(tool_ms, tool_name, tool, tool_name, args, config)

    def save_event(event):
        timed(logging_ms, 'event', logging_agent, event)

    runner = AgentRunner(
        llm=MeasuredLLM(llm, llm_ms), tool_invoker=tools, settings=settings,
        sessions=SQLiteSessions(database), event_subscriber=save_event,
    )
    app.dependency_overrides[get_agent_runner] = lambda: runner
    start = perf_counter()
    response = client.post('/api/chat', json={'message': message})
    total_ms = round((perf_counter() - start) * 1000, 2)
    response.raise_for_status()
    result = response.json()
    nodes = defaultdict(list)
    started_nodes = {}
    cached = 0
    for event in result['events']:
        if event['event_type'] == 'NODE_STARTED':
            started_nodes[event['node_name']] = datetime.fromisoformat(event['timestamp'])
        if event['event_type'] == 'NODE_COMPLETED':
            elapsed = datetime.fromisoformat(event['timestamp']) - started_nodes.pop(event['node_name'])
            nodes[event['node_name']].append(round(elapsed.total_seconds() * 1000, 2))
        if event['event_type'] == 'TOOL_RESPONDED' and event['payload'].get('cached'):
            cached += 1
    stored = client.get('/api/logs/' + result['session_id'])
    stored.raise_for_status()
    assert len(stored.json()['runs'][0]['events']) == len(result['events'])
    return {
        'scenario': name, 'http_ms': total_ms, 'agent_ms': result['elapsed_ms'],
        'outcome': result['events'][-1]['event_type'], 'replans': result['replan_count'],
        'recommendations': [item['match_id'] for item in result['recommendations']],
        'excluded': len(result['excluded']), 'errors': [error['code'] for error in result['errors']],
        'cached': cached, 'llm_ms': dict(llm_ms), 'tool_ms': dict(tool_ms),
        'node_ms': dict(nodes), 'logging_ms': round(sum(logging_ms['event']), 2),
    }


def mock_cases():
    alternatives = [{'from_date': f'2026-11-{day}', 'to_date': f'2026-11-{day}'} for day in (20, 21, 22)]
    return [
        ('normal', '서울 오후 2시 이후 강수확률 30% 이하 경기', analysis(region='서울', start_after='14:00',
           max_precipitation_probability_pct=30), FakeTools(), (1, 0, 0)),
        ('replan', '서울 LG 경기. LG 경기 없으면 다른 팀도 괜찮아', analysis(region='서울', preferred_team='LG',
           fallback_teams_allowed=True), FakeTools(), (1, 1, 0)),
        ('limit', 'LG 경기 없으면 다른 팀도 괜찮아. 대체 날짜: 2026-11-20,2026-11-21,2026-11-22 허용해',
           analysis(preferred_team='LG', alternative_date_ranges=alternatives), FakeTools([]), (0, 3, 1)),
        ('tool_failure', '서울 경기 강수확률 30% 이하', analysis(region='서울',
           max_precipitation_probability_pct=30), FakeTools(fail='get_weather'), (0, 0, 1)),
        ('greeting', '안녕하세요', {'intent': 'greeting'}, FakeTools(), (0, 0, 0)),
    ]


def live_probes(client, database):
    settings = load_settings()

    def no_kbl_or_other_tools(name, args, config):
        raise AssertionError('Greeting must not call a Tool')

    results = [measure(client, database, settings, JsonLLM(settings), no_kbl_or_other_tools,
                       'greeting', '안녕하세요') for _ in range(3)]
    for row in results:
        assert row['outcome'] == 'RUN_COMPLETED' and not row['errors'] and not row['tool_ms'], row
    now = datetime.now(KST)
    place_args = {'venue_name': '창원체육관', 'region_hint': '창원'}
    weather_args = {'lat': 35.2343, 'lon': 128.6625, 'date_time': (now + timedelta(hours=1)).isoformat()}
    probes = []
    for name, args in [('search_arena', place_args), ('get_weather', weather_args)]:
        timing = defaultdict(list)
        result = timed(timing, name, invoke, name, args, settings)
        evidence = {'tool': name, 'ms': timing[name][0], 'ok': result.ok,
                    'http_status': result.meta.http_status, 'service_code': result.meta.service_code,
                    'error': None if result.ok else result.error.code}
        if result.ok and name == 'get_weather':
            evidence.update(result.data.model_dump(mode='json'))
            query = result.meta.actual_query
            evidence['grid'] = [query.get('nx'), query.get('ny')]
        probes.append(evidence)
    return {'real_greeting': results, 'real_standalone_probes': probes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Make up to six GMS calls and one Kakao and KMA call each')
    args = parser.parse_args()
    with TemporaryDirectory() as directory, TestClient(app) as client:
        database = Database(Path(directory) / 'validation.sqlite3')
        app.dependency_overrides[get_database] = lambda: database
        try:
            if args.live:
                report = live_probes(client, database)
            else:
                rows = []
                settings = Settings()
                for _ in range(3):
                    for name, message, parsed, tool, expected in mock_cases():
                        row = measure(client, database, settings, FakeLLM([parsed]), tool, name, message)
                        assert row['outcome'] == 'RUN_COMPLETED', row
                        assert (len(row['recommendations']), row['replans'], len(row['errors'])) == expected, row
                        rows.append(row)
                report = {'mock': rows}
        finally:
            app.dependency_overrides.clear()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
