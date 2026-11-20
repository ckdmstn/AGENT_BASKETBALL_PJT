from datetime import date, time
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from backend.schemas import Arena, GameCandidate, GameDetail, Weather


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class DateRange(StrictModel):
    from_date: date
    to_date: date

    @model_validator(mode='after')
    def check_range(self):
        if not 0 <= (self.to_date - self.from_date).days <= 30:
            raise ValueError('Date range must be ordered and at most 31 days')
        return self


class Conditions(StrictModel):
    date_range: DateRange | None = None
    start_after: time | None = None
    region: str | None = Field(default=None, max_length=100)
    preferred_team: str | None = Field(default=None, max_length=100)
    weather_preference: Literal['low_rain'] | None = None
    max_precipitation_probability_pct: float | None = Field(default=None, ge=0, le=100)
    fallback_teams_allowed: bool = False
    alternative_date_ranges: list[DateRange] = Field(default_factory=list, max_length=3)


ConditionKey = Literal['date_range', 'start_after', 'region', 'preferred_team', 'weather_preference',
                       'max_precipitation_probability_pct', 'fallback_teams_allowed', 'alternative_date_ranges']


class Analysis(StrictModel):
    intent: Literal['plan', 'follow_up', 'help', 'greeting']
    conditions: Conditions = Field(default_factory=Conditions)
    changed_fields: list[ConditionKey] = Field(default_factory=list)
    reason: str = Field(default='', max_length=300)

    @model_validator(mode='after')
    def explicit_updates(self):
        if set(self.changed_fields) != self.conditions.model_fields_set:
            raise ValueError('Changed fields must exactly match explicitly supplied conditions')
        return self


ToolName = Literal['search_kbl_games', 'get_kbl_game_detail', 'search_arena', 'get_weather']


class WorkPlan(StrictModel):
    tools: list[ToolName] = Field(max_length=4)
    reason: str = Field(default='', max_length=300)


class Narration(StrictModel):
    # LLM chooses a natural-language lead; verified facts are rendered by Python.
    lead: Literal['조건 검증 결과를 안내합니다.', '확인되지 않은 정보와 조회 한계를 함께 안내합니다.',
                  '안녕하세요. 원하는 직관 조건을 알려 주세요.', '추천을 위해 필요한 조건을 확인해 주세요.']


class ConditionCheck(StrictModel):
    status: Literal['met', 'unmet', 'unknown']
    reason: str


class Assessment(StrictModel):
    match_id: str
    game: GameCandidate
    detail: GameDetail | None = None
    arena: Arena | None = None
    weather: Weather | None = None
    checks: dict[str, ConditionCheck]
    status: Literal['met', 'unmet', 'unknown']


class AgentError(StrictModel):
    code: str
    message: str
    tool_name: str | None = None


class ChatRequest(StrictModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    message: str = Field(min_length=1, max_length=4000)
    allow_other_teams: StrictBool | None = None


class ChatResponse(StrictModel):
    session_id: str
    run_id: str
    conditions: Conditions
    active_conditions: Conditions
    team_permission: Literal['allowed', 'denied', 'confirmation_required'] = 'denied'
    answer: str
    recommendations: list[Assessment]
    excluded: list[Assessment]
    replan_count: int = Field(ge=0, le=3)
    relaxation_history: list[dict]
    events: list[dict]
    errors: list[AgentError]
    warnings: list[str]
    elapsed_ms: float


class AgentState(TypedDict, total=False):
    session_id: str
    run_id: str
    user_message: str
    allow_other_teams: bool | None
    intent: str
    conditions: dict
    active_conditions: dict
    last_conditions: dict
    last_summary: str
    last_permissions: dict
    permissions: dict
    tasks: list[str]
    task_results: dict
    games: list[dict]
    details: dict
    arena_info: dict
    arena_reasons: dict[str, str]
    weather_info: dict
    eligible: list[dict]
    excluded: list[dict]
    replan_count: int
    max_replans: int
    relaxation_history: list[dict]
    answer: str
    errors: list[dict]
    warnings: list[str]
    fatal: bool
    bus: object
