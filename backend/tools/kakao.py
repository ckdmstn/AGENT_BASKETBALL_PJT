from pydantic import ValidationError

from backend.config import Settings
from backend.schemas import Arena, ArenaInput, ToolFailure, ToolMeta, ToolSuccess, failure
from backend.tools.http import get_json


def search_arena(args: ArenaInput, settings: Settings):
    query = ' '.join(part for part in (args.region_hint, args.venue_name) if part)
    meta = ToolMeta(source='Kakao Local', actual_query={'query': query})
    if not settings.kakao_key:
        return failure('MISSING_API_KEY', 'KAKAO_REST_API_KEY가 필요합니다.', meta)
    body = get_json('https://dapi.kakao.com/v2/local/search/keyword.json', params={'query': query},
                    headers={'Authorization': 'KakaoAK ' + settings.kakao_key}, settings=settings, meta=meta)
    if isinstance(body, ToolFailure):
        return body
    documents = body.get('documents') if isinstance(body, dict) else None
    if not isinstance(documents, list):
        return failure('MISSING_FIELD', '카카오 documents 필드가 누락되거나 변경되었습니다.', meta)
    if not documents:
        return failure('NO_RESULT', '검색된 장소가 없습니다.', meta)
    try:
        arenas = [Arena(name=item['place_name'], road_address=item.get('road_address_name') or None,
                        address=item.get('address_name') or None, lat=item.get('y') or None,
                        lon=item.get('x') or None, place_url=item.get('place_url') or None)
                  for item in documents]
    except (KeyError, TypeError, ValidationError):
        return failure('MISSING_FIELD', '카카오 장소 필수 필드가 누락되거나 변경되었습니다.', meta)
    meta.warnings.append('검색 후보입니다. 실제 KBL 경기장인지 별도 확인이 필요합니다.')
    return ToolSuccess(data=arenas, meta=meta)
