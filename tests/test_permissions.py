"""Supported consent grammar tests; no LLM or external HTTP calls."""
import pytest

from backend.agent.permissions import verify_permissions
from tests.test_agent import FakeTools, analysis, runner


@pytest.mark.parametrize('message,expected', [
    ('LG 경기만 추천해 줘',False),
    ('LG 경기 없으면 다른 팀도 괜찮아',True),
    ('LG 경기 아니면 추천하지 마',False),
    ('다른 팀도 괜찮을까?',False),
    ('아마 다른 팀도 괜찮아',False),
    ('다른 팀도 괜찮아 라고 말한 적 없어',False),
])
def test_unsupported_or_negative_text_blocks_false_llm_permission(message,expected):
    r=runner([analysis(preferred_team='LG',fallback_teams_allowed=True)]).run(message)
    assert r.conditions.fallback_teams_allowed is expected
    assert r.replan_count == int(expected)
    assert bool(r.recommendations) is expected


def test_previous_verified_consent_survives_team_only_follow_up():
    a=runner([analysis(preferred_team='LG',fallback_teams_allowed=True),
              {'intent':'follow_up','conditions':{'preferred_team':'DB'},'changed_fields':['preferred_team']}])
    a.run('LG 경기 없으면 다른 팀도 괜찮아','keep')
    r=a.run('팀만 DB로 바꿔 줘','keep')
    assert r.conditions.preferred_team=='DB' and r.conditions.fallback_teams_allowed is True
    assert r.replan_count==1


def test_withdrawal_wins_even_when_llm_omits_or_misreads_it():
    a=runner([analysis(preferred_team='LG',fallback_teams_allowed=True),
              {'intent':'follow_up','conditions':{'fallback_teams_allowed':True},'changed_fields':['fallback_teams_allowed']}])
    a.run('LG 경기 없으면 다른 팀도 괜찮아','revoke-wrong')
    r=a.run('다른 팀은 안 돼','revoke-wrong')
    assert not r.conditions.fallback_teams_allowed and r.replan_count==0


def test_permission_only_turns_preserve_filters_if_model_misclassifies():
    agent = runner([analysis(preferred_team='LG', region='서울'), {'intent': 'greeting'}, {'intent': 'help'}])
    original = agent.run('서울에서 LG 경기 추천', 'button-session')
    granted = agent.run('다른 팀도 괜찮아.', 'button-session')
    revoked = agent.run('다른 팀은 안 돼.', 'button-session')
    assert original.team_permission == 'denied'
    assert granted.team_permission == 'allowed'
    assert granted.conditions.preferred_team == 'LG'
    assert granted.active_conditions.preferred_team is None
    assert granted.conditions.date_range == original.conditions.date_range
    assert revoked.conditions == original.conditions
    assert revoked.team_permission == 'denied' and revoked.replan_count == 0


def test_ambiguous_message_returns_confirmation_required_without_permission():
    agent = runner([analysis(preferred_team='LG', fallback_teams_allowed=True)])
    response = agent.run('서울에서 LG 경기 추천해줘 없으면 다른 팀도 괜찮아', 'ambiguous')
    assert response.team_permission == 'confirmation_required'
    assert not response.conditions.fallback_teams_allowed and response.replan_count == 0
    assert not agent.sessions.load('ambiguous')['permissions']['team']


def test_unverified_legacy_session_flag_is_not_authority():
    from backend.agent.state import Conditions
    a=runner([{'intent':'follow_up','conditions':{'preferred_team':'DB'},'changed_fields':['preferred_team']}])
    a.sessions.save('legacy',Conditions.model_validate(analysis(preferred_team='LG',fallback_teams_allowed=True)['conditions']),'old')
    r=a.run('팀만 DB로 바꿔 줘','legacy')
    assert not r.conditions.fallback_teams_allowed and r.replan_count==0


def test_llm_invented_alternative_dates_are_not_searched():
    tools=FakeTools([])
    r=runner([analysis(alternative_date_ranges=[{'from_date':'2026-11-20','to_date':'2026-11-20'}])],tools).run('11월 19일 경기만 추천해 줘')
    assert r.replan_count==0 and r.conditions.alternative_date_ranges==[]
    assert all(args['from_date']=='2026-11-19' for name,args in tools.calls if name=='search_kbl_games')


def test_only_explicit_iso_date_alternatives_are_searched():
    tools=FakeTools([])
    r=runner([analysis(alternative_date_ranges=[{'from_date':'2026-11-21','to_date':'2026-11-21'}])],tools).run(
        '11월 19일 경기를 추천해 줘. 대체 날짜: 2026-11-20 허용해')
    assert r.replan_count==1
    assert [(d.from_date.isoformat(),d.to_date.isoformat()) for d in r.conditions.alternative_date_ranges]==[('2026-11-20','2026-11-20')]
    assert [args['from_date'] for name,args in tools.calls if name=='search_kbl_games']==['2026-11-19','2026-11-20']


def test_date_permission_withdrawal_ignores_llm_omission():
    a=runner([analysis(alternative_date_ranges=[{'from_date':'2026-11-20','to_date':'2026-11-20'}]),
              {'intent':'follow_up'}],FakeTools([]))
    first=a.run('추천해 줘. 대체 날짜: 2026-11-20 허용해','dates')
    second=a.run('다른 날짜는 안 돼','dates')
    assert first.replan_count==1 and second.replan_count==0
    assert second.conditions.alternative_date_ranges==[]


def test_unclear_consent_produces_confirmation_warning():
    r=runner([analysis(preferred_team='LG',fallback_teams_allowed=True)]).run('다른 팀도 괜찮을까?')
    assert r.replan_count==0 and any('확인' in warning for warning in r.warnings)
    assert r.warnings[0] in r.answer


@pytest.mark.parametrize('message', ['방금 허용은 취소해', '날짜는 바꾸지 마',
                                   '대체 날짜: 2026-11-20 허용해. 날짜는 바꾸지 마'])
def test_revocation_cannot_be_overridden_by_existing_or_same_message_allowance(message):
    previous={'team':True,'date_ranges':[{'from_date':'2026-11-20','to_date':'2026-11-20'}]}
    permission,_=verify_permissions(message,previous,follow_up=True)
    assert permission['date_ranges']==[]
    if '취소' in message:
        assert permission['team'] is False


@pytest.mark.parametrize('message', [
    '예시: LG 경기 없으면 다른 팀도 괜찮아',
    '다른 팀은 안 돼. LG 경기 없으면 다른 팀도 괜찮아',
    '대체 날짜: 2026-11-20 허용해 라고 친구가 말했어',
    '대체 날짜: 2026-02-30 허용해',
    '허용이 아님: LG 경기 없으면 다른 팀도 괜찮아',
])
def test_ambiguous_quoted_conflicting_or_invalid_permissions_do_not_grant(message):
    permission,warnings=verify_permissions(message,{},follow_up=False)
    assert not permission['team'] and permission['date_ranges']==[]


@pytest.mark.parametrize('failed_stage',['analyze','plan'])
@pytest.mark.parametrize('kind',['team','dates'])
def test_verified_withdrawal_persists_even_when_llm_processing_fails(failed_stage,kind):
    from backend.agent.graph import AgentRunner
    from backend.agent.llm import LLMError
    from backend.config import Settings
    from tests.test_agent import FakeLLM
    class ToggleLLM(FakeLLM):
        fail_stage=None
        def complete(self,stage,payload,output_model):
            if stage==self.fail_stage:
                raise LLMError('LLM_UPSTREAM_ERROR')
            return super().complete(stage,payload,output_model)
    initial=analysis(preferred_team='LG',fallback_teams_allowed=True) if kind=='team' else analysis(
        alternative_date_ranges=[{'from_date':'2026-11-20','to_date':'2026-11-20'}])
    llm=ToggleLLM([initial,{'intent':'follow_up'},{'intent':'follow_up'}])
    a=AgentRunner(llm=llm,tool_invoker=FakeTools() if kind=='team' else FakeTools([]),settings=Settings())
    grant='LG 경기 없으면 다른 팀도 괜찮아' if kind=='team' else '대체 날짜: 2026-11-20 허용해'
    assert a.run(grant,'failed-withdrawal').replan_count==1
    llm.fail_stage=failed_stage
    failed=a.run('다른 팀은 안 돼' if kind=='team' else '다른 날짜는 안 돼','failed-withdrawal')
    assert failed.errors
    llm.fail_stage=None
    final=a.run('다시 찾아 줘','failed-withdrawal')
    assert final.replan_count==0
    if kind=='team':
        assert not final.conditions.fallback_teams_allowed
    else:
        assert final.conditions.alternative_date_ranges==[]
