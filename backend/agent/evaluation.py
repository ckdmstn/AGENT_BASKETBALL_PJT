"""Deterministic comparisons. Unknown facts never satisfy a requested constraint."""
import re

from backend.agent.state import Assessment, ConditionCheck, Conditions
from backend.config import KST
from backend.schemas import Arena, GameCandidate, GameDetail, Weather

# Official references checked 2026-11-19; only these aliases have address evidence.
VENUES = [
    ({'잠실학생체육관', '서울특별시교육청학생체육관'}, '송파구올림픽로25',
     'https://ssg.sen.go.kr/fus/MI000000000000000366/html/cont0010v.do'),
    ({'안양정관장아레나'}, '안양시동안구평촌대로389',
     'https://www.kgc.co.kr/intro/kgc-introduction/affiliate.do'),
    ({'수원KT소닉붐아레나', 'KT소닉붐아레나', '서수원칠보체육관'}, '수원시권선구서수원로577번길171',
     'https://www.kbl.or.kr/upfiles/ebook/2425_media_guidebook.pdf'),
]


def normalized(value):
    return re.sub(r'\s+', '', value or '').casefold()


def verified_arena(venue_name: str, candidates: list[dict]) -> Arena | None:
    for aliases, address, _source in VENUES:
        names = {normalized(n) for n in aliases}
        if normalized(venue_name) not in names:
            continue
        matches = [Arena.model_validate(c) for c in candidates
                   if normalized(c.get('name')) in names and normalized(address) in normalized(c.get('road_address'))]
        if len(matches) == 1:
            return matches[0].model_copy(update={'verified_kbl_arena': True})
    return None


def requested_weather(c: Conditions) -> bool:
    return c.weather_preference is not None or c.max_precipitation_probability_pct is not None


def team_matches(team: str, game: dict) -> bool:
    # Explicit common team abbreviations; no geographic inference from team names.
    aliases = {'lg': 'LG', 'sk': 'SK', 'kt': 'KT', 'kcc': 'KCC', 'db': 'DB',
               '삼성': '삼성', '정관장': '정관장', '소노': '소노', '현대모비스': '현대모비스', '한국가스공사': '한국가스공사'}
    key = normalized(team)
    target = normalized(aliases.get(key, team))
    return any(target in normalized(game.get(k)) for k in ('home_team', 'away_team'))


def assess(game: dict, detail: dict | None, arena: dict | None, weather: dict | None,
           c: Conditions) -> Assessment:
    g = GameCandidate.model_validate(game)
    d = GameDetail.model_validate(detail) if detail else None
    a = Arena.model_validate(arena) if arena else None
    w = Weather.model_validate(weather) if weather else None
    checks = {}

    def put(key, result, evidence):
        checks[key] = ConditionCheck(status='unknown' if result is None else 'met' if result else 'unmet', reason=evidence)

    category = g.season_category
    regular = None if category is None or g.season_grade is None else category == 'R' and g.season_grade == 1
    put('competition', regular, f'정규리그 기준 R/1; 실측 대회={category}, 등급={g.season_grade}')
    put('detail', True if d is not None else None, '식별자 기반 상세 조회 확인' if d else '상세 정보를 확인하지 못함')
    # Prefer detail facts; if detail contradicts candidate, do not silently use either.
    conflicts = d and any(getattr(d, k) is not None and getattr(g, k) is not None and getattr(d, k) != getattr(g, k)
                          for k in ('start_at', 'home_team', 'away_team', 'venue_name'))
    if conflicts:
        put('detail', None, '목록과 상세 속성이 달라 확인 필요')
    start = d.start_at if d and not conflicts else None
    if c.date_range:
        put('date', None if start is None else c.date_range.from_date <= start.astimezone(KST).date() <= c.date_range.to_date,
            f'경기 시작={start.isoformat() if start else "미확인"}; 요청 범위={c.date_range.from_date}~{c.date_range.to_date}')
    if c.start_after:
        put('time', None if start is None else start.astimezone(KST).time() >= c.start_after,
            f'요청 시작 하한={c.start_after}; 실제 시작={start.isoformat() if start else "미확인"}')
    if c.preferred_team:
        put('team', team_matches(c.preferred_team, game), f'선호팀={c.preferred_team}; 실제={g.home_team}/{g.away_team}')
    put('venue', True if a and a.verified_kbl_arena else None, a.road_address if a else '공식 이름·주소와 일치하는 장소 미확인')
    if c.region:
        address = (a.road_address or a.address or '') if a else ''
        region = {'서울특별시': '서울', '부산광역시': '부산', '경기도': '경기'}.get(c.region, c.region)
        # Compare administrative address tokens, not arbitrary substring of a road name.
        tokens = address.split()[:3]
        put('region', None if not a or not address else region in tokens or any(t == region + '시' or t == region + '구' for t in tokens),
            f'요청 지역={c.region}; 확인 주소={address or "미확인"}')
    if requested_weather(c):
        pop = w.precipitation_probability_pct if w and w.available else None
        expected = start.astimezone(KST).replace(minute=0, second=0, microsecond=0) if start else None
        if w and w.forecast_at != expected:
            pop = None
        limit = c.max_precipitation_probability_pct
        put('weather', None if pop is None else True if limit is None else pop <= limit,
            f'강수확률={pop if pop is not None else "미확인"}; 상한={limit if limit is not None else "미지정, 낮은 순 정렬"}')
    statuses = [check.status for check in checks.values()]
    status = 'unmet' if 'unmet' in statuses else 'unknown' if 'unknown' in statuses else 'met'
    return Assessment(match_id=g.match_id, game=g, detail=d, arena=a, weather=w, checks=checks, status=status)
