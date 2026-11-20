# KBL GO — AI 한국프로농구 직관 플래너

> 상태: **설계 초안 v0.1 / 외부 API 정상 호출 실측 완료, 정책·경계 검증 진행 중**
> 기준: `AI코어프로젝트_3회차_요구사항정의서.pdf` (필수 F3001~F3019, 비기능 NF3001~NF3007)  
> 원칙: 명세서의 필수 항목을 우선하며, 과제 도메인 표현만 KBL로 변경한다. API 실측 및 회귀 테스트 이력은 `VERIFICATION.md`에서 구분한다.

## 1. 프로젝트 개요와 목표

자연어(날짜, 경기 시작 시각, 지역, 선호 팀, 날씨)를 입력받고 KBL 경기 일정과 경기장 장소, 가능한 범위의 기상청 예보를 조합해 근거 있는 직관 계획을 제안한다. 조건을 충족하지 못하면 허용된 조건만 완화해 제한된 횟수로 재계획한다. 사용자는 계획 CRUD와 Agent 실행 이력을 볼 수 있다.

기획 검증에 사용할 요청 3개:
1. "이번 주말 오후 2시 이후 서울에서 LG 경기를 추천해 줘. 없으면 다른 팀도 괜찮아."
2. "토요일에 서울에서 하는 경기 중 비 올 확률이 낮은 경기를 골라 줘."
3. "지난번 조건에서 선호팀만 SK로 바꿔 줘."

추가 질의 예: "오늘 가능한 경기가 있어?"(조건 누락 시 필요한 범위만 질문), "안녕"(Tool 불필요).

## 2. 요구사항 추적표

| ID | 필수 내용 | MVP 구현 및 증빙 |
|---|---|---|
| F3001 | Tool 이름·설명·입출력 스키마 등록, 외부/로컬 구분, 공통 실패 형식 | Tool Registry / 스키마 출력·정상·실패 테스트 |
| F3002 | 후보 조회 외부 Tool, 날짜 기본값, 다음 Tool 식별자, 조회 기준/추정 표시 | `search_kbl_games` / 기준 날짜 및 match_id 증빙 |
| F3003 | 식별자로 외부 상세조회, 필수 속성 불명 시 임의 추정 금지 | `get_kbl_game_detail` / 상세조회 가능 여부 우선 검증 |
| F3004 | 다른 출처 보조 정보 외부 Tool, 주소·링크, 미검색 처리 | `search_arena`(카카오), `get_weather`(기상청) |
| F3005 | 기준·선호·제약 조건 분석, 임의 채움 금지 | 의도·조건 JSON 및 미지정 필드 검증 |
| F3006 | Tool 선택/순서 계획, 필요 없는 호출 생략 | `tasks` 목록 및 일반대화 분기 |
| F3007 | 앞선 Tool 출력 식별자 전달, 실패해도 잔여 작업 진행 | Tool 결과·실패 이벤트 확인 |
| F3008 | 실제 속성과 계산값으로 제약 적합성 판정 | 시각·지역·팀·강수확률 계산 근거 및 미확인 표시 |
| F3009 | 대안 재탐색, 결과 재사용, 횟수 상한 | 캐시·최대 3회 재계획 테스트 |
| F3010 | 직전 요청과 결과 요약 유지, 조건 일부만 갱신 | session_id와 후속 발화 테스트 |
| F3011 | 추천·보조 정보·판정 근거·제외 사유 제시 | 구조화된 응답 및 UI |
| F3012 | 단계/Tool/LLM 판단 이벤트 발행, 구독자 독립 | 이벤트 버스 로그 확인 |
| F3013 | 로깅 서브 Agent 구독·세션별 저장, LLM 미사용 | 분리된 subscriber, 기록 비활성 테스트 |
| F3014 | 로그 목록·세션 상세·삭제, 수정 금지 | GET/DELETE API, PUT/PATCH 부재 |
| F3015 | 계획 저장/목록/상세, 날짜·시각·생성일, 중복 시간 경고 | 겹쳐도 201 저장 + overlap warning |
| F3016 | 계획 수정/삭제 즉시 UI 반영 | PATCH/DELETE 테스트 |
| F3017 | FastAPI 대화·계획·로그 경로 및 스키마 | `/docs`와 API 테스트 |
| F3018 | 대화·계획 관리 화면, 백엔드 API 연동 | JS fetch 네트워크 확인 |
| F3019 | 실행 단계·Tool 호출·재계획·로딩·실패/키 없음 표시 | 타임라인과 오류 시나리오 |

비기능: **NF3001** 키 환경변수, **NF3002** UI에서 비밀·오류 내부정보 숨김, **NF3003** Tool 오류 격리, **NF3004** 재계획 상한, **NF3005** 실용적 처리 시간 측정, **NF3006** FE/BE·Agent/Tool 분리, **NF3007** API 출처·약관·호출 한도 기록.

심화 F3020(로그 이상징후), F3021(Planner·Worker LLM 분화), F3022(기존 RAG 검색), F3023(Google Calendar)는 **필수 19개 완성 후에만** 검토한다. 특히 별도 로깅 Agent 자체는 심화가 아니라 필수다.

## 3. MVP 범위와 제외

### MVP
- 외부 API 3종 KBL 일정·카카오 장소·기상청 날씨의 **실제 호출 성공/실패**를 Tool 형태로 정규화한다.
- KBL 후보 목록 Tool과 식별자 기반 상세정보 Tool을 **논리적으로 분리**한다. 상세 API의 유효한 호출 경로/식별자는 실측 후 확정한다.
- LangGraph로 분석→계획→Tool 실행→판단→재계획→응답을 구성한다.
- 최근 세션 상태 요약, 이벤트 발행/구독, SQLite 계획 CRUD·실행 로그 목록/상세/삭제를 제공한다.
- 간단한 HTML/CSS/JS UI로 대화·저장 계획·로그 타임라인을 보여준다.

### 제외
- 티켓 예매/결제, 이동 경로 최적화, 좌석 추천, 실시간 교통, 알림, 회원가입, 스트리밍 토큰, 배포 자동화, 전면 RAG 이식, Google Calendar, 고도화된 멀티 Agent.
- 일정에 없는 경기나 경기 시각, 날씨 예보 범위 밖의 강수확률을 만들어내지 않는다.

## 4. 기술 스택

Python 3.10+, FastAPI, Pydantic, LangGraph(명세 제시 버전 1.2.10), LangChain 관련 패키지(명세 버전 기준), requests, python-dotenv, sqlite3(표준 라이브러리), HTML/CSS/Vanilla JS. LLM은 `.env`의 OpenAI 호환 API 설정을 사용하며 GMS 등 제공 환경의 접근 가능 모델을 실제로 검증한다. `requirements.txt`는 명세의 설치 가능한 버전과 환경을 우선 대조한다. ChromaDB는 기본 실행 의존성에서 제외한다.

## 5. 시스템 구성

```text
Frontend (chat / plans / logs)
       | JSON REST
FastAPI routes + Pydantic
       | session_id
LangGraph Main Agent
  analyze -> plan -> execute_tools -> evaluate -> [replan -> plan] or respond
            |             |
       Tool Registry      EventBus.publish(event)
            |                    |
  KBL list/detail, Kakao, KMA   LoggingSubscriber (LLM 없음)
            |                    |
       API clients             SQLite agent_events
FastAPI plans API -> SQLite plans
FastAPI chat API -> SQLite session_summaries
```

**중요:** 이벤트 발행과 로깅 구독은 분리한다. 동기식 in-process pub/sub로 충분하며 logger 실패를 잡아 메인 흐름을 유지한다. 이벤트는 저장 전후의 실제 발생 사실을 보존한다.

## 6. Agent State, Node, Edge

`AgentState`의 최소 필드: `session_id`, `user_message`, `intent`, `conditions`, `last_conditions`, `tasks`, `task_results`, `games`, `details`, `arena_info`, `weather_info`, `eligible`, `excluded`, `replan_count`, `max_replans=3`, `relaxation_history`, `answer`, `errors`.

- `analyze`: LLM 구조화 출력으로 intent(`plan|follow_up|help|greeting`)와 필터(`date_range`, `start_after`, `region`, `preferred_team`, `weather_preference`, `fallback_teams_allowed`)를 추출. 요청에 없는 조건은 null로 유지하며 후속 요청은 이전 조건과 **지정된 키만** 병합. LLM 분류 이유 이벤트 기록.
- `plan`: LLM이 조건과 캐시 상태를 보고 등록 Tool의 종속 순서를 구조화 출력한다. 인자는 Python이 실제 앞선 Tool 결과에서 결합하며 LLM이 생성하지 않는다. 인사/도움말·날짜 누락은 Tool 0개.
- `execute_tools`: 레지스트리에 등록된 Tool만 순서대로 호출; 경기 목록의 `match_id`를 상세 Tool에, 상세정보/경기장에서 확인한 명칭을 카카오 Tool에 전달. 실패해도 다른 후보를 진행; 조회 결과를 실행 단위 캐시로 보존.
- `evaluate`: 실제 경기 일시, 팀, 확인된 경기장 주소/행정구역, 실제 조회한 강수확률을 필터와 비교해 근거를 반환. 모르는 값은 `unknown`이며 임의로 합격 처리하지 않는다.
- `replan`: 충족하는 후보가 없고 사용자가 명시적으로 허용한 완화(예: 선호 LG→타 팀)나 대안 날짜 범위가 있을 때만 대안 작업을 구성. 기존 결과 재사용. 최대 3회 후 종료. 인증 실패/키 누락은 재계획 금지. 기존 Tool의 UPSTREAM_ERROR에 실제 인증 실패가 포함되므로 모든 외부 서비스 오류·타임아웃도 보수적으로 재계획하지 않는다.
- `respond`: 추천 경기/근거/주소/날씨 예보 기준시각/제외 사유/오류/조회 한계를 포함하는 구조화된 응답.

Edge: START→analyze→plan→(tasks 빈 경우 respond, 아니면 execute_tools)→evaluate→(적합하면 respond, 대안 있으면 replan→plan, 상한 도달 시 respond)→END. `replan_count`는 **재계획 분기 횟수**로 정의하고 최대 3.

**우선 검증:** KBL 실제 API가 경기 식별자·상세정보·시작 시각·홈 경기장 식별자를 제공하는지, 미래/지난 일정 검색이 가능한지. 이것이 F3003의 충족 여부를 좌우한다.

## 7. Tool 정의와 실패 계약

공통 결과: `{"ok":true,"data":{},"meta":{"source":"...","requested_at":"...","actual_query":"..."}}` 또는 `{"ok":false,"error":{"code":"...","message":"..."},"meta":{...}}`. Tool은 raw traceback/API key를 반환하지 않는다. 실패 코드: `INVALID_INPUT`, `MISSING_API_KEY`, `UPSTREAM_ERROR`, `TIMEOUT`, `NO_RESULT`, `UNSUPPORTED_DATE`, `MISSING_FIELD`, `INTERNAL_ERROR`. 외부 HTTP·연결·서비스 실패는 `UPSTREAM_ERROR`, 예상하지 못한 내부 예외·출력 계약 위반은 `INTERNAL_ERROR`로 구분한다.

| Tool | 사용 시점 / 입력 | 정규화된 출력 |
|---|---|---|
| `search_kbl_games` | 일정 후보가 필요할 때; `from_date`, `to_date`, `team_code?` | `[{match_id, home_team, away_team, start_at?, venue_name?, source}]`, 실제 조회 기준 |
| `get_kbl_game_detail` | 후보 `match_id`로 상세 속성 확인; `match_id`, `date?` | `match_id, start_at?, home_team?, away_team?, venue_name?, status?` (확인된 값만) |
| `search_arena` | 경기장 이름/주소 확인; `venue_name`, `region_hint?` | `name, road_address?, address?, lat?, lon?, place_url?` 또는 NO_RESULT |
| `get_weather` | 경기 일정·위치가 확인되고 예보 가능할 때; `date_time`, `lat`, `lon` | `forecast_at, issued_at, temperature_c?, precipitation_probability_pct?, precipitation_mm?, available` |

날씨 정책: `forecast_at`은 요청을 KST로 변환 후 분 이하를 내린 실제 예보 대상 정시, `issued_at`은 조회 발표 기준시각이다. `available=true`는 TMP/POP/PCP 중 하나 이상 제공됨을 뜻하며 조건 통과가 아니다. 강수확률 null은 미확인이므로 0%로 대체하거나 다른 필드로 강수확률 조건 충족을 추정하지 않는다. 기온 등 제공된 데이터는 보존한다. 사용자 임계값 판정은 DAY 2 Agent 범위다.

KBL 목록과 상세정보를 같은 공식적으로 확인된 호출 경로에서 가져올 수 있다면 **서로 다른 Tool의 입력/출력과 후보 ID 전달**을 반드시 입증한다. API가 진짜 상세 조회를 지원하지 않는다면 F3003 대응을 설계 변경으로 명시하며, 임의로 상세 호출 성공을 주장하지 않는다. 기상청은 예보 기준시각·격자 좌표 변환(nx, ny)·예보 제공 범위를 엄격히 검증해야 한다. 카카오가 장소명만 유사한 결과를 줘도 실제 KBL 경기장으로 검증 없이 확정하지 않는다. 경기장 이름-주소의 보조 목록은 **공식 정보로 대조하고 출처 기록** 후 사용한다.

### API 연결 및 제한

- KBL: `https://api.kbl.or.kr/match/list` / `Channel: WEB`, `TeamCode` 전달 방식은 실측 확인. 비공식 API이므로 응답 구조·약관·허용 여부 리스크를 문서화.
- Kakao Local: `https://dapi.kakao.com/v2/local/search/keyword.json`, `Authorization: KakaoAK <key>`.
- KMA: 공공데이터포털 데이터 ID `15084084`, `getVilageFcst` (serviceKey, base_date, base_time, nx, ny 등). 실제 엔드포인트/서비스키 인코딩은 실측 확인.
- 날씨 예보 범위를 벗어나면 "예보 제공 범위 밖"으로 표시하고 경기 추천 자체와 분리한다.
- 사용자 결정에 따라 `.env.example` 없이 로컬 `.env`를 직접 사용한다. 변수명은 README에 안내하며 실제 값은 공유하지 않는다. `.env`, SQLite DB, `.venv`, 캐시, 로그 원본은 `.gitignore`에 추가.
- 각 API 출처·이용 조건·호출 한도·검증 일자를 README의 표에 기록(실제 확인값만 기입).

## 8. DB 및 로깅 설계

SQLite 테이블:
- `plans(id, session_id, match_id, game_date, start_at, end_at NULL, home_team, away_team, venue_name, venue_address NULL, note NULL, created_at, updated_at)`.
- `sessions(session_id PRIMARY KEY, conditions_json, last_answer_json, updated_at)` — 전 회차 원본 API JSON은 저장하지 않음.
- `agent_events(id, session_id, run_id, sequence_no, event_type, node_name, tool_name NULL, payload_json, elapsed_ms NULL, created_at)` — 세션+발생 순서로 조회. 수정 API 없음.

이벤트 종류: `NODE_STARTED`, `NODE_COMPLETED`, `TOOL_REQUESTED`, `TOOL_RESPONDED`, `LLM_DECISION`, `REPLAN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`. 모든 이벤트에 `session_id`,`run_id`,`sequence_no`,`timestamp` 포함. LLM의 의도·분기 결정은 간단한 결정 이유와 함께 저장하되 민감정보와 토큰은 제외한다. Logger는 **LLM을 절대 호출하지 않는다**. Logger를 끊어도 Agent가 정상 응답하는 테스트를 둔다.

**일정 겹침**: 두 계획 모두 `start_at`과 `end_at`이 확인된 경우 `existing.start < new.end AND new.start < existing.end`를 사용한다. 시간은 같은 타임존(Asia/Seoul)으로 통일. 경기 종료 시각이 API에서 제공되지 않으면 종료 시각을 지어내지 않는다. 저장 UI에서 **사용자가 종료 예정 시각을 입력하도록 선택지**를 제공하고 값이 없으면 겹침 비교가 제한된다는 경고를 표시한다. 시간이 겹쳐도 저장은 진행하고 겹치는 계획 ID를 응답한다. 구현 완료 전 이 동작을 테스트로 증명한다.

## 9. FastAPI 계약(초안)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/chat` | `{session_id?, message}` → `{session_id, run_id, answer, recommendations, excluded, events, warnings}` |
| POST | `/api/plans` | 계획 저장 → 201, `{plan, overlap_warnings}` |
| GET | `/api/plans` | 목록 |
| GET | `/api/plans/{id}` | 상세 |
| PATCH | `/api/plans/{id}` | 변경 + 겹침 안내 |
| DELETE | `/api/plans/{id}` | 삭제 |
| GET | `/api/logs` | 세션별 실행 기록 목록 |
| GET | `/api/logs/{session_id}` | 세션의 이벤트 발생 순서별 상세 |
| DELETE | `/api/logs/{session_id}` | 해당 세션 로그 삭제(계획은 별개) |
| GET | `/api/health` | 서버 준비 상태(비밀 값 노출 금지) |

모든 요청·응답은 Pydantic으로 정의한다. UI는 요청 중 spinner, 응답 후 순서별 실행 타임라인 및 재계획 강조를 제공한다. 스트리밍/SSE 없이 **완료 후 이벤트 목록 반환**도 과제 범위 내에서 충분한 최소안이다.

## 10. 최소 폴더 구조

```text
kbl-go/
  .env                         # 로컬 전용, Git 제외
  .gitignore
  requirements.txt
  README.md
  docs/
    PROJECT_PLAN.md
    REQUIREMENTS.md
    TOOL_SPEC.md
    API_SPEC.md
    VERIFICATION.md
  backend/
    main.py
    config.py
    schemas.py
    db.py
    repositories.py
    agent/
      state.py
      graph.py
      nodes.py
      evaluation.py
      prompts.py
      llm.py
      events.py
      sessions.py
    tools/
      registry.py
      kbl.py
      kakao.py
      weather.py
    routers/
      chat.py
      plans.py
      logs.py
  frontend/
    index.html
    styles.css
    app.js
  tests/
    test_tools.py
    test_agent.py
    test_plans.py
    test_logs.py
    fixtures/
```

## 11. 3일 일정과 게이트

### DAY 1 — 명세/외부 API/계약
1. 프로젝트 골격, 로컬 `.env` 설정, 의존성, 문서/간단한 테스트 환경.
2. **최우선: 16시 이전 3개 외부 API 각각 실측 호출**(사용자 측 로컬 키 사용), 응답 필드/호출 한도/이용 약관 확인. KBL의 식별자→상세정보 연결과 기상청 예보 가능 범위를 반드시 검증.
3. 정규화 Tool 4개 및 실패 계약 테스트, `GET /api/health`, `/docs`, Tool 단독 테스트.
4. 상세 호출 불가능 등 실측 결과에 따라 `PROJECT_PLAN.md`, `TOOL_SPEC.md` 수정 후 구현 진행 여부 결정.

### DAY 2 — 메인 Agent, 이벤트, DB
1. `AgentState`, 분기형 LangGraph, Tool Registry, 캐시와 재계획 상한.
2. 세션 요약 Memory, 이벤트 발행/구독 Logging Agent(LLM 없음), SQLite.
3. 계획 CRUD(중첩 경고), 실행 로그 목록/상세/삭제, 테스트.

### DAY 3 — UI, 검증, 제출
1. 프론트 화면 API 연결(대화/계획/실행 타임라인/오류/로딩).
2. 정상, 재계획, 상한, Tool 실패, Tool 불필요, 이어 말하기, 시간 중복 계획, 로그 구독 해제 테스트.
3. README, 요구사항 정의서, Agent 설계, Tool 정의서, API 명세, 검증 결과·캡처·실행 로그 샘플 준비.
4. 3일차 오후 제공 셀프 체크리스트 반영. 시간이 남을 때만 F3022(RAG) 검토.

## 12. 검증 및 완료 기준

- **모든 F3001~F3019** 구현+테스트/화면/로그 증빙, **NF3001~NF3007** 점검.
- API 3종 **성공·실패 케이스**: HTTP 상태뿐 아니라 실제 응답 JSON·필요 필드까지 확인. 실제 검증 전에는 통과 표시하지 않는다.
- 도메인 3개 대표 제약 요청 / 5개 필수 검증 시나리오(일반 성공, 재계획, 상한, Tool 실패, Tool 없는 발화) 실행 결과·기대/실제 차이 기록.
- Tool 재사용 증명: 동일 요청의 재계획 시 동일 인자·동일 결과 재호출 횟수 0.
- Logger 구독 해제 시 정상 응답; 이벤트 세션별 분리; 로그 수정 API 없음.
- 일정 중첩 저장 허용+경고; UI 즉시 갱신.
- `.env` 추적·노출 없음; 소스/화면/로그의 키·스택트레이스 노출 검사.
- 실행 성능 실측과 문제 발생 단계 진단 기록.
- 제출: 요구사항 정의서, Agent 설계 문서, Tool 정의서, API 명세서, 구현 코드, 검증 문서/샘플 로그/캡처, README, 제공 셀프 체크리스트.

## 13. 설계 변경 시 갱신 기준

- KBL 응답 필드·Tool 이름/인자 변경 → §6~7, `TOOL_SPEC.md`, Agent State, Tool 테스트.
- LLM 모델·Agent 노드·분기 변경 → §4~6, Agent 설계, graph 테스트.
- DB 컬럼/겹침 계산/로그 스키마 변경 → §8~9, `API_SPEC.md`, CRUD 및 로그 테스트.
- API 경로/요청·응답 변경 → §9, `API_SPEC.md`, 프론트 fetch, `/docs` 캡처.
- UI/제출/요구사항 충족도 변경 → §2, §11~12, `REQUIREMENTS.md`, `VERIFICATION.md`, README.

각 변경은 '이전 설계 / 변경 내용 / 변경 이유 / 영향받는 테스트'로 짧게 남긴다.

## 14. 현재 미확인 사항(중요)

1. KBL 식별자·상세 경로·구장·시각 필드는 정상 실측했다. 장기 안정성·사용 허가·대회 선택 정책은 미확인이다.
2. 카카오/기상청 정상 인증·응답 필드는 실측했다. 호출 한도·이용 조건·인증 실패 응답의 실제 형태는 미확인이다.
3. KMA 미래 예보 가능 범위가 사용자 요청 날짜를 포함하는지.
4. 이번 ZIP 안의 기존 RAG는 `src/rag/graph.py`와 `src/vectorstore/store.py` 등을 포함하지만 **현재 MVP 구현에 통합하지 않는다**.

이 네 사항은 실제 로컬 실행 및 응답 증거로 확정하고, 그 전에는 성공 판정을 하지 않는다.

## 15. 진행 현황 — 작업 01 (2026-11-18)

설계 초안 상태를 유지하며 사용자 승인된 리뷰 변경만 §7 및 환경 설정 설명에 반영했다. 아래는 현재 구현 현황이며 미검증 정책을 임의 확정하지 않는다.

- Issue: #1 / 브랜치: `feat/project-setup-api-validation`.
- 완료: 설계 저장, 최소 FastAPI health·Swagger, 로컬 `.env`·Git 제외·의존성, 네 Tool 입력/출력·오류 및 Registry, API 검증 스크립트.
- 실측 완료: KBL `fromDate/toDate=YYYYMMDD`, `tcodeList`, `Channel=WEB`, `TeamCode=XX`; 목록 `gmkey` → `/match/{gmkey}` 상세 HTTP 200. 2026-11-18~25 7개, 과거 날짜·팀 필터·빈 결과 확인. F3003 구현 가능 근거 확보.
- 검증 완료: 최신 오프라인 테스트 32개 통과, 경고 1건; pip check 통과. 이전 실제 Uvicorn health/docs/openapi HTTP 200, 세 API 정상 호출 성공. 이번 리뷰 수정에서는 외부 API를 재호출하지 않았다. mock 성공과 실제 통신 성공을 구분한다.
- 미완료: 예보 마지막 시각·인코딩 형태별 인증·장소 일치·각 API 호출 한도/이용 허가 미확인.
- Task 02에서 기본 추천 범위를 정규리그로 지정했다. 2026-11-19 재실측한 `R/1`과 `정규시즌` 대응값을 적용하며 그 외 값은 충족으로 판단하지 않는다.
- 명세 PDF가 현재 폴더에 없어 전체 필수 라이브러리 버전 대조는 보류. LangGraph 1.2.10은 dry-run 설치 가능성만 확인했다.
- Task 01은 PR #2로 main에 병합되었다 (2026-11-19 08:44 KST). 이후 Main Agent 진행 현황은 §16을 따른다. UI·CRUD·RAG·별도 로깅 Agent는 미구현이다.
- 상세 증거와 명령: `docs/VERIFICATION.md`. 내부 작업 전달서·체크리스트·PR 초안은 로컬 보존하고 Git 추적에서 제외한다. 번호를 늘린 새 교환 문서 없이 기존 파일을 재사용한다. 공유 설계·검증 문서는 계속 추적한다.
- 다음 작업: 대회 범위·API 제약을 검토하고 승인된 설계 변경만 반영 → 다음 Issue 구현.

### 작업 01 추가 검증 — .env 적용 (2026-11-18 13:41 KST)

- 사용자 지시에 따라 `.env.example` 삭제를 유지하고 `.env` 직접 설정 방식으로 README·Git 제외 규칙을 정리했다. 기존 `load_settings()`가 루트 `.env`를 읽으므로 설정 코드 수정은 불필요했다. `.env` 값은 출력하거나 Git에 추가하지 않았다.
- 최신 실측: KBL 목록·상세, 카카오 장소, 기상청 예보 네 Tool 모두 성공. 검증 스크립트 종료 코드 0. 위의 키 없음 기록은 이전 실행 이력이며 현재 상태는 이 항목이 우선한다.
- Kakao HTTP 200: 잠실학생체육관 검색 → 서울특별시교육청 학생체육관 후보 1개, 도로명 주소·좌표·장소 링크 확인. 실제 경기장 일치 검증은 미완료로 유지한다.
- KMA HTTP 200 / 서비스 코드 00: 2026-11-18 11:00 발표, 서울시청 격자 (60,127), 15:00 예보 기온 9℃·강수확률 30%·강수없음 확인. 이 값은 특정 시각 실측 예보이며 미래 고정 데이터가 아니다.
- 남은 검증: 예보 제공 마지막 시각, 인증 실패 응답의 실제 형태, 계정별 한도, 장소 일치, KBL 대회 범위 및 사용 허가. 설계 초안 상태는 유지한다.

### PR #2 리뷰 반영 — 2026-11-18

- 이전: `forecast_at`에 발표 기준시각을 반환. 변경: 대상 정시로 수정하고 `issued_at`을 별도 보존. 이유: 예보 시각 의미 혼동 해소. 영향: Weather 스키마·Tool·시각/부분 데이터 회귀 테스트.
- 이전: 예상하지 못한 내부 예외도 `UPSTREAM_ERROR`. 변경: `INTERNAL_ERROR` 추가. 이유: 내부 처리 오류와 외부 API 실패 구분. 영향: 공통 오류 스키마·Registry·오류 격리 회귀 테스트.
- 강수확률 null과 `available` 의미는 §7 및 README에 명시했다. 전체 Agent 판정은 구현하지 않았다.
- 대회 종류 실측값은 보존하지만 추천 대상 대회 선택 정책은 계속 미확정이다.

## 16. Task 02 — Issue #3 Main Agent (2026-11-19)

### 구현 현황
- PR #2 병합 확인 후 최신 main `53c20ca`에서 `feat/langgraph-main-agent` 생성.
- LangGraph **1.2.10 실제 설치·실행**. `AgentState`·6개 Node·조건부 Edge·최대3회 재계획 구현.
- GMS `gpt-6-sol`의 OpenAI 호환 JSON 모드로 analyze/plan/respond 호출, Pydantic 검증. 분석의 `changed_fields`와 명시 조건 필드가 정확히 일치해야 하며 후속 발화는 그 필드만 병합한다.
- LLM은 실제 경기·위치·예보 값을 생성하지 않는다. 응답은 허용된 안내 문장을 LLM이 선택하고 실제 추천 사실·사유는 Python으로 렌더링한다.
- 기존 `registry.invoke()`와 네 외부 Tool을 그대로 재사용한다. 목록 ID→상세, 상세 구장명→장소, 공식 이름·주소로 대조한 장소 좌표+시작시각→날씨 전달.
- 검증 결과 `met/unmet/unknown`, 강수확률 null/예보 대상시각 불일치/조회 실패는 충족으로 처리하지 않는다. low_rain은 확인된 확률 오름차순이며 숫자 상한을 만들지 않는다.
- 실행 내 캐시, 원조건과 완화조건 분리, 메모리 세션 200개 조건·결과 요약, 요청별 EventBus, `POST /api/chat` 및 Pydantic 요청·응답 구현.
- `RUN_COMPLETED`는 그래프 실행 종료를 의미하며 일부 Tool 오류는 errors에 남을 수 있다. 분석·계획 등 실행을 막는 실패는 RUN_FAILED. 이벤트에 예외 원문/키를 기록하지 않는다.
- 전체 pytest **67 passed**, pip check 통과. 기존 Task01 32건 포함. 실제 HTTP에서 정상 추천·후속 조건 변경·1회 재계획/캐시·인사 무호출 확인. 상세 시각·호출·결과는 VERIFICATION.md에 기록.

### 승인된 구체화·변경과 영향
- 이전 SQLite 세션 계획 → 이번 단계는 Task02 지시에 따라 별도 MemorySessions로 최소 구현. 다음 Issue에서 저장 책임을 교체한다. 재시작/eviction/다중 worker 복구는 지원하지 않는다.
- 대회 정책 미확정 → 사용자 지정 기본 정규리그와 KBL 실측 R/1 근거로 기본 필터 확정. 영향: evaluation 및 비정규 대회 회귀 테스트. EASL/D리그로 자동 확대하지 않는다.
- 장소 유사 후보 미확정 → 공식 출처로 대조한 잠실학생·안양 정관장·수원 KT 3곳만 이름/주소 일치 확인. 다른 구장은 unknown. 표와 출처는 evaluation.py 및 VERIFICATION.md. 좌표는 카카오 실측값을 사용한다.
- 폭주 방지를 위해 단일 날짜 범위 최대31일, 명시 대안 범위 최대3개, 세션200개 제한. 범위를 넘으면 구조화 검증 오류로 처리하며 임의로 기간을 자르지 않는다. 후보 목록의 앞부분만 잘라 적합 후보를 놓치는 구현은 리뷰 후 제거했다.
- 서비스 실패는 조건 완화로 해결되지 않으므로 UPSTREAM_ERROR/TIMEOUT도 재계획 중단. 다른 후보의 잔여 작업은 계속한다. 인증 실패·후반 적합 후보 누락·조건 패치 불일치 회귀 테스트로 검증했다.

### 남은 항목
- SQLite CRUD·세션 영속화, Logging Agent 구독/저장, UI, RAG는 범위 밖.
- 단일 프로세스 공통 세션 잠금으로 다른 사용자도 대기할 수 있다. per-session 잠금 개선은 이번 범위에서 보류한다.
- 공식 구장 대조표는3곳만 지원. 나머지 구장·예보 마지막 시각·실제 인증 실패/쿼터 초과·API 사용허가/한도는 미검증.
- 명세 PDF가 없어 추가 고정 버전 전체 대조는 보류하며 설치된 LangGraph 고정 버전은 임의 변경하지 않았다.
- Issue #3 브랜치로 의미 단위 커밋·push, 구현 및 테스트 결과를 하나의 PR로 제출한다. 자동 merge하지 않는다.
- 구현과 검증은 push 완료. 사용자 승인 후 [PR #4](https://github.com/ckdmstn/AGENT_BASKETBALL_PJT/pull/4)를 생성했다. `Refs #3`로만 연결하며 Issue 종료 및 merge는 사용자가 진행한다. 이전 Closes 연결의 자동 검토 거부 상태는 해소되었다.

### PR #4 리뷰 보완 (2026-11-19)
- 지역 비교: 광역 정식명/약칭을 양쪽에 같은 표로 적용하고 주소 선행 행정구역만 비교한다. 도로명·숫자가 시작되면 탐색을 중단한다. 광역을 판별할 수 없거나 요청한 하위 행정구역 정보가 없으면 unknown이다. 장소의 공식 이름·주소 일치 검증과 지역 조건은 별도 checks로 유지한다.
- 판단 이벤트: analyze/plan의 기존 LLM_DECISION 필드를 유지하며 Analysis/WorkPlan.reason 기반 공개 판단 요약을 추가한다. 구독자 전달 전에 설정 키 정제, 인증·예외 표현 검사, 대화 원문 포함 검사, 최대120자 제한을 적용한다. 비어 있거나 부적절하면 결정적 짧은 요약으로 대체한다. 장문 추론·원문 전체 대화를 저장하지 않는다. 구독자 오류 격리는 유지한다.
- 응답: 경기 사실을 유지하면서 checks의 충족 근거를 Python으로 렌더링한다. 제외·미확인 후보는 첫3개에 대해 상태별 핵심 사유 최대2개씩 요약하고 전체 recommendations/excluded/checks는 그대로 반환한다.
- 이전 검토에서 발견한 허용 조건의 한계: Pydantic만으로 사용자 의도를 검증할 수 없었다. 이때의 잘못된 허용 플래그 재현은 아래 최종 보완에서 재계획0회로 수정했다. 전체 한국어 의미를 이해하는 검증기를 구현한 것은 아니다.
- 최신 검증: 전체91개 통과(기존67개 유지, 추가24개), pip check 통과. 이번 리뷰 수정에서는 실제 LLM·외부 API를 재호출하지 않았다. 상세 RED/GREEN과 대상 테스트는 VERIFICATION.md에 기록한다.
- 새 Issue/PR 없이 #3/PR #4에 보완 커밋을 push한다. Refs #3 유지, merge 및 Issue 종료는 수행하지 않는다.

### PR #4 최종 보완 — 조건 완화 권한 (2026-11-19)
- `permissions.py`의 작은 결정적 검증기가 LLM 플래그와 독립적으로 현재 발화의 지원 문법을 검사한다. 검증된 팀/대체 날짜 권한을 Conditions와 별도로 저장하고, next_alternative에서도 권한을 다시 검사한다. 과거 세션의 조건 플래그만 있고 검증 기록이 없으면 권한으로 인정하지 않는다.
- 지원 예: `LG 경기 없으면 다른 팀도 괜찮아`, `다른 팀도 괜찮아`. 팀 약칭·조건절·허용 종결어의 제한된 직접 표현만 인정하며 임의 앞문맥을 붙여 허용을 추출하지 않는다. 지원하지 않는 허용·인용·의문·모호한 표현은 자동 허용으로 해석하지 않고 확인 경고를 반환한다.
- 대체 날짜 지원 예: `대체 날짜: 2026-11-20 허용해`, `대체 날짜: 2026-11-20,2026-11-21~2026-11-22 허용해`. 정확한 ISO 날짜/범위만 최대3개 인정한다. LLM이 제안한 다른 날짜는 권한에 넣지 않는다. 상대 날짜·자연어 대체 기간·복잡한 조건부 허용은 자동 해석하지 않는다.
- `LG 경기만 추천해 줘`, `LG 경기 아니면 추천하지 마`, `다른 팀은 안 돼`, `다른 날짜는 안 돼`, `날짜는 바꾸지 마`, `방금 허용은 취소해` 등 지원 부정·철회 표현은 허용보다 우선한다. 새 허용과 충돌하면 보수적으로 중단한다.
- 같은 세션의 팀만 바꾸는 중립 후속 발화는 이전 검증 권한을 유지한다. 철회·불명확한 권한 축소는 LLM 처리 전에 세션에 반영하며 새 권한을 선부여하지 않는다. 이후 분석/계획이 실패해도 철회는 되돌리지 않는다. 저장소 메모리 한계는 그대로다.
- 원조건/활성조건 분리, 최대3회, Tool 캐시, 기존 그래프 구조는 유지했다. 최종116개 테스트 통과(기존91개 시나리오 유지 및 신규25개), pip check 통과. 기존 무단 허용 재현 기대값은0회로 바꾸고 허용/최대3회 전제의 합성 입력은 지원 문법으로 구체화했다. 실제 LLM/API는 재호출하지 않았다.
- 보장 범위는 지원 문법과 검증 메타데이터에 근거한 재계획 권한 검사다. 정규표현식으로 모든 한국어·다중 의도·부정 범위를 이해한다고 주장하지 않는다. 일반 날짜·지역·팀 등 원조건 추출 자체의 의미 정확성은 여전히 LLM의 한계이며 이번에 새 LLM 검증 Agent를 추가하지 않았다.

## 17. Task 03 — Issue #5 계획 관리와 실행 로그

| 테이블 | 저장 내용 및 키 |
| --- | --- |
| `plans` | 자동 증가 `id`, 선택 `session_id`, 경기 식별자·홈/원정 팀·장소·주소·메모·시작/종료 시각·생성/수정 시각. `(start_at, id)` 인덱스. 경기일은 KST 시작 시각에서 계산한다. |
| `sessions` | `session_id` 기본키, JSON 원조건과 검증된 완화 권한, 직전 추천 요약, 갱신 시각. |
| `agent_events` | `(session_id, run_id, sequence_no)` 복합 기본키, 발생 시각, 이벤트 종류, 노드·Tool 이름, 허용된 JSON 메타데이터. |

- SQLite 연결·초기화를 `backend/database.py`에 두었다. 계획 생성·수정과 중복 검사를 하나의 `BEGIN IMMEDIATE` 트랜잭션에서 실행한다. 모든 계획의 시각은 고정 정밀도 KST 문자열로 비교하며, 서로 닿기만 하는 일정은 겹치지 않는다. PATCH에서 기존 필드와 합친 뒤 시간 범위를 확인하고, 수정 대상 계획 자체는 검사에서 제외한다.
- FastAPI는 `SQLiteSessions`를 주입한다. 팀·대체 날짜 권한 철회는 LLM 분석 전에 별도 커밋하므로 이후 분석·계획 실패에도 보존된다. 이전 휘발성 저장소의 데이터는 메모리를 종료하면 사라진다. SQLite는 같은 DB 파일로 재시작 시 복원하며 자동 만료가 없다. 단일 프로세스에서 대화 턴을 직렬화한다.
- Logging Agent가 실행별 EventBus 구독자로 동작한다. 판단 분류·변경된 필드명·Tool 성공 여부·재계획 횟수 등 정형 필드만 기록한다. 자유 작성 판단 근거, Tool 인자, 원본 요청·응답과 예외는 저장하지 않는다. 이벤트 쓰기 오류는 EventBus에서 구독자 호출 단위로 격리된다.
- 로그 상세는 실행 시작 순으로 그룹화하고 실행 내 이벤트는 `sequence_no`로 정렬한다. 삭제는 해당 세션의 이벤트 행에만 적용된다. 전체 목록과 상세의 페이지네이션, 로그 자동 정리, 여러 worker의 동시 채팅은 후속 과제다. API 응답 구조는 README와 OpenAPI에 정리했다.

## 18. Task 04 — Issue #7 웹 UI

- FastAPI가 `/`에서 한국어 단일 페이지를, `/static/`에서 CSS·Vanilla JavaScript를 제공한다. Fetch 요청은 동일 origin의 기존 채팅·계획·로그 API를 사용한다.
- 추천 화면은 실제 `Assessment`의 검증 상태·근거와 확인된 경기장 주소를 표시한다. 강수확률 미확인과 예보 제공 여부를 구분한다. 원조건과 활성조건, 재계획 내역은 별도로 표시한다.
- 계획 조회·생성·수정·삭제를 기존 API에 연결한다. 수정은 변경한 메모와 종료 예정 시각만 보낸다. 실행 기록은 세션과 실행 단위로 표시하고 이벤트 순서, 캐시 재사용, 판단 이유 코드를 해석한다.
- 브라우저는 현재 세션 ID만 저장한다. 새 대화 시 기존 서버 세션은 보존한다. 화면 데이터는 DOM 텍스트로 렌더링하고 장소 링크는 HTTP(S)만 허용한다. 서비스는 인증 없는 로컬 단일 사용자 MVP다.

## 19. Task 05 — Issue #9 통합 검증과 시연

실제 LLM, KBL 일정·상세, 카카오 경기장 검색을 사용해 Chromium에서 과거 경기 추천과 계획·로그 관리까지 검증했다. 같은 경기장 좌표의 현재 기상청 예보는 정상 응답했다. 과거 경기 시각의 예보는 범위 제한으로 미확인 상태였다. 재계획, 권한 철회, 서버 재시작 후 SQLite 복원과 로그 삭제 범위를 확인했다.

실제 시연은 입력 날짜의 경기와 검증된 경기장을 사전에 확인하고 시작한다. 경기 시각의 예보가 필요하면 단기예보 범위도 확인한다. 서비스 장애나 경기 없음에 대비한 Mock 시연과 실제 검증 증적은 [검증 기록](VERIFICATION.md)에 구분했다.

## 20. Task 06 — Issue #11 라이트 테마와 팀 완화 권한

확정 딥 네이비 팔레트를 헤더·채팅·추천·계획·로그에 적용했다. 권한 버튼은 독립적인 한국어 메시지를 기존 `POST /api/chat`으로 전송한다. 기존 세션의 정확한 버튼 문구는 다른 조건을 유지하는 후속 발화로 처리하며, 권한 부여·철회는 기존 검증 문법과 SQLite 저장 절차를 따른다.

채팅 응답의 `team_permission`은 저장을 마친 권한 또는 해당 응답의 확인 필요 상태를 반환한다. 실패 응답에서는 철회 선반영 후의 저장 상태를 반환할 수 있다. 실제 팀 조건 해제는 원조건·활성조건·재계획 이력에서 별도로 표시한다. 권한 읽기 전용 API는 추가하지 않았으며 브라우저는 저장된 세션 ID로 다음 채팅을 보낸 뒤 상태를 다시 확인한다.

## 21. Task 07 — Issue #13 홈경기장 검증 확대

조사한 10개 구단의 9개 홈경기장을 공식 자료·KBL 일정·카카오 장소 응답으로 교차 확인했다. 이전 3곳에 창원·고양·부산·대구·울산·원주 6곳을 추가했다. 서울 삼성과 서울 SK는 조사 기간 중 잠실학생체육관을 사용했다.

등록 이름과 별칭은 완전 일치를 사용한다. 도로명주소는 시·도 표준 약칭과 공백만 정규화한 뒤 전체를 비교한다. 주소 후보 중복·좌표 누락·API 실패 등은 구체적인 미확인 사유로 남긴다. 검증 좌표만 날씨에 넘기며, 정규리그·지역·예보의 충족 여부는 각각 평가한다.

## 22. Task 08 — Issue #15 추천 결과 요약과 경기 상세

왼쪽 메시지 영역은 `recommendations`의 경기명·시작 시각·경기장을 응답 순서대로 요약한다. 일반 대화는 텍스트를 유지하며 조회 실패·빈 결과는 구조화된 상태로 분리한다. 오른쪽 경기 카드는 HTML `details/summary`이며 검증 상태와 기본 경기 정보를 항상 표시한다. 주소·날씨·검증 사유·계획 저장은 상세에 있다. 제외 후보는 그룹을 먼저 열고 각 경기를 개별적으로 펼친다. API와 Agent 판정은 유지한다.

## 23. Task 09 — Issue #17 메모만으로 계획 저장

웹 모달에는 선택 메모만 입력하며 새 계획은 `end_at: null`로 저장한다. 웹의 수정 요청은 `note`만 보내므로 기존 종료 시각이 보존된다. SQLite 컬럼과 API 요청·응답 스키마는 유지한다.

쓰기 트랜잭션 내에서 동일 경기, 동일 절대 시작 시각, 저장된 시간 구간 순으로 경고 이유를 판정한다. 종료 시각이 없는 계획은 시작 시점만 비교한다. 구간 비교는 종료 경계를 제외하며, 자기 자신과 중복 ID는 결과에서 제외한다. 경고와 함께 정상 저장한다.

## 24. Task 10 — Issue #19 동일 경기 재저장 방지와 삭제

계획 POST는 기존 `BEGIN IMMEDIATE` 쓰기 트랜잭션에서 `match_id`를 조회하고 없을 때만 INSERT한다. 같은 ID가 있으면 409를 반환한다. 같은 DB에서 이 API를 따르는 생성 요청은 SQLite 쓰기 잠금으로 직렬화된다. UNIQUE 제약이나 마이그레이션 없이 기존 중복 데이터를 보존하며, 직접 SQL 등 검사 경로를 우회하는 쓰기에는 이 정책이 적용되지 않는다.

다른 경기의 동일 시작 시각과 확인된 구간 교차는 기존 성공 응답의 일정 경고로 유지한다. 목록과 상세 모달은 같은 삭제 함수·API를 사용한다. 취소 시 요청을 보내지 않고, 실패 시 계획을 유지하며 성공 시 목록을 갱신한다.

## 25. Task 11 — Issue #21 채팅 체크박스 권한

`ChatRequest.allow_other_teams`는 엄격한 선택적 불리언이다. 명시된 값은 자연어의 팀 권한보다 우선하고, 충돌 사실을 경고로 알린다. 생략·`null`은 기존 문장 문법을 사용한다. AgentRunner는 그래프 호출 전에 기존 추천 조건을 보존한 채 팀 권한을 저장한다. LLM이 실패해도 적용된 값은 유지된다.

Analyze가 사용자 메시지에서 조건을 추출하더라도 팀 권한은 검증기가 결정한다. 날짜 권한은 별도의 기존 문법을 사용한다. 권한과 실제 완화는 독립이며, 기존 세션 복원·최대 재계획 횟수·검증 조건 판정은 유지한다. UI는 체크박스 선택과 서버 확인 상태를 별도로 표시한다.
