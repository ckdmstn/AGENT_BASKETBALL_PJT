"""Never return upstream bodies, exception strings, or credential-bearing URLs."""
import requests

from backend.config import Settings
from backend.schemas import ToolFailure, ToolMeta, failure


def get_json(url: str, *, params: dict, headers: dict, settings: Settings,
             meta: ToolMeta) -> dict | list | ToolFailure:
    try:
        response = requests.get(url, params=params, headers=headers, timeout=settings.timeout)
        meta.http_status = response.status_code
        if not 200 <= response.status_code < 300:
            try:
                error_body = response.json()
                if isinstance(error_body, dict):
                    code = error_body.get('resultCode', error_body.get('code'))
                    if isinstance(code, (str, int)):
                        meta.service_code = str(code)[:40]
            except ValueError:
                pass
            return failure('UPSTREAM_ERROR', '외부 API HTTP 오류입니다.', meta)
        body = response.json()
    except requests.Timeout:
        return failure('TIMEOUT', '외부 API 응답 시간이 초과되었습니다.', meta)
    except (requests.RequestException, ValueError):
        return failure('UPSTREAM_ERROR', '외부 API 연결 또는 JSON 응답 오류입니다.', meta)
    if not isinstance(body, (dict, list)):
        return failure('MISSING_FIELD', '외부 API 응답 구조가 예상과 다릅니다.', meta)
    if isinstance(body, dict):
        # Keys only; values may contain echoed tokens or server internals.
        meta.response_fields = sorted(str(key) for key in body)[:40]
    return body
