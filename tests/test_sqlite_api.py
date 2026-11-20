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


def test_plan_core_fields_update_and_preserve_identifiers_and_legacy_end(api):
    client, _ = api
    original = client.post('/api/plans', json={**PLAN, 'end_at': '2026-11-20T02:00:00+09:00'}).json()['plan']
    path = f"/api/plans/{original['id']}"
    changes = {'start_at': '2026-11-19T16:00:00Z', 'home_team': '개인 홈팀', 'away_team': '개인 원정팀',
               'venue_name': '개인 경기장', 'venue_address': '개인 주소', 'note': None}
    response = client.patch(path, json=changes)
    assert response.status_code == 200
    plan = response.json()['plan']
    assert plan['start_at'] == '2026-11-20T01:00:00+09:00' and plan['game_date'] == '2026-11-20'
    for key in ('home_team', 'away_team', 'venue_name', 'venue_address', 'note'):
        assert plan[key] == changes[key]
    for key in ('id', 'match_id', 'end_at', 'session_id', 'created_at'):
        assert plan[key] == original[key]
    assert response.json()['overlapping_plan_ids'] == []
    assert client.get(path).json() == plan
    assert client.get('/api/plans').json() == [plan]


@pytest.mark.parametrize('changes', [
    {'start_at': '2026-02-30T19:00:00+09:00'}, {'start_at': '2026-11-19T20:00:00'},
    {'start_at': '2026-11-19T21:01:00+09:00'}, {'home_team': '  '}, {'away_team': ''},
    {'venue_name': None}, {'unknown_field': 'text'},
])
def test_invalid_core_patch_preserves_row(api, changes):
    client, _ = api
    plan = client.post('/api/plans', json=PLAN).json()['plan']
    path = f"/api/plans/{plan['id']}"
    assert client.patch(path, json=changes).status_code == 422
    assert client.get(path).json() == plan


def test_plan_patch_changed_start_recomputes_conflicts(api):
    client, _ = api
    first = client.post('/api/plans', json={**PLAN, 'end_at': None}).json()['plan']
    second = client.post('/api/plans', json={**PLAN, 'match_id': 'other', 'end_at': None,
                                            'start_at': '2026-11-19T20:00:00+09:00'}).json()['plan']
    result = client.patch(f"/api/plans/{second['id']}", json={'start_at': first['start_at']}).json()
    assert result['overlapping_plan_ids'] == [first['id']]
    assert result['overlap_warnings'] == ['같은 시각에 시작하는 다른 경기 일정이 있습니다.']


def test_patch_match_id_keeps_available_identity_contract_and_blocks_collision(api):
    client, _ = api
    first = client.post('/api/plans', json=PLAN).json()['plan']
    second = client.post('/api/plans', json={**PLAN, 'match_id': 'other'}).json()['plan']
    path = f"/api/plans/{second['id']}"
    rejected = client.patch(path, json={'match_id': first['match_id'], 'note': 'must not save'})
    assert rejected.status_code == 409
    assert client.get(path).json() == second
    assert client.patch(path, json={'match_id': 'available'}).json()['plan']['match_id'] == 'available'


def test_overlap_across_timezones_and_adjacent_plans(api):
    client, _ = api
    first = client.post('/api/plans', json=PLAN).json()['plan']
    adjacent = {**PLAN, 'match_id': 'adjacent', 'start_at': '2026-11-19T12:00:00Z', 'end_at': '2026-11-19T13:00:00Z'}
    second = client.post('/api/plans', json=adjacent).json()
    assert second['overlapping_plan_ids'] == []
    path = f"/api/plans/{second['plan']['id']}"
    updated = client.patch(path, json={'start_at': '2026-11-19T11:00:00Z'}).json()
    assert updated['overlapping_plan_ids'] == [first['id']]
    assert updated['overlap_warnings']
    third = client.post('/api/plans', json={**PLAN, 'match_id': 'third'})
    assert third.status_code == 201
    assert third.json()['overlapping_plan_ids'] == [first['id'], second['plan']['id']]


def test_missing_end_time_still_blocks_duplicate_game(api):
    client, _ = api
    created = client.post('/api/plans', json={**PLAN, 'end_at': None}).json()
    assert created['plan']['end_at'] is None
    assert created['overlapping_plan_ids'] == [] and created['overlap_warnings'] == []
    known = client.post('/api/plans', json=PLAN)
    assert known.status_code == 409
    assert known.json() == {'detail': '이미 저장한 경기입니다. 저장한 계획에서 확인하거나 수정해 주세요.'}
    assert client.get('/api/plans').json() == [created['plan']]
    path = f"/api/plans/{created['plan']['id']}"
    assert client.patch(path, json={'end_at': None}).json()['plan']['end_at'] is None


def test_omitted_end_and_note_default_to_null(api):
    client, _ = api
    data = {key: value for key, value in PLAN.items() if key not in ('end_at', 'note')}
    response = client.post('/api/plans', json=data)
    assert response.status_code == 201
    plan = response.json()['plan']
    assert plan['end_at'] is None and plan['note'] is None
    assert client.get(f"/api/plans/{plan['id']}").json() == plan


def test_duplicate_reasons_are_prioritized_and_ids_are_unique(api):
    client, _ = api
    same_game = client.post('/api/plans', json={**PLAN, 'match_id': 'legacy-same-start',
                                              'end_at': '2026-11-19T20:00:00+09:00'}).json()['plan']
    same_start = client.post('/api/plans', json={**PLAN, 'match_id': 'different',
                                               'start_at': '2026-11-19T19:00:00+09:00', 'end_at': None}).json()['plan']
    legacy = client.post('/api/plans', json={**PLAN, 'match_id': 'legacy',
                                           'start_at': '2026-11-19T18:00:00+09:00'}).json()['plan']
    response = client.post('/api/plans', json={**PLAN, 'end_at': None})
    assert response.status_code == 201
    assert response.json()['overlapping_plan_ids'] == [same_game['id'], same_start['id'], legacy['id']]
    assert response.json()['overlap_warnings'] == [
        '같은 시각에 시작하는 다른 경기 일정이 있습니다.',
        '기존 일정의 시간 범위와 겹칠 수 있습니다.',
    ]


def test_same_match_id_is_blocked_even_when_start_changed(api):
    client, _ = api
    previous = client.post('/api/plans', json={**PLAN, 'end_at': None}).json()['plan']
    response = client.post('/api/plans', json={**PLAN, 'start_at': '2026-11-20T10:00:00Z', 'end_at': None})
    assert response.status_code == 409
    assert client.get('/api/plans').json() == [previous]


def test_legacy_end_boundary_and_note_patch_preserve_stored_end(api):
    client, _ = api
    legacy = client.post('/api/plans', json=PLAN).json()['plan']
    response = client.post('/api/plans', json={**PLAN, 'match_id': 'boundary',
                                              'start_at': '2026-11-19T12:00:00Z', 'end_at': None})
    assert response.status_code == 201
    assert response.json()['overlapping_plan_ids'] == [] and response.json()['overlap_warnings'] == []
    path = f"/api/plans/{legacy['id']}"
    changed = client.patch(path, json={'note': 'updated'}).json()
    assert changed['plan']['end_at'] == legacy['end_at']
    assert changed['overlapping_plan_ids'] == [] and changed['overlap_warnings'] == []
    assert client.get(path).json()['end_at'] == legacy['end_at']
    assert client.delete(path).status_code == 204


def test_concurrent_duplicate_create_allows_only_one_insert(api):
    client, _ = api
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post('/api/plans', json=PLAN), range(2)))
    assert sorted(result.status_code for result in results) == [201, 409]
    assert len(client.get('/api/plans').json()) == 1


def test_existing_duplicate_plans_are_preserved_and_individually_manageable(api):
    client, db = api
    original = client.post('/api/plans', json=PLAN).json()['plan']
    with db.connection(write=True) as conn:
        conn.execute(
            '''INSERT INTO plans (match_id, home_team, away_team, venue_name, start_at, end_at, note, created_at, updated_at)
               SELECT match_id, home_team, away_team, venue_name, start_at, end_at, ?, created_at, updated_at
               FROM plans WHERE id = ?''',
            ('legacy copy', original['id']),
        )
    before = client.get('/api/plans').json()
    assert len(before) == 2
    assert client.post('/api/plans', json=PLAN).status_code == 409
    assert client.get('/api/plans').json() == before
    duplicate_path = f"/api/plans/{before[1]['id']}"
    changed = client.patch(duplicate_path, json={'note': 'edited'})
    assert changed.status_code == 200
    assert changed.json()['plan']['end_at'] == original['end_at']
    assert changed.json()['overlapping_plan_ids'] == [original['id']]
    assert client.delete(duplicate_path).status_code == 204
    assert client.get('/api/plans').json() == [original]


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
