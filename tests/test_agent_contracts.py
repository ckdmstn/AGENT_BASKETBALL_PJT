from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests
from pydantic import ValidationError

from backend.agent.state import Analysis, Conditions, DateRange, Narration
from backend.agent.llm import JsonLLM, LLMError
from backend.agent.events import EventBus
from backend.agent.sessions import MemorySessions
from backend.config import Settings


def test_analysis_rejects_unlisted_or_missing_patch_values():
    with pytest.raises(ValidationError):
        Analysis(intent='follow_up', conditions={}, changed_fields=['preferred_team'])
    with pytest.raises(ValidationError):
        DateRange(from_date='2026-11-20', to_date='2026-11-19')


def test_session_copy_and_partial_update_are_isolated():
    sessions = MemorySessions()
    conditions = Conditions(region='서울', preferred_team='LG')
    sessions.save('s', conditions, 'summary')
    first = sessions.load('s')
    first['conditions']['region'] = '부산'
    assert sessions.load('s')['conditions']['region'] == '서울'
    assert sessions.load('other') is None


def test_subscriber_failure_does_not_break_events():
    bus = EventBus('s', 'r')
    bus.subscribe(Mock(side_effect=RuntimeError('private')))
    bus.publish('NODE_STARTED', node_name='analyze')
    bus.publish('NODE_COMPLETED', node_name='analyze')
    assert [e.sequence_no for e in bus.events] == [1, 2]
    assert all(e.session_id == 's' and e.run_id == 'r' for e in bus.events)
    assert 'private' not in str(bus.events)


@pytest.mark.parametrize('mode', ['missing', 'timeout', 'bad_json', 'http'])
def test_llm_errors_are_safe(mode):
    config = Settings(llm_key='' if mode == 'missing' else 'synthetic-private', llm_model='test')
    resp = Mock(status_code=401 if mode == 'http' else 200)
    resp.json.return_value = {'choices': [{'message': {'content': 'not JSON synthetic-private'}}]}
    with patch('requests.post', side_effect=requests.Timeout('synthetic-private') if mode == 'timeout' else None,
               return_value=resp) as post:
        with pytest.raises(LLMError) as exc:
            JsonLLM(config).complete('respond', {}, Narration)
    assert 'synthetic-private' not in str(exc.value)
    if mode == 'missing':
        post.assert_not_called()


def test_llm_success_uses_pydantic_validation():
    resp = Mock(status_code=200)
    resp.json.return_value = {'choices': [{'message': {'content': '{"lead":"조건 검증 결과를 안내합니다."}'}}]}
    with patch('requests.post', return_value=resp):
        result = JsonLLM(Settings(llm_key='test', llm_model='test')).complete('respond', {}, Narration)
    assert result.lead == '조건 검증 결과를 안내합니다.'
