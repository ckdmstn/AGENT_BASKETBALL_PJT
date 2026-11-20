"""Deterministic comparisons. Unknown facts never satisfy a requested constraint."""
import re

from backend.agent.state import Assessment, ConditionCheck, Conditions
from backend.config import KST
from backend.schemas import Arena, GameCandidate, GameDetail, Weather

# Official sources support facility names; KBL and Kakao labels were cross-checked.
VENUES = [
    ({'잠실학생체육관', '서울특별시교육청학생체육관'}, '서울 송파구 올림픽로 25',
     'https://ssg.sen.go.kr/fus/MI000000000000000366/html/cont0010v.do'),
    ({'안양정관장아레나'}, '경기 안양시 동안구 평촌대로 389',
     'https://www.kgc.co.kr/intro/kgc-introduction/affiliate.do'),
    ({'수원KT소닉붐아레나', 'KT소닉붐아레나', '서수원칠보체육관'}, '경기 수원시 권선구 서수원로577번길 171',
     'https://www.kbl.or.kr/upfiles/ebook/2425_media_guidebook.pdf'),
    ({'창원체육관', '창원스포츠파크 창원체육관'}, '경상남도 창원시 성산구 원이대로 450',
     'https://www.cwsisul.or.kr/_chsports/_sub01/sub01_02.html'),
    ({'고양소노아레나', '고양체육관'}, '경기 고양시 일산서구 중앙로 1601',
     'https://skygunners.kbl.or.kr/team/stadium'),
    ({'부산사직체육관', '부산 사직실내체육관', '부산사직종합운동장 실내체육관'}, '부산 동래구 사직로 55-32',
     'https://www.busan.go.kr/sports/main/3?action=view&no=127'),
    ({'대구체육관', '대구실내체육관'}, '대구 북구 대구체육관로 39',
     'https://www.kbl.or.kr/upfiles/ebook/2425_media_guidebook.pdf'),
    ({'울산동천체육관', '동천체육관'}, '울산 중구 염포로 85',
     'https://phoebus.kbl.or.kr/team/stadium'),
    ({'원주DB프로미아레나', '원주종합체육관'}, '강원특별자치도 원주시 서원대로 281',
     'https://cms.wfmc.kr/web/lay1/S1T156C179/contents.do'),
]
# The KBL label alone returned no Kakao result for this venue.
ARENA_SEARCH_NAMES = {'부산사직체육관': '부산 사직실내체육관'}


def normalized(value):
    return re.sub(r'\s+', '', value or '').casefold()


# Exact names/aliases only. Never strip arbitrary suffixes from a road name.
REGION_NAMES = {
    '서울': ('서울', '서울특별시'), '부산': ('부산', '부산광역시'),
    '대구': ('대구', '대구광역시'), '인천': ('인천', '인천광역시'),
    '광주': ('광주', '광주광역시'), '대전': ('대전', '대전광역시'),
    '울산': ('울산', '울산광역시'), '세종': ('세종', '세종특별자치시'),
    '경기': ('경기', '경기도'), '강원': ('강원', '강원도', '강원특별자치도'),
    '충북': ('충북', '충청북도'), '충남': ('충남', '충청남도'),
    '전북': ('전북', '전라북도', '전북특별자치도'), '전남': ('전남', '전라남도'),
    '경북': ('경북', '경상북도'), '경남': ('경남', '경상남도'),
    '제주': ('제주', '제주도', '제주특별자치도'),
}
REGION_ALIASES = {name: canonical for canonical, names in REGION_NAMES.items() for name in names}


def region_match(requested: str, address: str) -> bool | None:
    parts = address.split()
    if not parts or parts[0] not in REGION_ALIASES:
        return None
    province = REGION_ALIASES[parts[0]]
    if requested in REGION_ALIASES:
        return REGION_ALIASES[requested] == province
    # Only a contiguous administrative prefix is searchable; stop before roads/numbers.
    administrative = []
    for part in parts[1:]:
        if not re.fullmatch(r'[가-힣]+(?:시|군|구|읍|면|동)', part):
            break
        administrative.extend((part, part[:-1]))
    return requested in administrative if administrative else None


def road_address_key(value: str | None) -> tuple[str, str] | None:
    parts = (value or '').split(maxsplit=1)
    if len(parts) == 2 and parts[0] in REGION_ALIASES:
        return REGION_ALIASES[parts[0]], normalized(parts[1])
    return None


def verified_arena(venue_name: str, candidates: list[dict], error_code: str | None = None) -> tuple[Arena | None, str]:
    for aliases, address, _source in VENUES:
        names = {normalized(name) for name in aliases}
        if normalized(venue_name) in names:
            break
    else:
        return None, '아직 공식 주소 검증 대상에 등록되지 않은 경기장입니다.'
    if error_code and error_code != 'NO_RESULT':
        return None, '장소 조회에 실패하여 경기장 주소를 확인하지 못했습니다.'
    if not candidates:
        return None, '장소 검색 결과가 없어 경기장 위치를 확인하지 못했습니다.'
    named = [candidate for candidate in candidates if normalized(candidate.get('name')) in names]
    if not named:
        return None, '검색된 장소명이 공식 경기장 이름과 일치하지 않습니다.'
    official = road_address_key(address)
    matches = [candidate for candidate in named
               if official is not None and road_address_key(candidate.get('road_address')) == official]
    if not matches:
        if any(not candidate.get('road_address') for candidate in named):
            return None, '검색된 장소의 도로명주소가 누락되어 공식 주소를 확인하지 못했습니다.'
        return None, '검색된 장소가 공식 경기장 주소와 일치하지 않습니다.'
    if len(matches) != 1 or any(not candidate.get('road_address') for candidate in named):
        return None, '일치 가능성이 있는 장소가 여러 곳이어서 확정할 수 없습니다.'
    selected = Arena.model_validate(matches[0])
    if (selected.lat is None or selected.lon is None
            or not (30 <= selected.lat <= 44 and 120 <= selected.lon <= 133)):
        return None, '검색된 장소의 유효한 좌표를 확인하지 못했습니다.'
    return selected.model_copy(update={'verified_kbl_arena': True}), '공식 경기장 주소 검증 완료'


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
           c: Conditions, *, arena_reason: str | None = None) -> Assessment:
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
    put('venue', True if a and a.verified_kbl_arena else None,
        arena_reason or ((a.road_address or a.address or '구장 주소 미확인') if a else '공식 경기장 주소를 확인하지 못했습니다.'))
    if c.region:
        address = (a.road_address or '') if a and a.verified_kbl_arena else ''
        put('region', region_match(c.region, address),
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
