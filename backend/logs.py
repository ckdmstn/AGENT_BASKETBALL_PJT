import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from backend.agent.events import AgentEvent
from backend.database import Database, get_database


class LogSummary(BaseModel):
    session_id: str
    run_count: int
    event_count: int
    last_event_at: datetime


class LogRun(BaseModel):
    run_id: str
    events: list[AgentEvent]


class SessionLog(BaseModel):
    session_id: str
    runs: list[LogRun]


router = APIRouter(prefix='/api/logs', tags=['logs'])
DB = Annotated[Database, Depends(get_database)]


@router.get('')
def list_logs(db: DB) -> list[LogSummary]:
    with db.connection() as conn:
        rows = conn.execute(
            '''SELECT session_id, COUNT(DISTINCT run_id) AS run_count, COUNT(*) AS event_count,
                      MAX(timestamp) AS last_event_at
               FROM agent_events GROUP BY session_id ORDER BY last_event_at DESC, session_id'''
        )
        return [LogSummary.model_validate(dict(row)) for row in rows]


@router.get('/{session_id}')
def read_logs(session_id: str, db: DB) -> SessionLog:
    runs: dict[str, LogRun] = {}
    with db.connection() as conn:
        rows = conn.execute(
            '''SELECT *, MIN(timestamp) OVER (PARTITION BY run_id) AS run_started
               FROM agent_events WHERE session_id = ? ORDER BY run_started, run_id, sequence_no''',
            (session_id,),
        )
        for row in rows:
            event = AgentEvent.model_validate({**dict(row), 'payload': json.loads(row['payload'])})
            if event.run_id not in runs:
                runs[event.run_id] = LogRun(run_id=event.run_id, events=[])
            runs[event.run_id].events.append(event)
    if not runs:
        raise HTTPException(404, '실행 로그를 찾을 수 없습니다.')
    return SessionLog(session_id=session_id, runs=list(runs.values()))


@router.delete('/{session_id}', status_code=204)
def delete_logs(session_id: str, db: DB) -> Response:
    with db.connection(write=True) as conn:
        if not conn.execute('DELETE FROM agent_events WHERE session_id = ?', (session_id,)).rowcount:
            raise HTTPException(404, '실행 로그를 찾을 수 없습니다.')
    return Response(status_code=204)
