from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.config import KST

EventType = Literal['NODE_STARTED', 'NODE_COMPLETED', 'TOOL_REQUESTED', 'TOOL_RESPONDED',
                    'LLM_DECISION', 'REPLAN_STARTED', 'RUN_COMPLETED', 'RUN_FAILED']


class AgentEvent(BaseModel):
    session_id: str
    run_id: str
    sequence_no: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(KST))
    event_type: EventType
    node_name: str | None = None
    tool_name: str | None = None
    payload: dict = Field(default_factory=dict)


class EventBus:
    """Per-run publisher. Subscribers see copies and cannot interrupt the agent."""
    def __init__(self, session_id: str, run_id: str):
        self.session_id, self.run_id = session_id, run_id
        self.events: list[AgentEvent] = []
        self._subscribers = []

    def subscribe(self, subscriber):
        self._subscribers.append(subscriber)

    def publish(self, event_type: EventType, *, node_name=None, tool_name=None, payload=None):
        event = AgentEvent(session_id=self.session_id, run_id=self.run_id,
                           sequence_no=len(self.events) + 1, event_type=event_type,
                           node_name=node_name, tool_name=tool_name, payload=payload or {})
        self.events.append(event)
        for subscriber in tuple(self._subscribers):
            try:
                subscriber(event.model_copy(deep=True))
            except Exception:
                pass
