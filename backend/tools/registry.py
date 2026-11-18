from dataclasses import dataclass
from typing import Annotated, Callable
from urllib.parse import quote, unquote

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from backend.config import Settings, load_settings
from backend.schemas import (Arena, ArenaInput, GameCandidate, GameDetail, GameDetailInput,
                             SearchGamesInput, ToolFailure, ToolMeta, ToolSuccess, Weather,
                             WeatherInput, failure)
from backend.tools.kakao import search_arena
from backend.tools.kbl import get_kbl_game_detail, search_kbl_games
from backend.tools.weather import get_weather


@dataclass(frozen=True)
class ToolDefinition:
    description: str
    input_model: type[BaseModel]
    output_type: object
    handler: Callable
    kind: str = 'external'


TOOLS = {
    'search_kbl_games': ToolDefinition('날짜 범위의 KBL 일정 후보 조회', SearchGamesInput, list[GameCandidate], search_kbl_games),
    'get_kbl_game_detail': ToolDefinition('후보 gmkey 기반 KBL 상세 조회', GameDetailInput, GameDetail, get_kbl_game_detail),
    'search_arena': ToolDefinition('카카오 키워드로 경기장 장소 후보 검색', ArenaInput, list[Arena], search_arena),
    'get_weather': ToolDefinition('좌표와 시각의 기상청 단기예보 조회', WeatherInput, Weather, get_weather),
}


def tool_specs() -> list[dict]:
    return [{'name': name, 'description': tool.description, 'kind': tool.kind,
             'input_schema': tool.input_model.model_json_schema(),
             'output_schema': result_adapter(tool).json_schema()}
            for name, tool in TOOLS.items()]


def result_adapter(tool: ToolDefinition) -> TypeAdapter:
    return TypeAdapter(Annotated[ToolSuccess[tool.output_type] | ToolFailure, Field(discriminator='ok')])


def redact_result(value, settings: Settings):
    """Remove credential echoes from every string, including upstream field names."""
    variants = set()
    for secret in (settings.kakao_key, settings.kma_key):
        if secret:
            variants.update((secret, unquote(secret), quote(unquote(secret), safe='')))

    def clean(item):
        if isinstance(item, str):
            for secret in sorted(variants, key=len, reverse=True):
                item = item.replace(secret, '[REDACTED]')
            return item
        if isinstance(item, list):
            return [clean(part) for part in item]
        if isinstance(item, dict):
            return {clean(key): clean(part) for key, part in item.items()}
        return item

    return clean(value)


def invoke(name: str, arguments: dict, settings: Settings | None = None):
    tool = TOOLS.get(name)
    if tool is None:
        return failure('INVALID_INPUT', '등록되지 않은 Tool입니다.', ToolMeta(source='registry'))
    try:
        args = tool.input_model.model_validate(arguments)
    except ValidationError:
        return failure('INVALID_INPUT', 'Tool 입력 형식을 확인하세요.', ToolMeta(source='registry'))
    try:
        config = settings or load_settings()
        result = tool.handler(args, config)
        safe_result = redact_result(result.model_dump(mode='json'), config)
        return result_adapter(tool).validate_python(safe_result)
    except Exception:
        # Isolate one tool's unexpected error; never serialize its exception.
        return failure('INTERNAL_ERROR', 'Tool 내부 처리 중 오류가 발생했습니다.', ToolMeta(source='registry'))
