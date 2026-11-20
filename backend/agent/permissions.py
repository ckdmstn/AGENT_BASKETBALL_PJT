"""Fail-closed consent grammar, independent of LLM-extracted permission flags.

Only the documented direct phrases/ISO date directive grant new rights. This is
not a general Korean intent parser. Unsupported language needs clarification.
"""
import re
from copy import deepcopy

from backend.agent.state import DateRange

TEAM_ALLOW = re.compile(
    r'(?:(?:(?:LG|SK|KT|KCC|DB|삼성|정관장|소노|한국가스공사|현대모비스)(?:경기)?가?)?'
    r'(?:없으면|없다면|없을경우))?(?:다른팀|타팀)도?'
    r'(?:괜찮아|괜찮아요|가능해|가능해요|허용해|허용해줘|허용합니다)', re.IGNORECASE)
TEAM_DENY = re.compile(r'(?:다른팀|타팀)(?:은|는|도|을)?(?:안돼|안되|안됩|허용하지|추천하지|싫|제외|금지|취소|철회)|경기만추천|[A-Za-z]+만추천|아니면추천하지|팀(?:은|도|을)?(?:바꾸지|변경하지|그대로|유지)')
DATE_DENY = re.compile(r'(?:다른날짜|대체날짜|대안날짜|날짜변경)(?:은|는|도|를)?(?:안|허용하지|금지|취소|철회)|날짜(?:는|도|를)?(?:바꾸지|변경하지|그대로|유지)')
UNCERTAIN = re.compile(r'예시|예를|인용|라고|말했|말한|가정|아마|글쎄|모르|어떨|괜찮을|않|아니|아님|아냐|취소|철회|금지|제외')
DATE_ALLOW = re.compile(r'대체날짜(?::|는|로)(.+?)(?:을|를)?(?:허용해|허용해줘|허용합니다|괜찮아)')
ISO_RANGE = re.compile(r'(\d{4}-\d{2}-\d{2})(?:~(\d{4}-\d{2}-\d{2}))?')
TEAM_CONFIRMATION_WARNING = '다른 팀 허용 여부를 확인해 주세요. 명확한 허용 전에는 팀 조건을 완화하지 않습니다.'


def verify_permissions(
        message: str, previous: dict, *, follow_up: bool, allow_other_teams: bool | None = None,
) -> tuple[dict, list[str]]:
    permission = deepcopy(previous) if follow_up else {}
    permission = {'team': bool(permission.get('team', False)), 'date_ranges': permission.get('date_ranges', [])}
    compact = re.sub(r'\s+', '', message)
    clauses = [part for part in re.split(r'[.!?。]', compact) if part]
    uncertain = bool(UNCERTAIN.search(compact) or '?' in compact or '？' in compact or '"' in compact or "'" in compact)
    warnings = []

    scoped = any(word in compact for word in ('다른팀', '타팀', '대체날짜', '다른날짜', '대안날짜', '날짜변경'))
    revoke_all = not scoped and bool(re.search(r'(?:허용|동의|완화|그건).*(?:취소|철회)', compact))
    text_team = None
    if revoke_all or TEAM_DENY.search(compact):
        text_team = False
    elif not uncertain and any(TEAM_ALLOW.fullmatch(part) for part in clauses):
        text_team = True

    if allow_other_teams is not None:
        permission['team'] = allow_other_teams
        if text_team is not None and text_team != allow_other_teams:
            applied = '허용' if allow_other_teams else '미허용'
            warnings.append(f'메시지와 체크박스 설정이 달라 체크박스의 다른 팀 추천 설정({applied})을 적용했습니다.')
    elif text_team is not None:
        permission['team'] = text_team
    elif '다른팀' in compact or '타팀' in compact:
        permission['team'] = False
        warnings.append(TEAM_CONFIRMATION_WARNING)

    if revoke_all:
        permission['date_ranges'] = []
        if allow_other_teams is True:
            warnings.append('대체 날짜 허용 철회를 반영했습니다.')
        else:
            warnings.append('허용 철회를 반영했습니다. 자동 조건 완화를 중단합니다.')
        return permission, warnings

    if DATE_DENY.search(compact):
        permission['date_ranges'] = []
    else:
        directives = [DATE_ALLOW.fullmatch(part) for part in clauses]
        directives = [match for match in directives if match]
        dates = []
        valid = not uncertain and len(directives) == 1
        if valid:
            parts = directives[0].group(1).split(',')
            valid = 1 <= len(parts) <= 3
            for part in parts:
                match = ISO_RANGE.fullmatch(part)
                if not match:
                    valid = False
                    break
                try:
                    value = DateRange(from_date=match[1], to_date=match[2] or match[1]).model_dump(mode='json')
                except ValueError:
                    valid = False
                    break
                if value not in dates:
                    dates.append(value)
        if valid:
            permission['date_ranges'] = dates
        elif any(word in compact for word in ('대체날짜', '대안날짜', '다른날짜')):
            permission['date_ranges'] = []
            warnings.append('대체 날짜 허용을 확인해 주세요. 예: 대체 날짜: 2026-11-20 허용해. 확인 전에는 날짜를 변경하지 않습니다.')
    return permission, warnings
