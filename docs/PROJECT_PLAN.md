# KBL GO — AI 한국프로농구 직관 플래너

> 상태: **설계 초안 v0.1 / 외부 API 실측 검증 전**  
> 기준: `AI코어프로젝트_3회차_요구사항정의서.pdf` (필수 F3001~F3019, 비기능 NF3001~NF3007)  
> 원칙: 명세서의 필수 항목을 우선하며, 과제 도메인 표현만 KBL로 변경한다. 이 문서에 기재된 외부 API 결과는 이번 검토에서 재호출하여 입증하지 않았다.

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
- `plan`: 요청과 이미 저장된 Tool 결과를 보고 실행할 Tool 이름·인자·순서의 작업 목록 생성. 인사/도움말은 Tool 0개.
- `execute_tools`: 레지스트리에 등록된 Tool만 순서대로 호출; 경기 목록의 `match_id`를 상세 Tool에, 상세정보/경기장에서 확인한 명칭을 카카오 Tool에 전달. 실패해도 다른 후보를 진행; 조회 결과를 실행 단위 캐시로 보존.
- `evaluate`: 실제 경기 일시, 팀, 확인된 경기장 주소/행정구역, 실제 조회한 강수확률을 필터와 비교해 근거를 반환. 모르는 값은 `unknown`이며 임의로 합격 처리하지 않는다.
- `replan`: 충족하는 후보가 없고 사용자가 명시적으로 허용한 완화(예: 선호 LG→타 팀)나 다른 날짜 범위가 있을 때만 대안 작업을 구성. 기존 결과 재사용. 최대 3회 후 중단 사유 반환. 인증 실패/키 누락은 재계획 금지.
- `respond`: 추천 경기/근거/주소/날씨 예보 기준시각/제외 사유/오류/조회 한계를 포함하는 구조화된 응답.

Edge: START→analyze→plan→(tasks 빈 경우 respond, 아니면 execute_tools)→evaluate→(적합하면 respond, 대안 있으면 replan→plan, 상한 도달 시 respond)→END. `replan_count`는 **재계획 분기 횟수**로 정의하고 최대 3.

**우선 검증:** KBL 실제 API가 경기 식별자·상세정보·시작 시각·홈 경기장 식별자를 제공하는지, 미래/지난 일정 검색이 가능한지. 이것이 F3003의 충족 여부를 좌우한다.

## 7. Tool 정의와 실패 계약

공통 결과: `{"ok":true,"data":{},"meta":{"source":"...","requested_at":"...","actual_query":"..."}}` 또는 `{"ok":false,"error":{"code":"...","message":"..."},"meta":{...}}`. Tool은 raw traceback/API key를 반환하지 않는다. 실패 코드: `INVALID_INPUT`, `MISSING_API_KEY`, `UPSTREAM_ERROR`, `TIMEOUT`, `NO_RESULT`, `UNSUPPORTED_DATE`, `MISSING_FIELD`.

| Tool | 사용 시점 / 입력 | 정규화된 출력 |
|---|---|---|
| `search_kbl_games` | 일정 후보가 필요할 때; `from_date`, `to_date`, `team_code?` | `[{match_id, home_team, away_team, start_at?, venue_name?, source}]`, 실제 조회 기준 |
| `get_kbl_game_detail` | 후보 `match_id`로 상세 속성 확인; `match_id`, `date?` | `match_id, start_at?, home_team?, away_team?, venue_name?, status?` (확인된 값만) |
| `search_arena` | 경기장 이름/주소 확인; `venue_name`, `region_hint?` | `name, road_address?, address?, lat?, lon?, place_url?` 또는 NO_RESULT |
| `get_weather` | 경기 일정·위치가 확인되고 예보 가능할 때; `date_time`, `lat`, `lon` | `forecast_at, temperature_c?, precipitation_probability_pct?, precipitation_mm?, available` |

KBL 목록과 상세정보를 같은 공식적으로 확인된 호출 경로에서 가져올 수 있다면 **서로 다른 Tool의 입력/출력과 후보 ID 전달**을 반드시 입증한다. API가 진짜 상세 조회를 지원하지 않는다면 F3003 대응을 설계 변경으로 명시하며, 임의로 상세 호출 성공을 주장하지 않는다. 기상청은 예보 기준시각·격자 좌표 변환(nx, ny)·예보 제공 범위를 엄격히 검증해야 한다. 카카오가 장소명만 유사한 결과를 줘도 실제 KBL 경기장으로 검증 없이 확정하지 않는다. 경기장 이름-주소의 보조 목록은 **공식 정보로 대조하고 출처 기록** 후 사용한다.

### API 연결 및 제한

- KBL: `https://api.kbl.or.kr/match/list` / `Channel: WEB`, `TeamCode` 전달 방식은 실측 확인. 비공식 API이므로 응답 구조·약관·허용 여부 리스크를 문서화.
- Kakao Local: `https://dapi.kakao.com/v2/local/search/keyword.json`, `Authorization: KakaoAK <key>`.
- KMA: 공공데이터포털 데이터 ID `15084084`, `getVilageFcst` (serviceKey, base_date, base_time, nx, ny 등). 실제 엔드포인트/서비스키 인코딩은 실측 확인.
- 날씨 예보 범위를 벗어나면 "예보 제공 범위 밖"으로 표시하고 경기 추천 자체와 분리한다.
- `.env` 예시 키 이름만 `.env.example`에 기재. `.env`, SQLite DB, `.venv`, 캐시, 로그 원본은 `.gitignore`에 추가.
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
  .env.example
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
    agents/
      state.py
      graph.py
      nodes.py
      event_bus.py
      logging_agent.py
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
1. 프로젝트 골격, `.env.example`, 의존성, 문서/간단한 테스트 환경.
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

1. KBL 비공식 API가 안정적으로 제공하는 **식별자·상세정보 경로 및 구장·시각 필드**.
2. 카카오/기상청 인증 키와 호출 한도·약관·응답 필드의 현재 유효성.
3. KMA 미래 예보 가능 범위가 사용자 요청 날짜를 포함하는지.
4. 이번 ZIP 안의 기존 RAG는 `src/rag/graph.py`와 `src/vectorstore/store.py` 등을 포함하지만 **현재 MVP 구현에 통합하지 않는다**.

이 네 사항은 실제 로컬 실행 및 응답 증거로 확정하고, 그 전에는 성공 판정을 하지 않는다.

## 15. 진행 현황 — 작업 01 (2026-11-18)

기존 §1~14 원문과 **설계 초안 v0.1** 상태를 유지한다. 아래는 실측 결과와 구현 현황이며 미검증 설계를 임의 확정하지 않는다.

- Issue: #1 / 브랜치: `feat/project-setup-api-validation`.
- 완료: 설계 원문 저장 확인, 최소 FastAPI health·Swagger, `.env.example`·Git 제외·의존성, 네 Tool 입력/출력·오류 및 Registry, API 검증 스크립트.
- 실측 완료: KBL `fromDate/toDate=YYYYMMDD`, `tcodeList`, `Channel=WEB`, `TeamCode=XX`; 목록 `gmkey` → `/match/{gmkey}` 상세 HTTP 200. 2026-11-18~25 7개, 과거 날짜·팀 필터·빈 결과 확인. F3003 구현 가능 근거 확보.
- 검증 완료: 오프라인 테스트 27개 통과, 경고 1건; 실제 Uvicorn health/docs/openapi HTTP 200; pip check 통과. mock 성공과 실제 통신 성공을 구분한다. 독립 검토에서 발견한 키 반사 응답은 Tool 반환 경계에서 정제하고 회귀 테스트로 검증했다.
- 미완료: Kakao/KMA 인증 키 없음 → `MISSING_API_KEY`, 실제 호출 미실행. 실제 예보 범위·인코딩·장소 일치·각 API 호출 한도/이용 허가 미확인.
- 설계 검토 필요: KBL 결과에 EASL·D리그가 포함됨. 실제 대회 구분을 보존하나 추천 대상 정책은 미확정. 원 설계 §6~7 구체화 및 승인 필요.
- 명세 PDF가 현재 폴더에 없어 전체 필수 라이브러리 버전 대조는 보류. LangGraph 1.2.10은 dry-run 설치 가능성만 확인했다.
- 미구현: LangGraph, UI, CRUD, RAG, 로깅 Agent. PR 생성·push·merge 미실행.
- 상세 증거와 명령: `docs/VERIFICATION.md`. PR 초안: `docs/PR_TASK_01.md`.
- 다음 작업: 로컬 `.env` 키 설정 후 카카오·기상청 재검증 → 대회 범위·API 제약을 검토하고 승인된 설계 변경만 반영 → 다음 Issue 구현.
