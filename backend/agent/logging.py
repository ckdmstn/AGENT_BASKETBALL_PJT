import json
import logging
import sqlite3
from typing import get_args

from backend.agent.events import AgentEvent
from backend.agent.state import ConditionKey, ToolName
from backend.config import Settings
from backend.database import Database
from backend.schemas import ErrorCode
from backend.tools.registry import redact_result


NODES = {'analyze', 'plan', 'execute_tools', 'evaluate', 'replan', 'respond'}
TOOLS = get_args(ToolName)
ERROR_CODES = get_args(ErrorCode)
DECISION_REASONS = {
    'analyze': 'intent_and_condition_extraction',
    'plan': 'tools_for_condition_verification',
    'respond': 'verified_facts_rendering',
}
logger = logging.getLogger(__name__)


def safe_payload(event: AgentEvent) -> dict:
    payload = event.payload
    result = {}
    if event.event_type in ('NODE_COMPLETED', 'TOOL_RESPONDED'):
        result.update({key: payload[key] for key in ('ok', 'cached') if type(payload.get(key)) is bool})
        if payload.get('error_code') in ERROR_CODES:
            result['error_code'] = payload['error_code']
    elif event.event_type == 'LLM_DECISION':
        if event.node_name in DECISION_REASONS:
            result['reason_code'] = DECISION_REASONS[event.node_name]
        if payload.get('intent') in ('plan', 'follow_up', 'help', 'greeting'):
            result['intent'] = payload['intent']
        for key, allowed in (('changed_fields', get_args(ConditionKey)), ('tools', TOOLS)):
            if isinstance(payload.get(key), list):
                result[key] = [value for value in payload[key] if value in allowed]
        if payload.get('factual_output') == 'python_verified':
            result['factual_output'] = 'python_verified'
    elif event.event_type == 'REPLAN_STARTED':
        result['reason_code'] = 'authorized_condition_relaxation'
        if type(payload.get('attempt')) is int:
            result['attempt'] = payload['attempt']
        if isinstance(payload.get('changes'), dict):
            result['changed_fields'] = [key for key in payload['changes'] if key in get_args(ConditionKey)]
    elif event.event_type in ('RUN_COMPLETED', 'RUN_FAILED'):
        result.update({key: payload[key] for key in ('replan_count', 'recommendation_count')
                       if type(payload.get(key)) is int})
    return result


class LoggingAgent:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings

    def __call__(self, event: AgentEvent) -> None:
        ids = [event.session_id, event.run_id]
        if redact_result(ids, self.settings) != ids:
            return
        # Best-effort logging should wait less than user-facing writes on lock contention.
        try:
            with self.db.connection(write=True, timeout=0.05) as conn:
                conn.execute(
                    '''INSERT INTO agent_events
                       (session_id, run_id, sequence_no, timestamp, event_type, node_name, tool_name, payload)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(session_id, run_id, sequence_no) DO NOTHING''',
                    (event.session_id, event.run_id, event.sequence_no, event.timestamp.isoformat(timespec='microseconds'),
                     event.event_type, event.node_name if event.node_name in NODES else None,
                     event.tool_name if event.tool_name in TOOLS else None,
                     json.dumps(safe_payload(event))),
                )
        except sqlite3.Error:
            logger.warning('Agent event was not saved to SQLite.')
