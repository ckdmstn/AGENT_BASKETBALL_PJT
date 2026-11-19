from functools import lru_cache

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.agent.graph import AgentRunner
from backend.agent.state import ChatRequest, ChatResponse

app = FastAPI(title='KBL GO', version='0.2.0', description='LangGraph KBL 직관 추천 Agent')


@lru_cache
def get_agent_runner() -> AgentRunner:
    return AgentRunner()


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _exc):
    # Avoid FastAPI's default echo of potentially sensitive request inputs.
    return JSONResponse(status_code=422, content={'detail':'요청 형식을 확인해 주세요.'})


class HealthResponse(BaseModel):
    status: str


@app.get('/api/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok')


@app.post('/api/chat', response_model=ChatResponse)
def chat(request: ChatRequest, agent: AgentRunner = Depends(get_agent_runner)) -> ChatResponse:
    return agent.run(request.message, request.session_id)
