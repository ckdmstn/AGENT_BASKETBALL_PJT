import json
import re
from copy import deepcopy
from datetime import datetime

from backend.agent.evaluation import assess, requested_weather, team_matches, verified_arena
from backend.agent.llm import LLMError
from backend.agent.state import Analysis, Conditions, Narration, WorkPlan
from backend.config import KST
from backend.schemas import ToolFailure, ToolMeta, failure
from backend.tools.registry import redact_result

def next_alternative(state):
    if state['fatal'] or state['eligible'] or state['replan_count'] >= min(3, state['max_replans']):
        return None
    # Existing Tool contracts fold real auth/quota failures into UPSTREAM_ERROR.
    # Conservatively do not relax user conditions to work around service failures.
    if any(e['code'] in ('MISSING_API_KEY', 'INTERNAL_ERROR', 'UPSTREAM_ERROR', 'TIMEOUT') for e in state['errors']):
        return None
    original = Conditions.model_validate(state['conditions'])
    active = Conditions.model_validate(state['active_conditions'])
    if active.preferred_team and original.fallback_teams_allowed:
        return {'preferred_team': None}
    tried = {json.dumps(state['conditions'].get('date_range'), sort_keys=True)}
    tried.update(json.dumps(x['changes']['date_range'], sort_keys=True) for x in state['relaxation_history'] if 'date_range' in x['changes'])
    for alternative in original.alternative_date_ranges:
        value = alternative.model_dump(mode='json')
        if json.dumps(value, sort_keys=True) not in tried:
            return {'date_range': value}
    return None


class Nodes:
    def __init__(self, llm, settings, tool_invoker):
        self.llm, self.settings, self.invoke = llm, settings, tool_invoker

    def wrapped(self, name):
        def node(state):
            bus = state['bus']
            bus.publish('NODE_STARTED', node_name=name)
            try:
                getattr(self, name)(state)
            except LLMError as exc:
                state['errors'].append({'code': exc.code, 'message': 'LLM 처리에 실패했습니다.', 'tool_name': None})
                if name != 'respond':
                    state['fatal'] = True
                    state['tasks'] = []
                else:
                    state['answer'] = self.render(state, '확인되지 않은 정보와 조회 한계를 함께 안내합니다.')
            except Exception:
                state['errors'].append({'code': 'INTERNAL_ERROR', 'message': 'Agent 내부 처리 오류입니다.', 'tool_name': None})
                state['fatal'] = True
                state['tasks'] = []
                state['answer'] = '처리 중 오류가 발생했습니다. 조건과 설정을 확인해 주세요.'
            bus.publish('NODE_COMPLETED', node_name=name, payload={'ok': not state['fatal']})
            return state
        return node

    def ask(self, stage, payload, model):
        return self.llm.complete(stage, redact_result(payload, self.settings), model)

    def decision_reason(self, reason, state, fallback):
        """Short public summary only; sanitize before EventBus subscribers see it."""
        clean = ' '.join(redact_result(reason, self.settings).split())
        sensitive = re.search(r'api[ _-]?key|token|secret|password|authorization|bearer|traceback|exception|error|https?://|인증정보|비밀번호|예외', clean, re.IGNORECASE)
        message = ' '.join(state['user_message'].split())
        if (not clean or len(clean) > 120 or sensitive or '[REDACTED]' in clean
                or message in clean):
            return fallback
        return clean

    def analyze(self, state):
        result = self.ask('analyze', {'message': state['user_message'], 'current_date': datetime.now(KST).date().isoformat(),
                                     'last_conditions': state['last_conditions'], 'last_summary': state['last_summary']}, Analysis)
        state['intent'] = result.intent
        if result.intent == 'follow_up' and not state['last_conditions']:
            state['warnings'].append('이 세션의 이전 조건이 없습니다. 날짜와 조건을 다시 알려 주세요.')
        previous = state['last_conditions'] if result.intent == 'follow_up' else {}
        patch = result.conditions.model_dump(mode='json')
        merged = {**previous, **{k: patch[k] for k in result.changed_fields}}
        c = Conditions.model_validate(merged)
        state['conditions'] = c.model_dump(mode='json')
        state['active_conditions'] = deepcopy(state['conditions'])
        state['bus'].publish('LLM_DECISION', node_name='analyze',
                             payload={'intent': result.intent, 'changed_fields': result.changed_fields,
                                      'reason': self.decision_reason(result.reason, state, '요청 의도와 명시적으로 변경한 조건을 추출함')})

    def plan(self, state):
        c = Conditions.model_validate(state['active_conditions'])
        if state['fatal'] or state['intent'] in ('greeting', 'help') or not c.date_range:
            state['tasks'] = []
            return
        proposed = self.ask('plan', {'conditions': c.model_dump(mode='json'), 'replan_count': state['replan_count'],
                                    'cached_result_count': len(state['task_results'])}, WorkPlan)
        expected = ['search_kbl_games', 'get_kbl_game_detail', 'search_arena']
        if requested_weather(c):
            expected.append('get_weather')
        if proposed.tools != expected:
            raise LLMError('INVALID_TOOL_PLAN')
        state['tasks'] = proposed.tools
        state['bus'].publish('LLM_DECISION', node_name='plan',
                             payload={'tools': proposed.tools,
                                      'reason': self.decision_reason(proposed.reason, state, '조건 검증에 필요한 Tool을 종속 순서로 선택함')})

    def call(self, state, name, args):
        key = json.dumps([name, args], sort_keys=True)
        bus = state['bus']
        cached = key in state['task_results']
        if not cached:
            bus.publish('TOOL_REQUESTED', node_name='execute_tools', tool_name=name,
                        payload={'arguments': redact_result(args, self.settings)})
            try:
                result = self.invoke(name, args, self.settings)
            except Exception:
                result = failure('INTERNAL_ERROR', 'Tool 내부 처리 오류입니다.', ToolMeta(source='registry'))
            state['task_results'][key] = result.model_dump(mode='json')
        value = state['task_results'][key]
        code = None if value['ok'] else value['error']['code']
        bus.publish('TOOL_RESPONDED', node_name='execute_tools', tool_name=name,
                    payload={'cached': cached, 'ok': value['ok'], 'error_code': code})
        if not value['ok']:
            entry = {'code': code, 'message': value['error']['message'], 'tool_name': name}
            if entry not in state['errors']:
                state['errors'].append(entry)
        return value['data'] if value['ok'] else None

    def execute_tools(self, state):
        c = Conditions.model_validate(state['active_conditions'])
        rows = self.call(state, 'search_kbl_games', {'from_date': c.date_range.from_date.isoformat(), 'to_date': c.date_range.to_date.isoformat()})
        state['games'] = rows or []
        for g in state['games']:
            if g.get('season_category') != 'R' or g.get('season_grade') != 1:
                continue
            if c.preferred_team and not team_matches(c.preferred_team, g):
                continue
            mid = g['match_id']
            detail = self.call(state, 'get_kbl_game_detail', {'match_id': mid})
            if not detail:
                continue
            state['details'][mid] = detail
            venue = detail.get('venue_name')
            if not venue:
                continue
            # Do not inject requested region into search: it could select a wrong venue.
            places = self.call(state, 'search_arena', {'venue_name': venue})
            selected = verified_arena(venue, places or [])
            if not selected:
                continue
            state['arena_info'][mid] = selected.model_dump(mode='json')
            if 'get_weather' in state['tasks'] and detail.get('start_at') and selected.lat is not None and selected.lon is not None:
                weather = self.call(state, 'get_weather', {'date_time': detail['start_at'], 'lat': selected.lat, 'lon': selected.lon})
                if weather:
                    state['weather_info'][mid] = weather

    def evaluate(self, state):
        state['eligible'], state['excluded'] = [], []
        c = Conditions.model_validate(state['active_conditions'])
        for g in state['games']:
            mid = g['match_id']
            result = assess(g, state['details'].get(mid), state['arena_info'].get(mid), state['weather_info'].get(mid), c)
            target = 'eligible' if result.status == 'met' else 'excluded'
            state[target].append(result.model_dump(mode='json'))
        if requested_weather(c):
            state['eligible'].sort(key=lambda item: item['weather']['precipitation_probability_pct'])

    def replan(self, state):
        changes = next_alternative(state)
        if not changes:
            return
        updated = Conditions.model_validate({**state['active_conditions'], **changes})
        state['replan_count'] += 1
        state['active_conditions'] = updated.model_dump(mode='json')
        record = {'attempt': state['replan_count'], 'changes': changes}
        state['relaxation_history'].append(record)
        state['bus'].publish('REPLAN_STARTED', node_name='replan', payload=record)

    def respond(self, state):
        result = self.ask('respond', {'intent': state['intent'], 'has_dates': bool(state['conditions'].get('date_range')),
                                     'eligible_count': len(state['eligible']), 'unknown_count': sum(x['status']=='unknown' for x in state['excluded']),
                                     'error_count': len(state['errors'])}, Narration)
        state['bus'].publish('LLM_DECISION', node_name='respond', payload={'factual_output': 'python_verified'})
        state['answer'] = self.render(state, result.lead)

    def render(self, state, lead):
        if state['fatal']:
            return '요청을 처리하지 못했습니다. 오류 및 설정을 확인해 주세요.'
        if state['intent'] == 'greeting':
            return '안녕하세요. 날짜·지역·선호팀 등 원하는 직관 조건을 알려 주세요.'
        if state['intent'] == 'help':
            return '날짜와 원하는 지역·팀·시각·강수확률 조건을 알려 주세요. 허용한 조건만 완화합니다.'
        if not state['conditions'].get('date_range'):
            return '어느 날짜 또는 기간의 경기를 원하시나요? 미지정 날짜는 임의로 정하지 않습니다.'
        lines = [lead]
        for item in state['eligible']:
            g, d = item['game'], item['detail']
            lines.append(f"{d['start_at']}: {g['home_team']} vs {g['away_team']} / {d['venue_name']}")
            keys = ('date', 'time', 'team', 'region', 'weather')
            reasons = [item['checks'][k]['reason'] for k in keys
                       if k in item['checks'] and item['checks'][k]['status'] == 'met']
            lines.append('추천 근거: ' + '; '.join(reasons))
        if not state['eligible']:
            lines.append('검증된 조건 충족 경기가 없습니다. 불충족 또는 미확인 사유를 확인해 주세요.')
        # Keep the text concise; the complete per-candidate checks remain in the response.
        for item in state['excluded'][:3]:
            for status, label in (('unmet', '불충족'), ('unknown', '미확인')):
                reasons = [check['reason'] for check in item['checks'].values() if check['status'] == status]
                if reasons:
                    lines.append(f"{item['match_id']} {label}: " + '; '.join(reasons[:2]))
        if len(state['excluded']) > 3:
            lines.append(f"추가 제외·미확인 후보 {len(state['excluded']) - 3}건은 구조화된 checks를 확인해 주세요.")
        if state['relaxation_history']:
            lines.append(f"명시적으로 허용한 대안으로 {state['replan_count']}회 재계획했습니다.")
        if state['errors']:
            lines.append('일부 정보 조회에 실패했습니다. 오류 목록을 확인해 주세요.')
        return '\n'.join(lines)
