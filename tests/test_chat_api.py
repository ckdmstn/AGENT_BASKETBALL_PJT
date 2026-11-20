import pytest
from fastapi.testclient import TestClient

from backend.main import app, get_agent_runner
from tests.test_agent import FakeLLM, FakeTools, analysis
from backend.agent.graph import AgentRunner
from backend.config import Settings


@pytest.fixture
def client():
    agent = AgentRunner(llm=FakeLLM([analysis(), {'intent':'follow_up','conditions':{'preferred_team':'SK'},'changed_fields':['preferred_team']}]),
                        tool_invoker=FakeTools(),settings=Settings())
    app.dependency_overrides[get_agent_runner] = lambda: agent
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


def test_chat_response_and_session_follow_up(client):
    first = client.post('/api/chat',json={'session_id':'api-session','message':'경기 추천'})
    assert first.status_code == 200
    body = first.json()
    assert body['session_id']=='api-session' and body['run_id']
    assert body['recommendations'][0]['match_id']=='one'
    assert body['events'][-1]['event_type']=='RUN_COMPLETED'
    second = client.post('/api/chat',json={'session_id':'api-session','message':'팀만 SK로'})
    assert second.status_code == 200 and second.json()['conditions']['preferred_team']=='SK'
    assert second.json()['run_id'] != body['run_id']


@pytest.mark.parametrize('body',[{'message':''},{'message':'test','session_id':'bad / id'}, {'message':'x'*4001}])
def test_chat_invalid_request_does_not_echo_input(client,body):
    r=client.post('/api/chat',json=body)
    assert r.status_code == 422
    assert 'input' not in r.json()


def test_chat_schema_registered(client):
    spec=client.get('/openapi.json').json()
    assert '/api/chat' in spec['paths']
    assert 'ChatResponse' in spec['components']['schemas']


@pytest.mark.parametrize('choice', ['true', 1, 0, [], {}])
def test_chat_rejects_non_boolean_team_choice(client, choice):
    response = client.post('/api/chat', json={'message': '경기 추천', 'allow_other_teams': choice})
    assert response.status_code == 422
    assert response.json() == {'detail': '요청 형식을 확인해 주세요.'}


def test_chat_team_checkbox_has_priority_and_preserves_response(client):
    first = client.post('/api/chat', json={'message': 'LG만 추천해줘', 'allow_other_teams': True})
    assert first.status_code == 200 and first.json()['team_permission'] == 'allowed'
    assert any('체크박스' in item for item in first.json()['warnings'])
    second = client.post('/api/chat', json={
        'session_id': first.json()['session_id'], 'message': '다른 팀도 괜찮아.', 'allow_other_teams': False,
    })
    assert second.status_code == 200 and second.json()['team_permission'] == 'denied'
    assert not second.json()['conditions']['fallback_teams_allowed']
    assert second.json()['replan_count'] == 0
    assert any('체크박스' in item for item in second.json()['warnings'])


@pytest.mark.parametrize('choice', [{}, {'allow_other_teams': None}])
def test_chat_null_and_omitted_preserve_legacy_grammar(client, choice):
    response = client.post('/api/chat', json={'message': '다른 팀도 괜찮아.', **choice})
    assert response.status_code == 200 and response.json()['team_permission'] == 'allowed'
