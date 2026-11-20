from collections import Counter
from datetime import datetime

import pytest

from backend.agent.graph import AgentRunner
from backend.agent.llm import LLMError
from backend.agent.state import Analysis, Narration, WorkPlan
from backend.config import Settings
from backend.schemas import (Arena, GameCandidate, GameDetail, ToolMeta, ToolSuccess, Weather, failure)


class FakeLLM:
    def __init__(self, analyses):
        self.analyses = list(analyses)
        self.stages = []

    def complete(self, stage, payload, output_model):
        self.stages.append(stage)
        if stage == 'analyze':
            item = self.analyses.pop(0)
            if isinstance(item, Exception):
                raise item
            return Analysis.model_validate(item)
        if stage == 'plan':
            c = payload['conditions']
            tools = ['search_kbl_games', 'get_kbl_game_detail', 'search_arena']
            if c.get('weather_preference') or c.get('max_precipitation_probability_pct') is not None:
                tools.append('get_weather')
            return WorkPlan(tools=tools, reason='필요한 정보만 조회')
        return Narration(lead='조건 검증 결과를 안내합니다.')


def analysis(**changes):
    values = {'date_range': {'from_date': '2026-11-19', 'to_date': '2026-11-19'}, **changes}
    return {'intent': 'plan', 'conditions': values, 'changed_fields': list(values)}


def game(match_id='one', away='서울 SK', category='R'):
    return GameCandidate(match_id=match_id, home_team='서울 삼성', away_team=away,
                         start_at=datetime.fromisoformat('2026-11-19T19:00:00+09:00'),
                         venue_name='잠실학생체육관', source='mock', season_grade=1, season_category=category)


class FakeTools:
    def __init__(self, games=None, pop=20, fail=None):
        self.games = [game()] if games is None else games
        self.pop, self.fail, self.calls = pop, fail, []

    def __call__(self, name, args, settings):
        self.calls.append((name, args.copy()))
        meta = ToolMeta(source='offline mock')
        if name == self.fail:
            return failure('MISSING_API_KEY', '설정이 필요합니다.', meta)
        if name == 'search_kbl_games':
            return ToolSuccess(data=self.games, meta=meta) if self.games else failure('NO_RESULT', '없음', meta)
        if name == 'get_kbl_game_detail':
            g = next(g for g in self.games if g.match_id == args['match_id'])
            return ToolSuccess(data=GameDetail(match_id=g.match_id, home_team=g.home_team, away_team=g.away_team,
                                               start_at=g.start_at, venue_name=g.venue_name), meta=meta)
        if name == 'search_arena':
            return ToolSuccess(data=[Arena(name='서울특별시교육청 학생체육관', road_address='서울 송파구 올림픽로 25',
                                           lat=37.5122, lon=127.0754, place_url='https://place.map.kakao.com/1')], meta=meta)
        return ToolSuccess(data=Weather(forecast_at=datetime.fromisoformat(args['date_time']).replace(minute=0),
                                       issued_at=datetime.fromisoformat('2026-11-19T11:00:00+09:00'),
                                       temperature_c=12, precipitation_probability_pct=self.pop, available=True), meta=meta)


def runner(analyses, tools=None):
    return AgentRunner(llm=FakeLLM(analyses), tool_invoker=tools or FakeTools(), settings=Settings())


def test_real_graph_conditions_and_dependency_arguments():
    tools = FakeTools()
    agent = runner([analysis(region='서울', start_after='14:00', max_precipitation_probability_pct=30)], tools)
    r = agent.run('서울 오후2시 이후 강수확률30% 이하', 's')
    assert r.conditions.region == '서울'
    assert len(r.recommendations) == 1
    assert r.recommendations[0].checks['weather'].status == 'met'
    args = {name: args for name, args in tools.calls}
    assert args['get_kbl_game_detail']['match_id'] == 'one'
    assert args['search_arena']['venue_name'] == '잠실학생체육관'
    assert args['get_weather']['lat'] == 37.5122 and args['get_weather']['lon'] == 127.0754
    assert args['get_weather']['date_time'] == '2026-11-19T19:00:00+09:00'
    assert [e['node_name'] for e in r.events if e['event_type'] == 'NODE_STARTED'] == ['analyze','plan','execute_tools','evaluate','respond']
    assert r.events[-1]['event_type'] == 'RUN_COMPLETED'


def test_greeting_calls_no_tools():
    tools = FakeTools()
    r = runner([{'intent': 'greeting'}], tools).run('안녕')
    assert tools.calls == [] and r.recommendations == []


def test_missing_dates_asks_without_inventing_range():
    tools = FakeTools()
    r = runner([{'intent': 'plan', 'conditions': {'region':'서울'}, 'changed_fields':['region']}], tools).run('서울 경기 추천')
    assert not tools.calls and r.conditions.date_range is None
    assert '날짜' in r.answer


def test_null_probability_is_unknown_not_zero():
    r = runner([analysis(max_precipitation_probability_pct=30)], FakeTools(pop=None)).run('30% 이하')
    assert not r.recommendations
    assert r.excluded[0].checks['weather'].status == 'unknown'
    assert r.excluded[0].weather.temperature_c == 12


def test_weather_skipped_without_weather_condition():
    tools = FakeTools()
    runner([analysis()], tools).run('경기 추천')
    assert 'get_weather' not in [name for name,_ in tools.calls]


def test_explicit_team_relaxation_reuses_results():
    tools = FakeTools([game()])
    r = runner([analysis(preferred_team='LG', fallback_teams_allowed=True)], tools).run('LG 경기 없으면 다른 팀도 괜찮아')
    assert r.replan_count == 1 and len(r.recommendations) == 1
    assert r.conditions.preferred_team == 'LG' and r.active_conditions.preferred_team is None
    assert Counter(name for name,_ in tools.calls)['search_kbl_games'] == 1
    assert any(e['payload'].get('cached') for e in r.events if e['event_type']=='TOOL_RESPONDED')


def test_no_unapproved_relaxation():
    r = runner([analysis(preferred_team='LG')]).run('LG 경기')
    assert not r.recommendations and r.replan_count == 0
    assert r.active_conditions.preferred_team == 'LG'


def test_replan_maximum_three_with_authorized_date_alternatives():
    alternatives = [{'from_date':f'2026-11-{d}', 'to_date':f'2026-11-{d}'} for d in (20,21,22)]
    r = runner([analysis(preferred_team='LG', fallback_teams_allowed=True, alternative_date_ranges=alternatives)], FakeTools([])).run(
        'LG 경기 없으면 다른 팀도 괜찮아. 대체 날짜: 2026-11-20,2026-11-21,2026-11-22 허용해')
    assert r.replan_count == 3 and len(r.relaxation_history) == 3
    assert not r.recommendations
    assert r.active_conditions.region == r.conditions.region


@pytest.mark.parametrize('tool', ['search_kbl_games','get_kbl_game_detail','search_arena','get_weather'])
def test_tool_failure_is_safe_and_not_success(tool):
    r = runner([analysis(region='서울', max_precipitation_probability_pct=30, fallback_teams_allowed=True)], FakeTools(fail=tool)).run('다른 팀도 괜찮아')
    assert any(e.code == 'MISSING_API_KEY' for e in r.errors)
    assert not r.recommendations and r.replan_count == 0


def test_follow_up_changes_only_explicit_fields_and_keeps_original_after_relaxation():
    a = runner([analysis(region='서울', preferred_team='LG', fallback_teams_allowed=True),
                {'intent':'follow_up','conditions':{'preferred_team':'SK'},'changed_fields':['preferred_team']}])
    a.run('서울 경기를 추천해 줘. LG 경기 없으면 다른 팀도 괜찮아', 's')
    second = a.run('팀만 SK', 's')
    assert second.conditions.region == '서울' and second.conditions.preferred_team == 'SK'
    assert second.conditions.date_range.from_date.isoformat() == '2026-11-19'


def test_llm_failure_is_safe_and_does_not_execute_tools():
    tools = FakeTools()
    r = runner([LLMError('LLM_INVALID_RESPONSE')], tools).run('추천')
    assert not tools.calls and r.errors[0].code == 'LLM_INVALID_RESPONSE'
    assert r.events[-1]['event_type'] == 'RUN_FAILED'


def test_non_regular_competitions_are_excluded():
    r = runner([analysis()], FakeTools([game(category='EA')])).run('추천')
    assert not r.recommendations and r.excluded[0].checks['competition'].status == 'unmet'


def test_region_checked_against_arena_address_not_team_name():
    r = runner([analysis(region='부산')]).run('부산')
    assert not r.recommendations and r.excluded[0].checks['region'].status == 'unmet'


def test_unverified_place_never_used_as_weather_location():
    tools = FakeTools()
    original = tools.__call__
    def invoke(name,args,config):
        if name=='search_arena':
            return ToolSuccess(data=[Arena(name='학생체육관 비슷한곳',road_address='부산 어딘가',lat=35,lon=129)],meta=ToolMeta(source='mock'))
        return original(name,args,config)
    a = AgentRunner(llm=FakeLLM([analysis(max_precipitation_probability_pct=30)]),tool_invoker=invoke,settings=Settings())
    r = a.run('추천')
    assert not r.recommendations
    assert 'get_weather' not in [name for name,_ in tools.calls]


@pytest.mark.parametrize('tool,status,service', [('search_arena',401,None), ('get_weather',200,'30'),
                                               ('get_weather',429,None)])
def test_authentication_or_quota_failure_never_triggers_replan(tool,status,service):
    tools=FakeTools()
    def invoke(name,args,config):
        if name == tool:
            return failure('UPSTREAM_ERROR','외부 서비스 실패',ToolMeta(source='mock',http_status=status,service_code=service))
        return tools(name,args,config)
    a=AgentRunner(llm=FakeLLM([analysis(max_precipitation_probability_pct=30, fallback_teams_allowed=True,
                                       alternative_date_ranges=[{'from_date':'2026-11-20','to_date':'2026-11-20'}])]),
                  tool_invoker=invoke,settings=Settings())
    r=a.run('다른 팀도 괜찮아. 대체 날짜: 2026-11-20 허용해')
    assert r.replan_count == 0


def test_unavailable_detail_is_unknown_not_condition_failure():
    r=runner([analysis()],FakeTools(fail='get_kbl_game_detail')).run('추천')
    assert r.excluded[0].checks['detail'].status == 'unknown'


def test_matching_candidate_after_twelve_other_games_is_not_discarded():
    tools=FakeTools([game(str(i),away='창원 LG') for i in range(12)] + [game('target')])
    r=runner([analysis(preferred_team='SK',fallback_teams_allowed=True)],tools).run('SK 경기 없으면 다른 팀도 괜찮아')
    assert [x.match_id for x in r.recommendations] == ['target']
    assert r.replan_count == 0


@pytest.mark.parametrize('requested,address,expected', [
    ('서울','서울특별시 송파구 올림픽로 25','met'),
    ('서울특별시','서울 송파구 올림픽로 25','met'),
    ('부산','부산광역시 동래구 사직로 55','met'),
    ('부산광역시','부산 동래구 사직로 55','met'),
    ('경기','경기도 수원시 권선구 서수원로577번길 171','met'),
    ('경기도','경기 수원시 권선구 서수원로577번길 171','met'),
    ('서울','부산광역시 동래구 사직로 55','unmet'),
    ('서울',None,'unknown'),
    ('서울','주소 미확인 서울로 25','unknown'),
    ('서울','경기 수원시 서울로 25','unmet'),
    ('서울','경기 서울 수원시 25','unmet'),
    ('송파','서울특별시 강남구 송파로 25','unmet'),
    ('수원','경기도 서수원로577번길 171','unknown'),
])
def test_region_administrative_aliases_and_road_name_isolation(requested,address,expected):
    from backend.agent.evaluation import region_match

    assert region_match(requested, address or '') is {'met': True, 'unmet': False, 'unknown': None}[expected]


def test_llm_decision_reasons_are_recorded_in_order():
    a=analysis()
    a['reason']='명시한 날짜의 경기를 요청함'
    r=runner([a]).run('경기 추천')
    decisions=[e for e in r.events if e['event_type']=='LLM_DECISION']
    assert decisions[0]['payload']['reason']=='명시한 날짜의 경기를 요청함'
    assert decisions[1]['payload']['reason']=='필요한 정보만 조회'
    assert decisions[0]['payload']['changed_fields']==['date_range']
    assert decisions[1]['payload']['tools']==['search_kbl_games','get_kbl_game_detail','search_arena']
    assert [e['sequence_no'] for e in r.events] == list(range(1,len(r.events)+1))


@pytest.mark.parametrize('reason', ['synthetic-private-key', 'Authorization: Bearer hidden-credential',
                                   'Traceback RuntimeError: raw exception', '상세 내부 추론'*30, '경기 추천'])
def test_decision_reasons_are_safe_before_subscriber_delivery(reason):
    from unittest.mock import patch
    from backend.agent.events import EventBus
    captured=[]
    original=EventBus.publish
    def publish(bus,*args,**kwargs):
        if not bus._subscribers:
            bus.subscribe(lambda event: captured.append(event.model_dump(mode='json')))
            bus.subscribe(lambda event: (_ for _ in ()).throw(RuntimeError('subscriber error')))
        return original(bus,*args,**kwargs)
    a=analysis()
    a['reason']=reason
    config=Settings(llm_key='synthetic-private-key')
    class ReasonLLM(FakeLLM):
        def complete(self,stage,payload,output_model):
            result=super().complete(stage,payload,output_model)
            return result.model_copy(update={'reason':reason}) if stage=='plan' else result
    with patch.object(EventBus,'publish',publish):
        r=AgentRunner(llm=ReasonLLM([a]),tool_invoker=FakeTools(),settings=config).run('경기 추천')
    reasons=[e['payload']['reason'] for e in captured if e['event_type']=='LLM_DECISION' and e['node_name'] in ('analyze','plan')]
    assert reasons and all(0<len(text)<=120 for text in reasons)
    for text in reasons:
        assert not any(secret in text for secret in ('synthetic-private-key','hidden-credential','Traceback','raw exception','경기 추천'))
    assert r.events[-1]['event_type']=='RUN_COMPLETED'


def test_answer_renders_recommendation_reasons_from_checks():
    r=runner([analysis(region='서울',start_after='14:00',max_precipitation_probability_pct=30)]).run('추천')
    assert '2026-11-19T19:00:00+09:00' in r.answer and '잠실학생체육관' in r.answer
    assert '추천 근거' in r.answer
    for key in ('date','time','region','weather'):
        assert r.recommendations[0].checks[key].reason in r.answer


@pytest.mark.parametrize('pop,expected', [(None,'미확인'),(80,'불충족')])
def test_answer_explains_unknown_and_unmet_from_checks(pop,expected):
    r=runner([analysis(max_precipitation_probability_pct=30)],FakeTools(pop=pop)).run('강수30%')
    assert expected in r.answer
    assert r.excluded[0].checks['weather'].reason in r.answer
    assert not r.recommendations


def test_follow_up_revokes_prior_team_relaxation_permission():
    a=runner([analysis(preferred_team='LG',fallback_teams_allowed=True,region='서울',start_after='14:00'),
              {'intent':'follow_up','conditions':{'fallback_teams_allowed':False},'changed_fields':['fallback_teams_allowed']}])
    first=a.run('LG 경기 없으면 다른 팀도 괜찮아', 'revoke')
    second=a.run('이제 다른 팀은 안 돼', 'revoke')
    assert first.replan_count == 1 and second.replan_count == 0
    assert second.conditions.preferred_team=='LG' and not second.recommendations
    assert second.conditions.region=='서울' and second.conditions.start_after.isoformat()=='14:00:00'
    assert second.conditions.date_range == first.conditions.date_range


def test_structurally_valid_llm_permission_cannot_authorize_relaxation():
    # A valid schema is not user consent, even if the LLM says true.
    a=analysis(preferred_team='LG',fallback_teams_allowed=True)
    extracted=Analysis.model_validate(a)
    assert extracted.conditions.fallback_teams_allowed is True
    r=runner([a]).run('LG 경기만 추천해 줘')
    assert r.replan_count == 0
    assert r.conditions.fallback_teams_allowed is False
