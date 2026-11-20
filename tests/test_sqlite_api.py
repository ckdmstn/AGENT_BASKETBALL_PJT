from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.database import Database, get_database
from backend.main import app, get_agent_runner
from backend.config import Settings
from tests.test_agent import FakeLLM, FakeTools, analysis


PLAN = {
    'session_id': 'session-a',
    'match_id': 'one',
    'home_team': '서울 삼성',
    'away_team': '서울 SK',
    'venue_name': '잠실학생체육관',
    'start_at': '2026-11-19T10:00:00Z',
    'end_at': '2026-11-19T21:00:00+09:00',
    'note': '직관 계획',
}


@pytest.fixture
def api(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    app.dependency_overrides[get_database] = lambda: db
    get_agent_runner.cache_clear()
    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_database, None)
        get_agent_runner.cache_clear()


def test_database_initializes_idempotently(api):
    _, db = api
    db = Database(db.path)
    with db.connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {'plans', 'sessions', 'agent_events'} <= tables
        assert conn.execute('PRAGMA busy_timeout').fetchone()[0] > 0


def test_plan_crud_preserves_fields(api):
    client, _ = api
    response = client.post('/api/plans', json=PLAN)
    assert response.status_code == 201
    new = response.json()['plan']
    assert new['start_at'] == '2026-11-19T19:00:00+09:00'
    assert new['game_date'] == '2026-11-19'
    assert new['created_at'] == new['updated_at']
    path = f"/api/plans/{new['id']}"
    assert client.get('/api/plans').json() == [new]
    assert client.get(path).json() == new

    result = client.patch(path, json={'note': None})
    assert result.status_code == 200
    patched = result.json()['plan']
    assert patched['updated_at'] >= new['updated_at']
    assert {**patched, 'note': new['note'], 'updated_at': new['updated_at']} == new
    assert result.json()['overlapping_plan_ids'] == []
    assert result.json()['overlap_warnings'] == []
    assert client.delete(path).status_code == 204
    assert client.get('/api/plans').json() == []


@pytest.mark.parametrize('method', ['get', 'patch', 'delete'])
def test_plan_not_found(api, method):
    client, _ = api
    options = {'json': {'note': '수정'}} if method == 'patch' else {}
    assert client.request(method, '/api/plans/999', **options).status_code == 404


@pytest.mark.parametrize('changes', [
    {'start_at': '2026-02-30T19:00:00+09:00'}, {'start_at': '2026-11-19T19:00:00'},
    {'start_at': '9999-12-31T23:00:00Z'},
    {'start_at': '2026-11-19'}, {'start_at': 1795100000}, {'start_at': '1795100000'},
    {'end_at': '2026-11-19T19:00:00+09:00'}, {'home_team': '  '}, {'unexpected': 'private-input'},
])
def test_invalid_plan_input_is_not_echoed(api, changes):
    client, _ = api
    response = client.post('/api/plans', json={**PLAN, **changes})
    assert response.status_code == 422
    assert 'private-input' not in response.text


def test_invalid_patch_does_not_write(api):
    client, _ = api
    plan = client.post('/api/plans', json=PLAN).json()['plan']
    path = f"/api/plans/{plan['id']}"
    for change in ({'start_at': '2026-11-19T22:00:00+09:00'}, {'venue_name': None}, {}):
        assert client.patch(path, json=change).status_code == 422
    assert client.get(path).json() == plan


def test_overlap_across_timezones_and_adjacent_plans(api):
    client, _ = api
    first = client.post('/api/plans', json=PLAN).json()['plan']
    adjacent = {**PLAN, 'start_at': '2026-11-19T12:00:00Z', 'end_at': '2026-11-19T13:00:00Z'}
    second = client.post('/api/plans', json=adjacent).json()
    assert second['overlapping_plan_ids'] == []
    path = f"/api/plans/{second['plan']['id']}"
    updated = client.patch(path, json={'start_at': '2026-11-19T11:00:00Z'}).json()
    assert updated['overlapping_plan_ids'] == [first['id']]
    assert updated['overlap_warnings']
    third = client.post('/api/plans', json=PLAN)
    assert third.status_code == 201
    assert third.json()['overlapping_plan_ids'] == [first['id'], second['plan']['id']]


def test_missing_end_time_is_reported_for_both_sides(api):
    client, _ = api
    created = client.post('/api/plans', json={**PLAN, 'end_at': None}).json()
    assert created['plan']['end_at'] is None
    assert created['overlapping_plan_ids'] == [] and created['overlap_warnings']
    known = client.post('/api/plans', json=PLAN).json()
    assert known['overlapping_plan_ids'] == [] and known['overlap_warnings']
    path = f"/api/plans/{known['plan']['id']}"
    assert client.patch(path, json={'end_at': None}).json()['plan']['end_at'] is None


def test_concurrent_create_checks_committed_overlap(api):
    client, _ = api
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post('/api/plans', json=PLAN), range(2)))
    assert [result.status_code for result in results] == [201, 201]
    assert sorted(len(result.json()['overlapping_plan_ids']) for result in results) == [0, 1]


def test_log_api_wiring_order_and_independent_delete(api, monkeypatch):
    client, db = api
    llm = FakeLLM([analysis(region='서울'), {'intent': 'follow_up'}, analysis(region='수원')])
    monkeypatch.setattr('backend.main.load_settings', Settings)
    monkeypatch.setattr('backend.agent.graph.JsonLLM', lambda _: llm)
    monkeypatch.setattr('backend.agent.graph.invoke', FakeTools())
    responses = []
    for sid in ('session-a', 'session-a', 'session-b'):
        response = client.post('/api/chat', json={'session_id': sid, 'message': '경기 추천'})
        assert response.status_code == 200
        responses.append(response.json())
    assert responses[1]['conditions']['region'] == '서울'
    listing = {row['session_id']: row for row in client.get('/api/logs').json()}
    assert listing['session-a']['run_count'] == 2
    assert listing['session-a']['event_count'] == sum(len(run['events']) for run in responses[:2])

    path = '/api/logs/session-a'
    runs = client.get(path).json()['runs']
    assert [run['run_id'] for run in runs] == [result['run_id'] for result in responses[:2]]
    for run in runs:
        assert [event['sequence_no'] for event in run['events']] == list(range(1, len(run['events']) + 1))
        assert run['events'][-1]['event_type'] == 'RUN_COMPLETED'
    assert client.patch(path, json={}).status_code == 405
    assert client.put(path, json={}).status_code == 405
    assert client.post('/api/plans', json=PLAN).status_code == 201
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == client.delete(path).status_code == 404
    assert client.get('/api/logs/session-b').status_code == 200
    assert len(client.get('/api/plans').json()) == 1
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 2

    assert client.get('/docs').status_code == 200
    paths = client.get('/openapi.json').json()['paths']
    assert set(paths['/api/plans/{plan_id}']) == {'get', 'patch', 'delete'}
    assert set(paths['/api/logs/{session_id}']) == {'get', 'delete'}
    assert '/api/chat' in paths
