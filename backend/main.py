from functools import lru_cache
from sqlite3 import Error as SQLiteError

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent.graph import AgentRunner
from backend.agent.logging import LoggingAgent
from backend.agent.sessions import SQLiteSessions
from backend.agent.state import ChatRequest, ChatResponse
from backend.config import ROOT, load_settings
from backend.database import Database, get_database
from backend.logs import router as logs_router
from backend.plans import router as plans_router

app = FastAPI(title='KBL GO', version='0.2.0', description='LangGraph KBL 직관 추천 Agent')
app.include_router(plans_router)
app.include_router(logs_router)
frontend = ROOT / 'frontend'
app.mount('/static', StaticFiles(directory=frontend), name='static')


@app.get('/', include_in_schema=False)
def web_ui() -> FileResponse:
    return FileResponse(frontend / 'index.html')


@lru_cache
def get_agent_runner(db: Database = Depends(get_database)) -> AgentRunner:
    settings = load_settings()
    return AgentRunner(settings=settings, sessions=SQLiteSessions(db), event_subscriber=LoggingAgent(db, settings))


@app.exception_handler(SQLiteError)
async def database_error(_request, _exc):
    return JSONResponse(status_code=503, content={'detail': '저장소를 사용할 수 없습니다.'})


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
