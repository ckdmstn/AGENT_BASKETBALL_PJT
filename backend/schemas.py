from datetime import date as Date, datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.config import KST

ErrorCode = Literal['INVALID_INPUT', 'MISSING_API_KEY', 'UPSTREAM_ERROR', 'TIMEOUT',
                    'NO_RESULT', 'UNSUPPORTED_DATE', 'MISSING_FIELD', 'INTERNAL_ERROR']
T = TypeVar('T')


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class SearchGamesInput(InputModel):
    from_date: Date = Field(default_factory=lambda: datetime.now(KST).date())
    to_date: Date = Field(default_factory=lambda: datetime.now(KST).date())
    team_code: str | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode='after')
    def ordered_dates(self):
        if self.from_date > self.to_date:
            raise ValueError('from_date must not exceed to_date')
        return self


class GameDetailInput(InputModel):
    match_id: str = Field(min_length=1, max_length=100)
    date: Date | None = None


class ArenaInput(InputModel):
    venue_name: str = Field(min_length=1, max_length=200)
    region_hint: str | None = Field(default=None, max_length=100)


class WeatherInput(InputModel):
    date_time: datetime
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)

    @model_validator(mode='after')
    def timezone_required(self):
        if self.date_time.utcoffset() is None:
            raise ValueError('timezone offset required')
        return self


class GameCandidate(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    start_at: datetime | None = None
    venue_name: str | None = None
    source: str
    season_grade: int | None = None
    season_category: str | None = None


class GameDetail(BaseModel):
    match_id: str
    start_at: datetime | None = None
    home_team: str | None = None
    away_team: str | None = None
    venue_name: str | None = None
    status: str | None = None


class Arena(BaseModel):
    name: str
    road_address: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    place_url: str | None = None
    verified_kbl_arena: bool = False


class Weather(BaseModel):
    forecast_at: datetime = Field(description='실제 예보 대상 정시 (Asia/Seoul). 요청 시각을 KST로 변환한 뒤 분 이하를 내린 시각.')
    issued_at: datetime = Field(description='조회에 사용한 예보 발표 기준시각 (base_date/base_time, Asia/Seoul).')
    temperature_c: float | None = None
    precipitation_probability_pct: float | None = Field(default=None, ge=0, le=100,
        description='강수확률(%). null은 미제공/미확인이며 0%나 강수 조건 충족을 뜻하지 않는다.')
    precipitation_mm: str | None = None
    available: bool = Field(description='대상 시각의 기온·강수확률·강수량 중 하나 이상 제공됨. 모든 항목 존재 또는 사용자 조건 충족을 뜻하지 않는다.')


class ToolMeta(BaseModel):
    source: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    actual_query: dict = Field(default_factory=dict)
    http_status: int | None = None
    service_code: str | None = None
    response_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolError(BaseModel):
    code: ErrorCode
    message: str


class ToolSuccess(BaseModel, Generic[T]):
    model_config = ConfigDict(extra='forbid')
    ok: Literal[True] = True
    data: T
    error: None = None
    meta: ToolMeta


class ToolFailure(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ok: Literal[False] = False
    data: None = None
    error: ToolError
    meta: ToolMeta


ToolResult = Annotated[ToolSuccess[T] | ToolFailure, Field(discriminator='ok')]


def failure(code: ErrorCode, message: str, meta: ToolMeta) -> ToolFailure:
    return ToolFailure(error=ToolError(code=code, message=message), meta=meta)
