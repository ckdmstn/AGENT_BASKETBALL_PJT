from datetime import datetime

import pytest

from backend.agent.evaluation import verified_arena
from backend.schemas import Arena, GameCandidate, ToolMeta, ToolSuccess, failure
from tests.test_agent import FakeTools, analysis, runner


CHANGWON = {
    'name': '창원스포츠파크 창원체육관',
    'road_address': '경남 창원시 성산구 원이대로 450',
    'lat': 35.2327367366309,
    'lon': 128.666283189427,
}


@pytest.mark.parametrize('venue, name, address', [
    ('창원체육관', CHANGWON['name'], CHANGWON['road_address']),
    ('잠실학생체육관', '서울특별시교육청 학생체육관', '서울 송파구 올림픽로 25'),
    ('안양 정관장 아레나', '안양정관장아레나', '경기 안양시 동안구 평촌대로 389'),
    ('수원 KT 소닉붐 아레나', '서수원칠보체육관', '경기 수원시 권선구 서수원로577번길 171'),
    ('부산사직체육관', '부산사직종합운동장 실내체육관', '부산 동래구 사직로 55-32'),
    ('고양소노아레나', '고양체육관', '경기 고양시 일산서구 중앙로 1601'),
    ('대구체육관', '대구실내체육관', '대구 북구 대구체육관로 39'),
    ('울산동천체육관', '동천체육관', '울산 중구 염포로 85'),
    ('원주DB프로미아레나', '원주종합체육관', '강원특별자치도 원주시 서원대로 281'),
])
def test_documented_names_and_road_address_match(venue, name, address):
    arena, reason = verified_arena(venue, [{**CHANGWON, 'name': name, 'road_address': address}])
    assert arena and arena.verified_kbl_arena and reason == '공식 경기장 주소 검증 완료'


@pytest.mark.parametrize('name, candidates, error, cause', [
    ('창원체육관 옆', [CHANGWON], None, '등록되지 않은'),
    ('창원체육관', [], 'NO_RESULT', '검색 결과가 없어'),
    ('창원체육관', [], 'UPSTREAM_ERROR', '조회에 실패'),
    ('창원체육관', [{**CHANGWON, 'name': '창원체육관 보조경기장'}], None, '장소명이'),
    ('창원체육관', [{**CHANGWON, 'road_address': '서울 창원시 성산구 원이대로 450'}], None, '주소와 일치하지'),
    ('창원체육관', [{**CHANGWON, 'road_address': CHANGWON['road_address'] + '-1'}], None, '주소와 일치하지'),
    ('창원체육관', [CHANGWON, CHANGWON], None, '여러 곳'),
    ('창원체육관', [{**CHANGWON, 'road_address': None}], None, '주소가 누락'),
    ('창원체육관', [{**CHANGWON, 'lat': None}], None, '유효한 좌표'),
])
def test_unverified_candidates_return_specific_reason(name, candidates, error, cause):
    arena, reason = verified_arena(name, candidates, error)
    assert arena is None and cause in reason


class ChangwonTools(FakeTools):
    def __init__(self, *, arena_error=None, weather_error=None, pop=None):
        game = GameCandidate(match_id='S49G01N79', home_team='창원 LG', away_team='안양 정관장',
                             start_at=datetime.fromisoformat('2026-12-03T19:00:00+09:00'),
                             venue_name='창원체육관', source='fixture', season_grade=1, season_category='R')
        super().__init__([game], pop=pop)
        self.arena_error = arena_error
        self.weather_error = weather_error

    def __call__(self, name, args, settings):
        meta = ToolMeta(source='fixture')
        if name == 'search_arena':
            self.calls.append((name, args))
            if self.arena_error:
                return failure(self.arena_error, 'fixture', meta)
            return ToolSuccess(data=[Arena(**CHANGWON)], meta=meta)
        if name == 'get_weather' and self.weather_error:
            self.calls.append((name, args))
            return failure(self.weather_error, 'fixture', meta)
        return super().__call__(name, args, settings)


@pytest.mark.parametrize('region, arena_error, weather_error, pop, region_status, weather_status, recommended', [
    ('창원', None, None, 10, 'met', 'met', True),
    ('서울', None, None, 10, 'unmet', 'met', False),
    ('창원', 'UPSTREAM_ERROR', None, 10, 'unknown', 'unknown', False),
    ('창원', None, 'UNSUPPORTED_DATE', None, 'met', 'unknown', False),
    ('창원', None, None, None, 'met', 'unknown', False),
])
def test_changwon_graph_location_weather_and_recommendation(
        region, arena_error, weather_error, pop, region_status, weather_status, recommended):
    tools = ChangwonTools(arena_error=arena_error, weather_error=weather_error, pop=pop)
    extracted = analysis(region=region, preferred_team='LG', max_precipitation_probability_pct=30,
                         date_range={'from_date': '2026-12-03', 'to_date': '2026-12-03'})
    result = runner([extracted], tools).run(f'12월 3일 {region}에서 LG 경기 추천. 강수확률 30% 이하.')
    item = (result.recommendations if recommended else result.excluded)[0]
    assert item.checks['region'].status == region_status
    assert item.checks['weather'].status == weather_status
    expected_weather_args = {'date_time': '2026-12-03T19:00:00+09:00', 'lat': CHANGWON['lat'], 'lon': CHANGWON['lon']}
    assert [args for name, args in tools.calls if name == 'get_weather'] == ([] if arena_error else [expected_weather_args])
    if arena_error:
        assert item.checks['venue'].status == 'unknown' and '조회에 실패' in item.checks['venue'].reason
    else:
        assert item.checks['venue'].status == 'met'
        if pop is None and not weather_error:
            assert item.weather.precipitation_probability_pct is None
