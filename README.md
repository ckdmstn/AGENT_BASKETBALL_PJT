# KBL GO

한국프로농구 AI 직관 플래너. Issue #1의 외부 Tool에 Issue #3의 LangGraph Main Agent와 채팅 API를 연결했다.
설계 기준은 [PROJECT_PLAN](docs/PROJECT_PLAN.md)이다. 웹에서 AI 직관 추천을 받고 SQLite에 계획을 저장하거나 Agent 실행 기록을 확인할 수 있다. RAG는 후속 작업이다.

## Windows / PowerShell 실행

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# 프로젝트 루트의 .env에 아래 환경변수를 설정한다.
.venv\Scripts\python -m uvicorn backend.main:app --reload
```

- 웹 UI: http://127.0.0.1:8000/
- 상태: http://127.0.0.1:8000/api/health
- Swagger: http://127.0.0.1:8000/docs
- 외부 API Tool은 아직 HTTP 라우트로 공개하지 않았다. Python의 `invoke(name, arguments)`로 호출한다.
- `.env`에 `KAKAO_REST_API_KEY`, `KMA_SERVICE_KEY`를 로컬에서 입력한다. 현재 설정된 키로 두 API의 실제 인증 성공을 확인했다. 기상청 키는 일반/URL 인코딩 형태를 처리하며, 두 형태 각각의 별도 실측은 하지 않았다.
- 현재 프로젝트는 `.env`를 직접 사용한다. 기존 파일은 덮어쓰지 않는다. 추가 설정 이름은 `KBL_BASE_URL`, `KBL_TEAM_CODE`, `API_TIMEOUT_SECONDS`이며 기본값은 각각 `https://api.kbl.or.kr`, `XX`, `15`다.
- 자연어 채팅은 `OPENAI_API_KEY`, `OPENAI_BASE_URL`(HTTPS OpenAI 호환 `/v1` 등 API 루트), `OPENAI_MODEL` 설정이 필요하다. 현재 GMS의 `gpt-6-sol`로 실제 JSON 모드 호출을 확인했다. URL 끝에 `/chat/completions`는 붙이지 않는다. 기존 프로세스 환경변수가 로컬 파일보다 우선하며 설정 변경 후 서버를 재시작한다.

## 웹 UI 사용

웹 UI는 밝은 블루그레이 배경과 흰색 카드에 딥 네이비 버튼과 브랜드를 사용한다. 채팅 아래 **다른 팀 추천**에서 **다른 팀도 허용** 또는 **허용 취소**를 누른다. 채팅에 `다른 팀도 괜찮아.` 또는 `다른 팀은 안 돼.`를 별도 메시지로 입력해도 된다.

**허용됨**은 세션에 저장된 권한이다. **이번 실행에서 선호 팀 조건이 완화됐습니다** 안내는 실제로 이번 실행에서 선호 팀 조건을 해제했을 때 표시된다. 모호한 표현에는 **확인 필요**가 표시되며 버튼으로 명시적으로 허용할 수 있다. 기존 세션을 새로고침하거나 응답을 받지 못하면 **상태 미확인**을 표시하고 다음 정상 채팅 응답으로 권한을 확인한다.

1. **직관 추천**에서 날짜, 지역, 팀 등을 자연어로 입력한다. 예를 들어 `2026년 11월 19일 오후 2시 이후 수원에서 서울 SK 경기를 추천해 줘`처럼 입력한다. Enter는 전송, Shift+Enter는 줄바꿈이다. 응답에 따라 추천·제외 후보와 검증 근거, 원조건과 적용 조건을 확인할 수 있다.
2. **계획 저장**으로 확인된 경기 정보를 확인하고 선택적으로 종료 예정 시각과 메모를 입력한다. **저장한 계획**의 상세에서 종료 예정 시각과 메모를 수정하거나 계획을 삭제할 수 있다. 중복 일정이 있으면 저장 결과와 별도로 경고를 표시한다.
3. **Agent 실행 기록**에서 세션별 실행 상세를 열면 분석, Tool 호출, 캐시 재사용, 조건 조정과 완료·실패 상태를 확인할 수 있다. 로그를 삭제해도 계획과 대화 조건은 유지된다.

브라우저는 현재 `session_id`만 같은 origin의 `localStorage`에 저장한다. 새로고침 뒤에는 기존 조건을 이어갈 수 있으며 화면의 메시지 내역은 새로 시작한다. **새 대화**는 브라우저의 세션 선택을 초기화하고 다음 요청에서 새 ID를 받는다. 세션 ID는 인증 수단이 아니며 같은 브라우저 프로필과 origin을 사용하는 사용자가 접근할 수 있다. API에 별도 인증이 없으므로 루프백 주소에서 로컬 단일 사용자용으로 실행한다.

## 최종 시연 순서

PowerShell에서 프로젝트 루트의 `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`으로 서버를 실행한다. [웹 UI](http://127.0.0.1:8000/)와 [Swagger](http://127.0.0.1:8000/docs)를 사용할 수 있다.

1. **실제 추천**. 검증 기준 문장은 `2026년 11월 19일 오후 6시 이후 안양에서 부산 KCC 경기 추천해 줘.`이다. 이 문장은 실제로 조회한 과거 일정의 기록을 재현한다. 앞으로 관람할 경기를 시연할 때는 KBL 일정에 있는 날짜와 검증 가능한 경기장으로 바꾼다. 경기 시각이 단기예보 범위에 있을 때만 해당 경기 예보를 평가한다.
2. **후속 대화와 재계획**. 같은 대화에서 `선호 팀을 창원 LG로 바꿔 줘. 강수확률 100% 이하면 좋겠어. 다른 팀도 괜찮아.`를 보낸다. 원조건·적용 조건·재계획을 확인하고 `다른 팀은 안 돼. 기존 조건으로 다시 찾아 줘.`로 팀 완화 권한을 철회한다. 예보 범위 밖인 과거 경기는 강수 조건이 미확인으로 남는다.
3. **계획 관리**. 추천 카드에서 경기 시작 이후의 종료 시각을 입력해 저장한다. 같은 시간대로 한 번 더 저장해 중복 경고를 확인한다. 계획 상세에서 메모를 수정하고, 시연 중 만든 복제 계획만 삭제한다.
4. **실행 기록**. 세션 상세에서 Node·Tool·판단·재계획 순서를 확인한다. 시연 세션의 로그를 삭제하고 계획 목록과 후속 대화 상태가 남는지 확인한다.
5. **대체 시연**. API 오류 시 인증 변수의 설정 여부와 네트워크 연결을 확인하고 재시도를 사용한다. 경기 없음은 정상 결과로 안내하며, 필요하면 로컬 `.verification/browser/server.py` 및 `.verification/browser/smoke.cjs` 시나리오를 **Mock 데모**로 실행한다. 이 파일은 Git 제외 검증 자료이며 실제 조회와 구분한다.

## Swagger에서 채팅 실행

Swagger에서 `POST /api/chat`을 열고 다음 요청을 실행한다. 실제 날짜에 경기가 없으면 추천이 없을 수 있다.

```json
{"session_id":"demo-session","message":"2026년 11월 19일 오후 2시 이후 수원에서 서울 SK 경기를 추천해 줘. 강수확률 50% 이하면 좋겠어."}
```

같은 `session_id`로 `팀만 LG로 바꿔 줘. 없으면 다른 팀도 괜찮아.`를 요청하면 날짜·지역·시간·강수 조건을 유지한다. 세션 ID를 생략하면 새 ID를 발급한다. 응답의 `conditions`는 사용자가 요청한 원조건, `active_conditions`는 허용된 재계획 적용 조건이다. 완화한 조건이 다음 발화의 원조건을 덮어쓰지 않는다.

## 직관 계획 및 실행 로그 API

| 메서드와 경로 | 응답 |
| --- | --- |
| `POST /api/plans` | 201 및 `plan`, `overlapping_plan_ids`, `overlap_warnings` |
| `GET /api/plans`, `GET /api/plans/{plan_id}` | 계획 목록과 상세 |
| `PATCH /api/plans/{plan_id}` | 명시된 필드 변경 후 계획 및 중복 경고 |
| `DELETE /api/plans/{plan_id}` | 204 |
| `GET /api/logs` | 세션별 실행 수, 이벤트 수, 마지막 발생 시각 |
| `GET /api/logs/{session_id}` | 실행별 이벤트 상세. 실행 내 순서는 `sequence_no` 기준 |
| `DELETE /api/logs/{session_id}` | 해당 세션의 로그만 삭제하고 204 반환 |

계획 생성에 `match_id`, `home_team`, `away_team`, `venue_name`, `start_at`이 필요하다. `session_id`, `venue_address`, `note`, `end_at`은 선택 항목이다. 시간대가 포함된 시각을 입력하면 KST로 저장하고 `game_date`는 KST 시작일로 반환한다. 겹치는 일정도 저장되며, 종료 시각이 없어 검사가 제한되면 경고를 반환한다. PATCH에서 선택 필드에 `null`을 보내면 값을 지운다.

SQLite 파일은 최초 사용 시 `data/kbl-go.sqlite3`에 생성되며 Git에서 제외된다. 같은 파일을 사용하면 서버 재시작 후에도 같은 `session_id`의 조건·권한·직전 추천 요약을 복원한다. 계획과 로그 API에는 사용자 인증이 없으므로 로컬 단일 사용자 환경에서 사용한다.

## 검증

```powershell
.venv\Scripts\python -m pytest tests/test_tool_contracts.py -q
.venv\Scripts\python -m pytest -q
$env:PYTHONIOENCODING = 'utf-8'
.venv\Scripts\python scripts/check_external_apis.py --from-date 2026-11-18 --to-date 2026-11-25 --output .verification/api-check.json
```

검증 스크립트 종료 코드: 모두 성공하면 0, 실패/건너뜀/키 누락이 하나라도 있으면 1.
`.verification/`는 Git 제외이며 정규화된 결과 중 최대 3개 샘플만 저장한다. 원본 HTTP 본문·인증 헤더·기상청 서비스키 URL은 출력하지 않는다.
`--no-env-file`은 .env 로딩만 생략하며 프로세스 환경변수는 읽는다.
날씨 기본 위치는 서울시청(37.5665, 126.9780)이고 장소 검색 결과와 연결된 좌표가 아니다. `--weather-at`, `--lat`, `--lon`, `--venue`로 개별 검증 입력을 바꿀 수 있다.

## 파일 연결

`scripts/check_external_apis.py → tools.registry.invoke → Pydantic 입력 검사 → 각 Tool → 공통 HTTP 처리 → Pydantic 결과 검사`

`tool_specs()`는 네 Tool의 설명, 외부 구분, 입력 및 성공/실패 출력 JSON Schema를 반환한다.
성공은 `ok=true, data, error=null, meta`, 실패는 `ok=false, data=null, error={code,message}, meta`다.
`meta`는 조회 시각·실제 비밀 없는 인자·HTTP/서비스 상태·필드명을 제공한다.
예상하지 못한 내부 예외와 출력 계약 오류는 `INTERNAL_ERROR`다. 외부 HTTP·연결·서비스 실패는 `UPSTREAM_ERROR`, 타임아웃은 `TIMEOUT`으로 구분하며 예외 원문은 반환하지 않는다.
카카오 결과는 장소 후보이며 실제 KBL 경기장으로 확정하지 않는다. KBL 목록은 EASL/D리그 포함 가능성을 경고하며 실제 대회 구분값을 보존한다.
Main Agent는 `backend/agent/`에 있다. `analyze → plan → execute_tools → evaluate → respond`, 대안이 있으면 `evaluate → replan → plan`으로 분기한다. 인사·도움말·날짜 누락은 Tool 없이 응답한다. 기존 Tool 함수는 다시 작성하지 않았다.

LLM은 JSON 모드로 의도·변경 필드·Tool 순서·응답 안내 문장을 선택하고 Pydantic으로 검증한다. 응답의 경기 사실·검증 사유는 Python이 실제 데이터에서 작성한다. 모델이 경기·주소·예보를 생성하지 못하도록 자연어 안내 문장은 허용된 문장으로 제한했다.

조건 검증은 `met/unmet/unknown`이다. 지역은 팀 연고지가 아니라 검증된 장소 주소로 비교한다. 정규리그는 실측 `season_category=R`, `season_grade=1`로 제한하며 EASL·D리그는 제외한다. 미확인 대회 값은 충족으로 처리하지 않는다. `low_rain`은 확인된 강수확률 오름차순이며 임의의 숫자 상한을 만들지 않는다.

재계획은 명시적 타 팀 허용·대안 날짜만 적용하며 최대 3회다. 지역·시간은 임의 변경하지 않는다. 키 누락·내부 오류뿐 아니라 인증 실패가 포함될 수 있는 외부 서비스 오류·타임아웃도 조건 완화로 해결하지 않는다. 다른 후보의 잔여 작업은 계속한다. 동일 실행의 동일 Tool·인자는 성공/실패 모두 캐시하고 이벤트에 캐시 여부를 기록한다.

조건 완화는 LLM의 True 플래그만으로 허용하지 않는다. `permissions.py`가 지원하는 직접 표현 또는 같은 세션의 이전 검증 기록이 필요하다.

- 팀 허용 예: `LG 경기 없으면 다른 팀도 괜찮아`, `다른 팀도 괜찮아`. 긴 요청과 허용 문장은 마침표로 나누어 명확히 전달한다.
- 대체 날짜 예: `대체 날짜: 2026-11-20 허용해`, `대체 날짜: 2026-11-20,2026-11-21~2026-11-22 허용해`. ISO 날짜/범위 최대3개만 지원한다.
- 철회 예: `다른 팀은 안 돼`, `다른 날짜는 안 돼`, `날짜는 바꾸지 마`, `방금 허용은 취소해`. 철회는 LLM 처리 전에 권한 축소로 저장하여 이후 오류가 나도 유지한다.
- 불명확한 표현·인용·의문이나 지원 밖 문법은 자동 허용하지 않고 확인을 요청한다. 이전의 검증된 허용은 팀만 바꾸는 후속 요청에서 유지한다. 단순 조건 플래그만 있던 과거 세션은 권한으로 인정하지 않는다.
- 이 검증은 제한된 문법에 대한 보수적 정책이며 모든 한국어 의도 이해를 보장하지 않는다. 일반 원조건 추출은 여전히 LLM을 사용한다.

## 날씨 필드 정책

- `forecast_at`: 실제 예보 대상 시각. 요청 시각을 KST로 변환한 뒤 분·초를 내린 정시의 응답을 조회한다. 예: 15:45 요청은 15:00 예보를 의미한다.
- `issued_at`: 조회에 사용한 발표 기준시각 (`base_date/base_time`). 대상 시각과 다르다.
- `available=true`: 해당 대상 시각의 기온·강수확률·강수량 중 하나 이상이 제공됨을 뜻한다. 강수 조건 통과를 뜻하지 않는다.
- `precipitation_probability_pct=null`: 강수확률 미확인. 0%로 대체하거나 기온·`available`·강수량 표현만으로 강수확률 조건을 충족시켜서는 안 된다. 다른 제공 데이터는 그대로 사용할 수 있다.
- DAY 2 Agent는 강수확률이 확인된 경우에만 명시된 상한과 비교하며 예보 대상 시각이 실제 경기 정시와 일치하는지도 검사한다.

## 현재 제약

- FastAPI는 만료 또는 자동 삭제가 없는 SQLite 세션 저장소를 사용한다. 직접 생성한 `AgentRunner`는 저장소를 주입하지 않으면 기존 200개 한도의 메모리 저장소를 사용한다.
- 세션 갱신 충돌 방지를 위해 단일 프로세스에서 전체 실행을 직렬화한다. 여러 worker의 동시 채팅은 지원 범위 밖이다.
- 단일 날짜 범위는 최대 31일, 명시적 대안 날짜 범위는 최대 3개다. 후보 목록 자체를 앞부분에서 잘라 적합 후보를 버리지 않는다. 넓은 기간은 외부 호출과 지연이 늘어난다.
- 공식 이름·도로명 주소 대조표는 현재 잠실학생체육관·안양 정관장 아레나·수원 KT 소닉붐 아레나 3곳이다. 그 외 구장이나 이름·주소가 모호한 후보는 `unknown`이고 임의 좌표로 날씨를 조회하지 않는다. 출처는 [검증 기록](docs/VERIFICATION.md)에 있다.
- Logging Agent는 EventBus의 정형 메타데이터를 저장한다. 저장 오류는 해당 이벤트에만 영향을 주며 자동 재시도는 없다. 실행 중 로그를 삭제하면 이후 발행된 이벤트가 다시 기록될 수 있다.

## 문서 관리

공유 설계 `docs/PROJECT_PLAN.md`와 검증 증거 `docs/VERIFICATION.md`는 Git에서 관리한다. 내부 작업 전달서·구현 체크리스트·PR 초안은 로컬에 유지하고 Git 추적에서 제외한다. 다음 작업도 기존 로컬 파일을 재사용하며 번호를 붙인 새 교환 문서를 추가하지 않는다. Git 추적 제외는 과거 커밋 이력을 삭제하는 작업은 아니다.

## API 출처와 현재 상태 (2026-11-19)

| API | 출처 | 실측/정책 확인 |
|---|---|---|
| KBL | [공식 웹 앱](https://www.kbl.or.kr/) / `api.kbl.or.kr` | 목록·gmkey 상세 HTTP 200. 공개 API 문서/사용 허가/호출 한도 미확인. 웹 앱 구현은 사용 허가를 뜻하지 않는다. |
| Kakao | [로컬 개발 가이드](https://developers.kakao.com/docs/ko/local/dev-guide), [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota), [이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common) | 실제 HTTP 200, 장소 후보의 주소·좌표·링크 확인. 무료 적용/유료 활성화 조건은 앱별 확인 필요. 앱 잔여 한도 미확인. |
| KMA | [공공데이터포털 15084084](https://www.data.go.kr/data/15084084/openapi.do) | 실제 HTTP 200 / 서비스 00, 대상 시각의 기온·강수확률·강수량 확인. 예보 마지막 시각·발급 계정별 한도 미확인. |

실제 명령/환경 버전/응답 증거/제약은 [검증 기록](docs/VERIFICATION.md)에 정리했다.
명세 PDF가 현재 저장소에 없어 LangChain 등 나머지 명세 고정 버전 대조는 보류했다. LangGraph 1.2.10은 실제 설치하고 그래프·HTTP 통합 실행을 검증했다.
