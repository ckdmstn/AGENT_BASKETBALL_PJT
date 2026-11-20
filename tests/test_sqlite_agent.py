import json
import sqlite3
from contextlib import contextmanager

import pytest

from backend.agent.events import EventBus
from backend.agent.graph import AgentRunner
from backend.agent.llm import LLMError
from backend.agent.logging import LoggingAgent
from backend.agent.sessions import SQLiteSessions
from backend.config import Settings
from backend.database import Database
from tests.test_agent import FakeLLM, FakeTools, analysis


DATE = {'from_date': '2026-11-20', 'to_date': '2026-11-20'}
GRANT = '다른 팀도 괜찮아. 대체 날짜: 2026-11-20 허용해'


def make_agent(path, analyses, *, subscriber=None, llm=None):
    return AgentRunner(llm=llm or FakeLLM(analyses), tool_invoker=FakeTools(), settings=Settings(),
                       sessions=SQLiteSessions(Database(path)), event_subscriber=subscriber)


def test_restored_sessions_isolate_conditions_and_verified_permissions(tmp_path):
    path = tmp_path / 'test.sqlite3'
    first = make_agent(path, [analysis(preferred_team='LG', region='서울'), analysis(region='수원')])
    initial = first.run(GRANT, 'a')
    first.run('수원 경기 추천', 'b')
    assert initial.conditions.preferred_team == 'LG'
    assert initial.active_conditions.preferred_team is None

    follow_up = {'intent': 'follow_up', 'conditions': {'preferred_team': 'SK'}, 'changed_fields': ['preferred_team']}
    restored = make_agent(path, [follow_up, {'intent': 'follow_up'}])
    saved = restored.sessions.load('a')
    assert saved['summary'] == '추천 ID: one'
    assert saved['permissions'] == {'team': True, 'date_ranges': [DATE]}
    a = restored.run('팀만 SK로 바꿔 줘', 'a')
    b = restored.run('다시 찾아 줘', 'b')
    assert a.conditions.preferred_team == 'SK' and a.conditions.region == '서울'
    assert a.conditions.fallback_teams_allowed
    assert [item.model_dump(mode='json') for item in a.conditions.alternative_date_ranges] == [DATE]
    assert b.conditions.region == '수원' and not b.conditions.fallback_teams_allowed
    assert b.conditions.alternative_date_ranges == []


@pytest.mark.parametrize('stage', ['analyze', 'plan', None])
def test_revocations_survive_new_runner_and_optional_llm_failure(tmp_path, stage):
    class FailingLLM(FakeLLM):
        def complete(self, current_stage, payload, output_model):
            if stage == current_stage:
                raise LLMError('LLM_UPSTREAM_ERROR')
            return super().complete(current_stage, payload, output_model)

    path = tmp_path / 'test.sqlite3'
    initial = make_agent(path, [analysis(preferred_team='LG')])
    assert initial.run(GRANT, 'a').conditions.fallback_teams_allowed
    failing = make_agent(path, [], llm=FailingLLM([{'intent': 'follow_up'}]))
    withdrawn = failing.run('방금 허용은 취소해', 'a')
    assert bool(withdrawn.errors) == (stage is not None)
    restored = make_agent(path, [{'intent': 'follow_up'}])
    assert restored.sessions.load('a')['permissions'] == {'team': False, 'date_ranges': []}
    result = restored.run('다시 찾아 줘', 'a')
    assert result.replan_count == 0
    assert result.conditions.preferred_team == 'LG'
    assert not result.conditions.fallback_teams_allowed and result.conditions.alternative_date_ranges == []


def test_logging_is_structured_and_unsubscribes(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    secret = 'synthetic-api-secret'
    logger = LoggingAgent(db, Settings(llm_key=secret))
    bus = EventBus('session', 'run')
    bus.subscribe(logger)
    bus.publish('LLM_DECISION', node_name='analyze',
                payload={'reason': secret, 'intent': 'plan', 'changed_fields': [secret, 'region'],
                         'raw_message': 'private transcript'})
    bus.publish('TOOL_REQUESTED', tool_name='search_arena', payload={'arguments': {'api_key': secret}})
    bus.publish('TOOL_RESPONDED', tool_name='search_arena',
                payload={'ok': False, 'error_code': 'UPSTREAM_ERROR', 'traceback': 'raw traceback'})
    bus.unsubscribe(logger)
    bus.publish('RUN_COMPLETED')
    sensitive_bus = EventBus(secret, 'run')
    sensitive_bus.subscribe(logger)
    sensitive_bus.publish('RUN_COMPLETED')
    with db.connection() as conn:
        rows = [dict(row) for row in conn.execute('SELECT * FROM agent_events ORDER BY sequence_no')]
    assert [row['sequence_no'] for row in rows] == [1, 2, 3]
    assert [json.loads(row['payload']) for row in rows] == [
        {'intent': 'plan', 'changed_fields': ['region']}, {},
        {'ok': False, 'error_code': 'UPSTREAM_ERROR'},
    ]
    assert all(value not in repr(rows) for value in (secret, 'private transcript', 'raw traceback'))
    assert bus.events[-1].event_type == 'RUN_COMPLETED'


def test_logging_database_failure_does_not_interrupt_agent(tmp_path, monkeypatch):
    path = tmp_path / 'test.sqlite3'
    logger_db = Database(path)
    logger = LoggingAgent(logger_db, Settings())

    @contextmanager
    def broken_database(**_):
        raise sqlite3.OperationalError('raw exception text')
        yield

    monkeypatch.setattr(logger_db, 'connection', broken_database)
    agent = make_agent(path, [analysis(), analysis()], subscriber=logger)
    for subscriber in (logger, None):
        agent.event_subscriber = subscriber
        result = agent.run('경기 추천', 'a')
        assert len(result.recommendations) == 1
        assert result.errors == []
        assert result.events[-1]['event_type'] == 'RUN_COMPLETED'
        assert 'raw exception text' not in result.model_dump_json()
    with Database(path).connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM agent_events').fetchone()[0] == 0


def test_failed_run_event_keeps_only_safe_metadata(tmp_path):
    path = tmp_path / 'test.sqlite3'
    db = Database(path)
    logger = LoggingAgent(db, Settings())
    agent = make_agent(path, [RuntimeError('private exception text')], subscriber=logger)
    result = agent.run('private raw message', 'a')
    assert result.events[-1]['event_type'] == 'RUN_FAILED'
    with db.connection() as conn:
        rows = [dict(row) for row in conn.execute('SELECT * FROM agent_events ORDER BY sequence_no')]
    assert rows[-1]['event_type'] == 'RUN_FAILED'
    assert json.loads(rows[-1]['payload']) == {'replan_count': 0, 'recommendation_count': 0}
    assert 'private' not in repr(rows)
