import math
from datetime import datetime, timedelta
from urllib.parse import unquote

from pydantic import ValidationError

from backend.config import KST, Settings
from backend.schemas import ToolFailure, ToolMeta, ToolSuccess, Weather, WeatherInput, failure
from backend.tools.http import get_json


def grid_coordinates(lat: float, lon: float) -> tuple[int, int]:
    """KMA Lambert conformal conic grid, 5 km. See data portal conversion guide."""
    rad = math.pi / 180
    re, slat1, slat2 = 6371.00877 / 5, 30 * rad, 60 * rad
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
        math.tan(math.pi / 4 + slat2 / 2) / math.tan(math.pi / 4 + slat1 / 2))
    sf = math.tan(math.pi / 4 + slat1 / 2) ** sn * math.cos(slat1) / sn
    ro = re * sf / math.tan(math.pi / 4 + 38 * rad / 2) ** sn
    ra = re * sf / math.tan(math.pi / 4 + lat * rad / 2) ** sn
    theta = ((lon - 126 + 180) % 360 - 180) * rad * sn
    return math.floor(ra * math.sin(theta) + 43 + 0.5), math.floor(ro - ra * math.cos(theta) + 136 + 0.5)


def forecast_base(now: datetime) -> datetime:
    # Conservative availability margin: publication hour + 10 minutes.
    safe = now.astimezone(KST) - timedelta(minutes=10)
    for hour in (23, 20, 17, 14, 11, 8, 5, 2):
        candidate = safe.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate <= safe:
            return candidate
    return (safe - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)


def get_weather(args: WeatherInput, settings: Settings):
    meta = ToolMeta(source='KMA getVilageFcst', actual_query=args.model_dump(mode='json'))
    if not settings.kma_key:
        return failure('MISSING_API_KEY', 'KMA_SERVICE_KEY가 필요합니다.', meta)
    now = datetime.now(KST)
    target = args.date_time.astimezone(KST).replace(minute=0, second=0, microsecond=0)
    if target.date() < now.date() or target.date() > now.date() + timedelta(days=3):
        return failure('UNSUPPORTED_DATE', '단기예보 조회 대상 날짜 범위 밖입니다.', meta)
    if not (30 <= args.lat <= 44 and 120 <= args.lon <= 133):
        return failure('INVALID_INPUT', '국내 단기예보 격자 범위의 좌표가 필요합니다.', meta)
    nx, ny = grid_coordinates(args.lat, args.lon)
    base = forecast_base(now)
    params = {'base_date': base.strftime('%Y%m%d'), 'base_time': base.strftime('%H%M'),
              'nx': nx, 'ny': ny, 'pageNo': 1, 'numOfRows': 1500, 'dataType': 'JSON'}
    meta.actual_query.update(params)
    meta.warnings.append('발표 후 10분 여유를 적용하며 대상 시각의 실제 응답 존재를 검사합니다.')
    body = get_json('https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst',
                    params={**params, 'serviceKey': unquote(settings.kma_key)}, headers={}, settings=settings, meta=meta)
    if isinstance(body, ToolFailure):
        return body
    try:
        code = body['response']['header']['resultCode']
        meta.service_code = str(code)
        if str(code) != '00':
            return failure('NO_RESULT' if str(code) == '03' else 'UPSTREAM_ERROR', '기상청 서비스 오류입니다.', meta)
        payload = body['response']['body']
        rows = payload['items']['item']
        if not isinstance(rows, list):
            raise TypeError
        if int(payload.get('totalCount', len(rows))) > len(rows):
            return failure('MISSING_FIELD', '예보 응답 페이지가 불완전합니다.', meta)
        matching = [r for r in rows if r['fcstDate'] == target.strftime('%Y%m%d') and r['fcstTime'] == target.strftime('%H%M')]
        if not matching:
            return failure('UNSUPPORTED_DATE', '해당 시각의 예보가 응답에 없습니다.', meta)
        values = {r['category']: r['fcstValue'] for r in matching}
        if not any(k in values for k in ('TMP', 'POP', 'PCP')):
            return failure('MISSING_FIELD', '대상 시각의 날씨 필드가 없습니다.', meta)
        weather = Weather(forecast_at=base, temperature_c=values.get('TMP'),
                          precipitation_probability_pct=values.get('POP'),
                          precipitation_mm=values.get('PCP'), available=True)
    except (KeyError, TypeError, ValueError, ValidationError):
        return failure('MISSING_FIELD', '기상청 필수 필드가 누락되거나 변경되었습니다.', meta)
    return ToolSuccess(data=weather, meta=meta)
