from time import perf_counter
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from backend.agent.events import EventBus
from backend.agent.llm import JsonLLM
from backend.agent.nodes import Nodes, next_alternative
from backend.agent.permissions import TEAM_CONFIRMATION_WARNING, verify_permissions
from backend.agent.sessions import MemorySessions
from backend.agent.state import AgentState, ChatRequest, ChatResponse, Conditions
from backend.config import load_settings
from backend.tools.registry import invoke, redact_result


def build_graph(nodes: Nodes):
    builder = StateGraph(AgentState)
    for name in ('analyze', 'plan', 'execute_tools', 'evaluate', 'replan', 'respond'):
        builder.add_node(name, nodes.wrapped(name))
    builder.add_edge(START, 'analyze')
    builder.add_edge('analyze', 'plan')
    builder.add_conditional_edges('plan', lambda s: 'execute_tools' if s['tasks'] and not s['fatal'] else 'respond',
                                  ['execute_tools', 'respond'])
    builder.add_edge('execute_tools', 'evaluate')
    builder.add_conditional_edges('evaluate', lambda s: 'replan' if next_alternative(s) else 'respond', ['replan', 'respond'])
    builder.add_edge('replan', 'plan')
    builder.add_edge('respond', END)
    return builder.compile()


class AgentRunner:
    def __init__(self, llm=None, tool_invoker=None, settings=None, sessions=None, *, event_subscriber=None):
        self.settings = settings or load_settings()
        self.sessions = sessions or MemorySessions()
        self.event_subscriber = event_subscriber
        self.graph = build_graph(Nodes(llm or JsonLLM(self.settings), self.settings, tool_invoker or invoke))

    def run(self, message: str, session_id: str | None = None) -> ChatResponse:
        request = ChatRequest(message=message, session_id=session_id)
        sid, rid = request.session_id or str(uuid4()), str(uuid4())
        started = perf_counter()
        with self.sessions.lock:
            previous = self.sessions.load(sid) or {}
            checked, permission_warnings = verify_permissions(
                request.message, previous.get('permissions', {}), follow_up=True)
            if previous:
                self.sessions.restrict_permissions(sid, checked)
                previous = self.sessions.load(sid)
            bus = EventBus(sid, rid)
            if self.event_subscriber is not None:
                bus.subscribe(self.event_subscriber)
            conditions = Conditions().model_dump(mode='json')
            state = AgentState(session_id=sid, run_id=rid, user_message=request.message, intent='plan',
                               conditions=conditions, active_conditions=conditions.copy(),
                               last_conditions=previous.get('conditions', {}), last_summary=previous.get('summary', ''),
                               last_permissions=previous.get('permissions', {}), permissions={},
                               tasks=[], task_results={}, games=[], details={}, arena_info={}, arena_reasons={}, weather_info={},
                               eligible=[], excluded=[], replan_count=0, max_replans=3, relaxation_history=[],
                               answer='', errors=[], warnings=[], fatal=False, bus=bus)
            try:
                result = self.graph.invoke(state, {'recursion_limit': 40})
            except Exception:
                result = state
                result['fatal'] = True
                result['errors'].append({'code':'INTERNAL_ERROR', 'message':'Agent 실행에 실패했습니다.', 'tool_name':None})
                result['answer'] = '요청을 처리하지 못했습니다.'
            bus.publish('RUN_FAILED' if result['fatal'] else 'RUN_COMPLETED',
                        payload={'replan_count': result['replan_count'], 'recommendation_count':len(result['eligible'])})
            response = ChatResponse(session_id=sid, run_id=rid, conditions=result['conditions'],
                                    active_conditions=result['active_conditions'], answer=result['answer'],
                                    recommendations=result['eligible'], excluded=result['excluded'],
                                    replan_count=result['replan_count'], relaxation_history=result['relaxation_history'],
                                    errors=result['errors'], warnings=list(dict.fromkeys(result['warnings'])),
                                    events=[event.model_dump(mode='json') for event in bus.events],
                                    elapsed_ms=round((perf_counter()-started)*1000, 2))
            response = ChatResponse.model_validate(redact_result(response.model_dump(mode='json'), self.settings))
            stored_permissions = previous.get('permissions', {})
            if not result['fatal'] and result['intent'] in ('plan','follow_up'):
                summary = '추천 ID: ' + ','.join(item.match_id for item in response.recommendations)
                self.sessions.save(sid, response.conditions, summary, result['permissions'])
                stored_permissions = result['permissions']
            if stored_permissions.get('team'):
                return response.model_copy(update={'team_permission': 'allowed'})
            if TEAM_CONFIRMATION_WARNING in permission_warnings:
                return response.model_copy(update={'team_permission': 'confirmation_required'})
            return response
