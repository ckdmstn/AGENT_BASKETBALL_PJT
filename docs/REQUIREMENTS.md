# 요구사항 정의 및 검증

KBL 직관 추천을 대상으로 날짜, 지역, 시작 시각, 팀, 강수 조건을 결합한다. KBL에서 경기 목록·상세를, Kakao에서 경기장 주소·좌표를, 기상청에서 해당 격자와 시각의 단기예보를 조회한다. 저장 대상은 팀·경기 시작 시각·장소·선택 메모를 포함한 개인 직관 계획이다.

기획 검증에서 경기 목록의 식별자와 상세 결과가 이어지는 것을 확인했다. KBL 목록에 EASL·D리그가 섞이고 장소 검색 결과에 유사 시설이 포함될 수 있어 정규리그 필터와 경기장 검증을 추가했다. 예보 시간이 경기 시간과 다르거나 강수확률이 비어 있을 때는 미확인으로 처리한다. 실제 호출 및 설계 변경 이력은 [프로젝트 계획](PROJECT_PLAN.md)과 [검증 기록](VERIFICATION.md)에 있다.

| ID | 검증 대상 | 구현 | 테스트 | 증빙·판정 |
| --- | --- | --- | --- | --- |
| F3001 | Tool 등록과 검증 | [코드](../backend/tools/registry.py) | [테스트](../tests/test_tool_contracts.py) | [1번](CHECKLIST.md) · PASS |
| F3002 | 날짜 기본값과 KBL 후보 조회 범위 | [코드](../backend/tools/kbl.py) | [테스트](../tests/test_tool_contracts.py) | [2번](CHECKLIST.md) · PASS |
| F3003 | 경기 식별자로 상세 조회 | [코드](../backend/tools/kbl.py) | [테스트](../tests/test_tool_contracts.py) | [3번](CHECKLIST.md) · PASS |
| F3004 | 경기장 보조 검색 | [코드](../backend/tools/kakao.py) | [테스트](../tests/test_tool_contracts.py) | [4번](CHECKLIST.md) · PASS |
| F3005 | 요청 조건 분석 | [코드](../backend/agent/nodes.py) | [테스트](../tests/test_agent.py) | [5번](CHECKLIST.md) · PASS |
| F3006 | Tool 계획 및 무호출 경로 | [코드](../backend/agent/graph.py) | [테스트](../tests/test_agent.py) | [6번](CHECKLIST.md) · PASS |
| F3007 | Tool 결과 연결 및 실패 격리 | [코드](../backend/agent/nodes.py) | [테스트](../tests/test_agent.py) | [7번](CHECKLIST.md) · PASS |
| F3008 | 실측 기반 조건 판정 | [코드](../backend/agent/evaluation.py) | [테스트](../tests/test_agent.py) | [8번](CHECKLIST.md) · PASS |
| F3009 | 허용 대안·캐시·재계획 상한 | [코드](../backend/agent/nodes.py) | [테스트](../tests/test_agent.py) | [9번](CHECKLIST.md) · PASS |
| F3010 | 후속 대화 및 세션 격리 | [코드](../backend/agent/sessions.py) | [테스트](../tests/test_sqlite_agent.py) | [11번](CHECKLIST.md) · PASS |
| F3011 | 추천·근거·제외 사유 | [코드](../backend/agent/evaluation.py) | [테스트](../tests/test_agent.py) | [12번](CHECKLIST.md) · PASS |
| F3012 | 이벤트 발행·구독 분리 | [코드](../backend/agent/events.py) | [테스트](../tests/test_sqlite_agent.py) | [14번](CHECKLIST.md) · PASS |
| F3013 | LLM 없는 로깅과 저장 오류 격리 | [코드](../backend/agent/logging.py) | [테스트](../tests/test_sqlite_agent.py) | [17번](CHECKLIST.md) · PASS |
| F3014 | 로그 목록·상세·삭제 | [코드](../backend/logs.py) | [테스트](../tests/test_sqlite_api.py) | [18번](CHECKLIST.md) · PASS |
| F3015 | 계획 저장·조회·겹침 안내 | [코드](../backend/plans.py) | [테스트](../tests/test_sqlite_api.py) | [19번](CHECKLIST.md) · PASS |
| F3016 | 계획 핵심 값 편집·삭제 | [코드](../frontend/app.js) | [테스트](../tests/test_sqlite_api.py) | [20번](CHECKLIST.md) · PASS |
| F3017 | FastAPI 경로와 계약 | [코드](../backend/main.py) | [테스트](../tests/test_chat_api.py) | [21번](CHECKLIST.md) · PASS |
| F3018 | 대화와 계획 화면에서 API 사용 | [코드](../frontend/app.js) | [테스트](../tests/test_web.py) | [21번](CHECKLIST.md) · PASS |
| F3019 | 타임라인·재계획·로딩·오류 안내 | [코드](../frontend/app.js) | [테스트](../tests/test_agent.py) | [22번](CHECKLIST.md) · PASS |
| NF3001 | 키 보관 및 제거 | [코드](../backend/config.py) | [테스트](../tests/test_tool_contracts.py) | [25번](CHECKLIST.md) · PASS |
| NF3002 | 오류 상세와 키 노출 방지 | [코드](../backend/main.py) | [테스트](../tests/test_chat_api.py) | [25번](CHECKLIST.md) · PASS |
| NF3003 | 단일 Tool 실패 내성 | [코드](../backend/agent/nodes.py) | [테스트](../tests/test_agent.py) | [7번](CHECKLIST.md) · PASS |
| NF3004 | 최대 3회 재계획 | [코드](../backend/agent/nodes.py) | [테스트](../tests/test_agent.py) | [10번](CHECKLIST.md) · PASS |
| NF3005 | 대표 시나리오 응답 시간 | [코드](../backend/agent/graph.py) | [테스트](../tests/test_agent.py) | [23번](CHECKLIST.md) · BLOCKED |
| NF3006 | 프론트·백엔드 및 Agent·Tool 분리 | [코드](../backend/main.py) | [테스트](../tests/test_web.py) | [26번](CHECKLIST.md) · PASS |
| NF3007 | 외부 API 출처·약관·호출 한도 | [코드](../backend/tools/kbl.py) | [공급자 정보](TOOL_SPEC.md) | [26번](CHECKLIST.md) · BLOCKED |

F3020–F3023은 선택 심화 기능이며 이번 제출 범위에서 선택하지 않았다. 필수 제출 상태는 [체크리스트](CHECKLIST.md)를 기준으로 확인한다.
