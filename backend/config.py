"""Load secrets without exposing them through repr or API responses."""
import os
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9), name='Asia/Seoul')


@dataclass(frozen=True)
class Settings:
    kakao_key: str = field(default='', repr=False)
    kma_key: str = field(default='', repr=False)
    kbl_base_url: str = 'https://api.kbl.or.kr'
    kbl_team_code: str = 'XX'
    timeout: float = 15


def load_settings(*, use_env_file: bool = True) -> Settings:
    if use_env_file:
        load_dotenv(ROOT / '.env', override=False)
    try:
        timeout = float(os.getenv('API_TIMEOUT_SECONDS', '15'))
        if not 0 < timeout <= 60:
            timeout = 15
    except ValueError:
        timeout = 15
    return Settings(kakao_key=os.getenv('KAKAO_REST_API_KEY', '').strip(),
                    kma_key=os.getenv('KMA_SERVICE_KEY', '').strip(),
                    kbl_base_url=os.getenv('KBL_BASE_URL', 'https://api.kbl.or.kr').rstrip('/'),
                    kbl_team_code=os.getenv('KBL_TEAM_CODE', 'XX'), timeout=timeout)
