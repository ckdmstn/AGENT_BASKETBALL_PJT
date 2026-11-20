from datetime import datetime
from urllib.parse import quote

from pydantic import ValidationError

from backend.config import KST, Settings
from backend.schemas import (GameCandidate, GameDetail, GameDetailInput, SearchGamesInput,
                             ToolFailure, ToolMeta, ToolSuccess, failure)
from backend.tools.http import get_json


def search_kbl_games(args: SearchGamesInput, settings: Settings):
    params = {'fromDate': args.from_date.strftime('%Y%m%d'), 'toDate': args.to_date.strftime('%Y%m%d'),
              'tcodeList': args.team_code or 'all'}
    meta = ToolMeta(source='KBL', actual_query={**params, 'Channel': 'WEB', 'TeamCode': settings.kbl_team_code})
    meta.warnings.append('목록에는 EASL·D리그가 섞일 수 있습니다. season_grade/category를 확인하세요.')
    body = get_json(settings.kbl_base_url + '/match/list',
                    params=params,
                    headers={'Channel': 'WEB', 'TeamCode': settings.kbl_team_code},
                    settings=settings, meta=meta)
    if isinstance(body, ToolFailure):
        return body
    if isinstance(body, dict):
        code = body.get('resultCode')
        meta.service_code = str(code) if isinstance(code, (str, int)) else None
        if code is not None and code not in ('Success', 'SUCCESS', '00', 0):
            return failure('UPSTREAM_ERROR', 'KBL 서비스가 실패를 반환했습니다.', meta)
    if not isinstance(body, list):
        return failure('MISSING_FIELD', 'KBL 목록 응답 구조가 변경되었습니다.', meta)
    if not body:
        return failure('NO_RESULT', '해당 범위에 KBL 일정이 없습니다.', meta)
    try:
        games = []
        outside_range = 0
        for row in body:
            game_date = datetime.strptime(row['gameDate'], '%Y%m%d').date()
            if not args.from_date <= game_date <= args.to_date:
                outside_range += 1
                continue
            games.append(GameCandidate(match_id=row['gmkey'], home_team=row['tnameH'], away_team=row['tnameA'],
                                       start_at=start_time(row), venue_name=row.get('stadiumnameF') or row.get('stadiumname') or None,
                                       source='KBL', season_grade=row.get('seasonGrade'), season_category=row.get('seasonCategory')))
        meta.response_fields = sorted(body[0])
    except (KeyError, TypeError, ValueError, ValidationError):
        return failure('MISSING_FIELD', 'KBL 후보 필수 필드가 누락되거나 변경되었습니다.', meta)
    if outside_range:
        meta.warnings.append(f'KBL이 반환한 요청 범위 밖 일정 {outside_range}건을 제외했습니다.')
    if not games:
        return failure('NO_RESULT', '요청 날짜 범위에 해당하는 일정이 없습니다.', meta)
    return ToolSuccess(data=games, meta=meta)


def get_kbl_game_detail(args: GameDetailInput, settings: Settings):
    meta = ToolMeta(source='KBL', actual_query=args.model_dump(mode='json'))
    body = get_json(settings.kbl_base_url + '/match/' + quote(args.match_id, safe=''), params={},
                    headers={'Channel': 'WEB', 'TeamCode': settings.kbl_team_code}, settings=settings, meta=meta)
    if isinstance(body, ToolFailure):
        return body
    try:
        row = body['game']
        if row['gmkey'] != args.match_id:
            return failure('MISSING_FIELD', '요청 식별자와 상세 응답 식별자가 다릅니다.', meta)
        if args.date and row['gameDate'] != args.date.strftime('%Y%m%d'):
            return failure('MISSING_FIELD', '요청 날짜와 상세 응답 날짜가 다릅니다.', meta)
        detail = GameDetail(match_id=row['gmkey'], start_at=start_time(row),
                            home_team=row.get('tnameH'), away_team=row.get('tnameA'),
                            venue_name=row.get('stadiumnameF') or row.get('stadiumname') or None,
                            status='ended' if row.get('isEnded') == 1 else 'started' if row.get('isStarted') == 1 else None)
        meta.response_fields = sorted(row)
    except (KeyError, TypeError, ValueError, ValidationError):
        return failure('MISSING_FIELD', 'KBL 상세 필수 필드가 누락되거나 변경되었습니다.', meta)
    return ToolSuccess(data=detail, meta=meta)


def start_time(row: dict) -> datetime | None:
    if not row.get('gameStart'):
        return None
    return datetime.strptime(row['gameDate'] + row['gameStart'], '%Y%m%d%H%M').replace(tzinfo=KST)
