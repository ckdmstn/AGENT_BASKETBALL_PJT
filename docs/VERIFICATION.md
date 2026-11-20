# 작업 01 검증 기록

## PR #6 리뷰 보완 — 판단 이유와 로그 저장 실패 (2026-11-20)

- 새 `LLM_DECISION`에는 노드에 따라 `intent_and_condition_extraction`, `tools_for_condition_verification`, `verified_facts_rendering` 코드가 저장된다. `REPLAN_STARTED`에는 `authorized_condition_relaxation`이 추가된다. 기존 정형 필드는 유지한다. 코드는 애플리케이션이 생성하며 자유 텍스트 판단 근거와 입력에서 주입된 코드는 저장하지 않는다. 이전 로그에는 코드가 없을 수 있다.
- SQLite 이벤트 쓰기가 실패하면 표준 로거에 고정 WARNING을 남긴다. 경고에는 식별자·payload·예외 원문·traceback이 없다. 해당 이벤트는 누락될 수 있으며 자동 재시도와 DB 재기록은 없다. 경고는 누락 발생을 알려주며 이벤트별 추적 정보는 제공하지 않는다.
- 기존 저장 실패 테스트에 고정 경고와 예외 비노출 검증을 추가했다. 신규 테스트 1개는 계획·응답·재계획 이벤트에 주입된 자유 텍스트 및 코드가 저장되지 않는지 확인한다.
- `.\.venv\Scripts\python.exe -m pytest -q`는 **143 passed in 9.11s**였다. 기존 142개를 유지했다. `.\.venv\Scripts\python.exe -m pip check`는 `No broken requirements found.`를 반환했다. 실제 외부 API와 LLM은 재호출하지 않았다.

## Task 03 — SQLite 계획 CRUD·세션·Logging Agent (2026-11-20)

| 검증 | 결과 |
| --- | --- |
| 변경 전 `.\.venv\Scripts\python.exe -m pytest -q` | 116 passed |
| 구현 후 동일 명령 | **142 passed in 10.18s**. 기존 116개 유지 및 신규 26개 |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found |

- 임시 SQLite 초기화와 재초기화, 계획 CRUD 상태 코드, 잘못된 시각·필드의 422, 부분 수정 또는 명시적 null, KST 중복·경계 및 동시 생성, 종료 시각 누락 경고를 확인했다.
- 같은 DB를 여는 새 Runner에서 원조건·추천 요약·검증 권한을 복원했다. 사용자별 세션 격리와 팀·대체 날짜 권한의 철회가 분석 및 계획 단계의 LLM 실패 뒤에도 보존되는지 확인했다.
- 로그 API의 실행 구분과 이벤트 순서, 저장 실패 또는 구독 해제 이후 추천 성공, 실패 실행 기록, 합성 인증키·대화 원문·원본 예외 비저장, 삭제 후 계획·대화 세션 및 타 세션 로그 보존을 확인했다.
- FastAPI TestClient로 채팅 연동, `/docs`와 `/openapi.json` 경로 등록을 확인했다. 추적을 비활성화하고 Tool 및 LLM을 모의 실행했다. 실제 LLM이나 KBL·카카오·기상청 API 호출과 다중 worker 환경은 이번 검증에 포함하지 않았다.

## PR #4 최종 보완 — 권한 검증 최신 결과 (2026-11-19)

실제 LLM/KBL/Kakao/KMA API **재호출 없음**. 아래 이전 통합 결과는 당시 실행 이력이며 이번에는 잘못된 합성 LLM 출력·Tool mock으로 권한 검증을 재현했다.

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pip check
```

결과: **116 passed, 실패0**, **No broken requirements found**. 이전91개 테스트의 검증 목적 유지, 신규 `test_permissions.py` 25개 추가. 기존 무단 허용 테스트는 허용을 전제로 한 한계 문서화 대신 올바른0회 기대값으로 변경했다. 기존 캐시/최대3회/철회 테스트는 실제 권한 근거가 되도록 입력 문장만 명확히 했다.

검증 내용:
- LLM이 True를 반환해도 `LG 경기만`, `LG 경기 아니면 추천하지 마`, 모호한 질문·추측·인용은 팀 재계획0회. 명시적 허용은1회와 기존 캐시 재사용.
- 이전 검증 권한으로 팀만 변경하면 유지, 철회가 LLM 출력에 누락/오독되어도 취소, 검증 기록 없는 과거 세션 플래그는 거부.
- LLM이 만든 대체 날짜는 조회하지 않고 직접 ISO 명령에서 확인된 날짜만 재탐색. 잘못된 날짜·허용 철회·상충하는 허용/부정은 거부.
- 모호한 허용은 warnings와 answer에 확인 요청을 표시한다. 최대3회와 원조건/활성조건 분리는 유지.
- 독립 검토에서 철회 후 분석/계획 실패 시 권한이 되살아나는 경로 발견. 팀/날짜×분석/계획의4개 실패 회귀 테스트로 재현 후 수정. 철회는 실행 전 세션 권한 축소로 선반영하고 새 허용은 선부여하지 않는다.
- 무제한 앞문맥을 허용하는 패턴을 제거하고 제한된 직접 팀 표현 전체 절만 인정한다. `허용이 아님: LG 경기 없으면 다른 팀도 괜찮아` 같은 문맥은 허용되지 않는다.

RED 이력: 권한 모듈 미구현 수집 오류 → 초기108통과(기존3개 허용/기간 입력의 지원 문법 구체화 후) → 철회 표현3실패 재현·수정111통과 → 처리 실패 후 철회 지속4실패 재현·수정115통과 → 비허용 앞문맥1실패 재현·수정116통과. 확인 안내 문구의 answer 누락도 단일 실패로 재현 후 수정했다.

한계: 지원 문법 밖의 일반 한국어를 완전히 해석하지 않는다. 복잡한 범위/간접화법/외국어 허용은 미검증이며 자동 grant를 지원하지 않는다. 원조건 추출 자체를 검증하는 별도 Agent는 없다. 이전 메모리 세션·구장3곳·공통 잠금·날씨/이용 조건 제약도 유지한다.

권한 수정은 기존 PR #4에 Refs #3로 반영하며 merge/Issue 종료하지 않는다. 상세 지원 예시는 PROJECT_PLAN 및 README에 기록한다.

## PR #4 리뷰 반영 — 2026-11-19 최신 결과

- 실제 LLM 및 KBL/Kakao/KMA API **재호출하지 않음**. 아래 Task02의 실제 HTTP 결과는 이번 리뷰 수정 전 실행 이력이며, 이번 검증은 오프라인 mock/합성 입력 기반이다.
- 최초 RED: `pytest tests/test_agent.py -q` → 15 failed / 30 passed. 지역 별칭·주소 누락·이벤트 reason 누락·추천/제외 근거 누락을 재현했다. 구현 후 전체90 passed.
- 추가 경계 RED: 광역만 있고 요청 하위 행정구역이 없는 주소 → 1 failed / 13 passed(지역 선택). unknown으로 보완 후 최종 전체91 passed.

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pip check
```

최종: **91 passed, 실패0**, **No broken requirements found**. 기존67개 테스트 삭제·제외 없음.

추가24개 회귀 시나리오:
- 지역13개: 서울/서울특별시, 부산/부산광역시, 경기/경기도 양방향, 다른 광역, 주소 없음, 선행 광역 미판별, 도로명에만 지역명, 잘못된 중간 토큰, 하위 행정구역과 유사 도로명, 하위 행정구역 누락. 공식 장소 확인과 지역 확인 분리도 검증.
- 이벤트1개: analyze/plan reason 기록, 기존 intent/changed_fields/tools 및 sequence 순서 유지.
- 이벤트 보호5개: 실제 설정을 대신하는 합성 키, 인증 헤더, 예외 문자열, 긴 추론, 대화 원문을 analyze/plan reason에 주입. 구독자 수신 전에 정제/대체되고 최대120자임을 검증. 구독자 하나의 실패에도 RUN_COMPLETED 유지.
- 렌더링3개: 추천 경기 사실 및 date/time/region/weather 충족 이유, POP null 미확인 이유, POP 상한 초과 불충족 이유. 기존 구조화 checks도 유지.
- 조건2개: 후속 발화의 타 팀 허용 철회 및 다른 조건 유지, 구조적으로 유효하나 사용자 뜻과 다른 합성 허용 결과의 한계 재현. 기존 비허용 완화 방지·일부 조건 변경 테스트 유지.

주의: 마지막 합성 허용 테스트는 잘못된 LLM 해석이 실제로 통과할 수 있음을 문서화한 것이며, 사용자 의미 검증이 완성되었다는 증거가 아니다. 복잡한 신규 검증기를 추가하지 않았다. reason 보호도 설정 키/의심 표현/길이/원문 검사이며 모든 임의 민감 텍스트를 식별하는 범용 DLP는 아니다.

지역·이벤트·렌더링만 수정했다. SQLite CRUD·Logging Agent·UI·RAG는 미구현을 유지한다. PR #4에 Refs #3로 반영하고 자동 merge/Issue 종료하지 않는다.

## Task 02 Main Agent — 2026-11-19 최신 검증

기준: Issue #3, `feat/langgraph-main-agent`, 선행 PR #2는 08:44 KST main 병합 확인. 기존 Task01 이력은 아래에 유지한다.

### 실행 명령과 오프라인 결과
```powershell
.venv/Scripts/python -m pip install langgraph==1.2.10
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pip check
```

- LangGraph 1.2.10 실제 설치·compile/invoke 실행. langchain-core 1.8.3 등 의존성 설치 성공. 명세 PDF 부재로 나머지 명세 고정 버전 대조는 보류했다.
- 최신 pytest: **67 passed, 실패0**, 기존 Task01 32개 포함. pip check: **No broken requirements found**.
- 이번 설치로 httpx2가 전이 의존성으로 설치되었고, 현재 실행에는 이전 Starlette TestClient 경고가 발생하지 않았다.
- 테스트를 먼저 추가해 미구현 모듈 수집 실패를 확인한 뒤 구현했다. 기반40 → 그래프57 → API62 통과. 독립 검토 보완 시 인증/쿼터 재계획·상세조회 미확인·후반 후보·조건 패치 검증에서 6 실패/24 통과를 확인한 뒤 최종67 통과.
- `tests/test_agent_contracts.py`: 조건 구조·patch 검증, 세션 복사/격리, 구독자 오류 격리, LLM 키누락/타임아웃/HTTP/파싱 실패·성공.
- `tests/test_agent.py`: 실제 StateGraph 실행, ID/구장/좌표/시각 전달, 인사0회, 날짜 누락, POP null, 날씨 불필요 호출 생략, 명시적 팀 완화·캐시, 비허용 완화 방지, 최대3회, Tool 실패, 후속 세션, LLM 실패, 대회/지역/장소 검증, 인증·쿼터 실패 무재계획, 13번째 적합 후보 보존.
- `tests/test_chat_api.py`: POST 응답 구조·후속 발화·입력 오류 비노출·OpenAPI 등록.

### 실제 LLM 및 HTTP 통합 (mock 아님)
- 현재 설정된 GMS `gpt-6-sol`: HTTPS chat/completions JSON 모드 HTTP200 및 구조화 응답 확인. 키·오류 원문은 출력하지 않았다.
- 직접 AgentRunner 실행: 수원 서울SK 강수50% 이하 요청, 네 Tool 성공, 조건 충족1개, 약9.2초.
- 임시 Uvicorn `--host 127.0.0.1 --port 8765` 실행 후 실제 requests HTTP 호출. 로컬 전용 `.verification/check_chat_live.py`로 실행했고 테스트 종료 후 해당 서버만 종료했다.
- 최초 한글 stdin 파이프 테스트는 PowerShell 인코딩으로 입력이 손실되어 Tool 미실행으로 끝났다. 이를 성공 증거로 사용하지 않았고 UTF-8 파일/문자열 인자로 재실행했다.
- 리뷰 수정 후 같은 HTTP 시나리오를 재검증한 최종 결과:

| 요청 | HTTP | 실제 결과 | Tool 실제 호출 / 캐시 | 소요 |
|---|---|---|---|---|
| 2026-11-19 14시 이후 수원 서울SK, 강수확률50% 이하 | 200 | 조건 충족1개, 제외1개, 오류0, 재계획0 | 4 / 0 | 8806.30ms |
| 같은 세션: 팀만 LG로, 없으면 타팀 허용 | 200 | 날짜·시간·지역·강수조건 유지, 선호LG 보존, 활성조건만 팀 완화, 추천1개, 오류0, 재계획1 | 7 / 1 | 12313.05ms |
| 같은 세션: 안녕 | 200 | 추천·제외0, 오류0, 재계획0 | 0 / 0 | 4052.22ms |

health/docs도 HTTP200. 위 Tool 호출은 registry의 실제 네 외부 Tool을 사용했다. 후속 요청의 목록 실제 호출은1회이고 재계획 시 같은 결과를 캐시에서 사용했다. 최종 안전한 응답 샘플 `.verification/chat-live.json`은 Git 제외다. 날씨는 이 통합 검증에서 카카오가 반환하고 공식 이름·주소로 대조한 실제 경기장 좌표를 사용했다.

### 정책 실측·장소 출처
- 2026-11-19~25 KBL 목록 HTTP200: R/1/정규시즌 2개, D1/2/D리그1차 3개를 같은 원본에서 확인했다. R/1만 추천 대상으로 판단하며 다른 값이나 누락은 정규리그로 추정하지 않는다.
- 장소 이름·주소를 다음 공식 출처로 대조했다. 소스 표는 `backend/agent/evaluation.py`에 보존하며 좌표는 하드코딩하지 않는다.
  - [학생체육관 공식 안내](https://ssg.sen.go.kr/fus/MI000000000000000366/html/cont0010v.do): 학생체육관 / 송파구 올림픽로25. KBL 실측의 잠실학생체육관 이름과 대조.
  - [KGC 공식 소개](https://www.kgc.co.kr/intro/kgc-introduction/affiliate.do): 안양 정관장 아레나 / 안양시 동안구 평촌대로389.
  - [KBL 공식 미디어 가이드](https://www.kbl.or.kr/upfiles/ebook/2425_media_guidebook.pdf), [수원시 공식 안내](https://www.suwon.go.kr/webcontent/ckeditor/2022/7/27/e471c9f8-36b0-402b-8187-5de1888c7db5.pdf): 수원KT/서수원칠보 / 수원시 권선구 서수원로577번길171.
- [LangGraph 공식 StateGraph 참조](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)를 참고하되 실제 동작은 설치된 1.2.10의 테스트로 확인했다.

### 리뷰 결과·남은 한계
- 독립 검토의 중요 지적 2개(인증 실패 시 재계획, 앞12개 후보 절단)를 재현 테스트로 수정했다. 조건 patch의 명시 필드와 changed_fields 불일치도 안전하게 거부한다. 상세 조회 실패는 unmet이 아니라 unknown으로 수정했다.
- 보류한 경미 항목: 전체 실행을 세션 저장소 공통 잠금으로 보호하므로 다른 세션도 대기한다. 단일 프로세스 MVP이며 동시 처리 개선은 후속 검토 대상이다.
- 메모리200세션·재시작 복구 없음·다중 worker 비공유, 기간31일 제한, 장소대조3곳만 지원. 기간별 후보 수가 많으면 실제 호출·지연이 증가한다.
- 실제 인증 실패/쿼터 초과/각 발표 경계·예보 마지막 시각/전체10개 구장·KBL 사용허가·한도는 미검증이다. 해당 실패 처리는 mock으로만 테스트했다.
- SQLite CRUD·Logging Agent 구독/저장·UI·RAG는 미구현이며 Issue #3 범위 밖이다. 자동 merge하지 않는다.
- GitHub 최종 상태: 사용자 승인에 따라 `Refs #3`로 [PR #4](https://github.com/ckdmstn/AGENT_BASKETBALL_PJT/pull/4) 생성 성공. 기존 로컬 초안을 재사용했다. Issue 종료 및 merge는 수행하지 않았다. 이전 Closes 연결의 자동 승인 거부 기록은 현재 상태가 아니다.

## PR #2 리뷰 수정 검증 — 2026-11-18

- 실제 외부 API **재호출하지 않음**. 아래 13:41의 실제 정상 호출 기록은 수정 전 버전의 이력이다. 수정 후 검증은 네트워크 격리 mock 회귀 테스트다.
- RED: 전체 pytest 4 실패 / 28 통과. 대상 시각 대신 발표 시각 반환 2건, 내부 예외를 UPSTREAM_ERROR로 반환 2건을 재현했다.
- GREEN: `.venv/Scripts/python -m pytest -q` → **32 passed, 1 warning**, 실패 0. `.venv/Scripts/python -m pip check` → **No broken requirements found**.
- 추가 테스트 5건: UTC 06:45 입력 → KST 대상 15:00 / 발표 11:00 분리, 기온만 있는 부분 응답의 POP null 보존, 내부 RuntimeError, 잘못된 반환 구조, 외부 연결 오류 유지. 기존 27건도 통과했다.
- `forecast_at`은 실제 대상 정시, `issued_at`은 조회 발표 기준시각이다. `available`은 일부 데이터 존재이고 강수 조건 충족이 아니다. 강수확률 null은 미확인이다. 조건 판정은 DAY 2 범위로 미구현.
- 공통 오류 코드에 INTERNAL_ERROR를 추가했다. 내부 예외 원문·traceback·키는 반환하지 않는다.
- 내부 작업 전달서·체크리스트·PR 초안 3개는 Git 추적에서 제외하되 로컬 보존한다. 기존 파일을 재사용한다. 공유 설계·검증 기록은 유지한다.
- 기존 PR #2는 open, 미병합이다. 같은 브랜치에 리뷰 보완 커밋을 push하고 본문을 갱신한다. 새 Issue/PR은 생성하지 않는다.

## 최신 재검증 — 2026-11-18 13:41 KST

사용자가 `.env.example`을 삭제하고 `.env`에 키를 입력했다. 기존 설정 코드가 이미 루트 `.env`를 로딩하여 코드 변경 없이 인증됐다. README와 `.gitignore`만 현재 사용 방식에 맞게 정리했다. 아래의 초기 키 누락 기록은 이전 실행 이력이다.

실행 명령: `.venv/Scripts/python scripts/check_external_apis.py --from-date 2026-11-18 --to-date 2026-11-25 --output .verification/api-check.json`

**종료 코드 0, 네 Tool 모두 ok=true.**

| API | 최신 실측 |
|---|---|
| KBL 목록/상세 | 각각 HTTP 200, 목록 7개, 첫 gmkey `S49G01N75` 상세 일치 |
| Kakao | HTTP 200, 장소 후보 1개. 서울특별시교육청 학생체육관 / 서울 송파구 올림픽로 25 / 위도 37.51219787219792, 경도 127.07537857414752 / 장소 링크 확인 |
| KMA | HTTP 200, resultCode 00. base_date=20261118, base_time=1100, nx=60, ny=127. 서울시청 2026-11-18 15:00 KST 예보: 기온 9℃, 강수확률 30%, 강수없음 |

날씨는 서울시청 독립 검증 좌표이며 카카오 경기장 좌표와 연결한 결과가 아니다. Kakao의 실제 경기장 일치 여부는 여전히 미확인이다. 현재 키 형태의 인증·예보 조회는 성공했으나 모든 인코딩 형태, 예보 마지막 시각, 실제 인증 실패 시나리오, 계정별 한도는 미검증이다.

`.env`는 Git ignore와 미추적 상태를 유지한다. 정규화된 샘플은 Git 제외 경로 `.verification/api-check.json`에 저장했다. 실제 키는 문서/로그에 기록하지 않는다.

## 초기 검증 이력

검증일: 2026-11-18 (Asia/Seoul). Issue #1, 브랜치 `feat/project-setup-api-validation`.
이 문서는 실측 증거이며 설계 초안 전체를 확정하는 문서가 아니다.

## 환경과 실행 결과

| 명령/확인 | 실제 결과 |
|---|---|
| `python --version` | Python 3.12.10 |
| `python -m venv .venv` | 성공 |
| `.venv/Scripts/python -m pip install -r requirements.txt` | 성공 |
| `.venv/Scripts/python -m pip install --dry-run langgraph==1.2.10` | 의존성 해석 성공, 설치·런타임 미검증 |
| `.venv/Scripts/python -m pytest tests/test_tool_contracts.py -q` | 개발 중 최초 모듈 미구현으로 수집 실패 → 구현 후 20 통과 → 추가 회귀 테스트 반영 |
| `.venv/Scripts/python -m pytest -q` | 27 통과, 실패 0, 경고 1 (Starlette TestClient의 httpx 지원 폐기 예정) |
| `.venv/Scripts/python -m pip check` | No broken requirements found |
| Uvicorn `backend.main:app --host 127.0.0.1 --port 8765` | 실제 프로세스 실행 후 HTTP 검사, 검사 종료 후 해당 프로세스만 종료 |
| `GET /api/health` | HTTP 200, `{"status":"ok"}` |
| `GET /docs` | HTTP 200, SwaggerUIBundle 포함 HTML |
| `GET /openapi.json` | HTTP 200, `/api/health` 등록 확인 |
| `git check-ignore .env .venv .verification` | 모두 ignore |
| `git ls-files -- .env` | 출력 없음, 추적되지 않음 |

스테이징 검사에서 설계 원문 3~4행의 Markdown 강제 줄바꿈용 공백 2개가 `trailing whitespace`로 표시됐다. 사용자 원문 보존 요구에 따라 유지했다. `PROJECT_PLAN.md`를 제외한 staged diff 공백 검사는 통과했다.

설치된 주요 버전: FastAPI 0.163.2, Uvicorn 0.54.0, Pydantic 2.14.3, requests 2.34.2, python-dotenv 1.2.4, httpx 0.28.1, pytest 9.2.0.
기존 전역 LangGraph는 1.2.11이지만 사용하지 않았으며 설계의 1.2.10을 임의 대체하지 않았다.
명세 PDF 파일이 없어 LangChain 등 명세 고정 버전 대조는 미실행이다.

## 실측 외부 API

실행:
```powershell
$env:PYTHONIOENCODING = 'utf-8'
.venv\Scripts\python scripts/check_external_apis.py --from-date 2026-11-18 --to-date 2026-11-25 --output .verification/api-check.json
```

2026-11-18 12:42 KST 실행, 종료 코드 **1**. KBL은 성공했지만 두 인증 키가 없어 전체 성공을 뜻하는 0을 반환하지 않았다. traceback 없이 JSON 결과를 출력했다.

| Tool/API | HTTP | 서비스 코드 | 실제 결과/필드 |
|---|---|---|---|
| KBL 목록 | 200 | 없음 (배열 직접 반환) | 20261118~20261125, 7개. `gmkey`, `gameDate`, `gameStart`, `tnameH`, `tnameA`, `stadiumnameF`, `seasonGrade`, `seasonCategory` 확인 |
| KBL 상세 | 200 | 없음 (`game/teams/teamrecords` 객체) | 목록 첫 항목 `S49G01N75` → `GET /match/S49G01N75`, 동일 gmkey·시각·팀·경기장 확인 |
| Kakao | 미호출 | 없음 | `MISSING_API_KEY`; 검색어 잠실학생체육관. `.env`가 비어 있고 해당 프로세스에 키가 없음 |
| KMA | 미호출 | 없음 | `MISSING_API_KEY`; 입력 2026-11-18 14:00 KST, 서울시청 좌표 37.5665/126.9780. 인증·응답·예보 범위 실측 미검증 |

KBL 최소 실측 샘플:
```json
{"match_id":"S49G01N75","home_team":"서울 삼성","away_team":"창원 LG","start_at":"2026-11-18T19:00:00+09:00","venue_name":"잠실학생체육관"}
```

추가 실제 KBL 검사:
- 과거 2025-11-18: HTTP 200, 2개.
- 2026-11-18 + `tcodeList=50`: HTTP 200, 1개.
- 2026-11-20: HTTP 200, 빈 배열 → `NO_RESULT`.
- 처음 날짜 인자 없이 `Channel: WEB`, `TeamCode: XX`만 사용: HTTP 500, `resultCode=Fail`, `object=null`, `errorCode=500`. 이때의 500을 API 전체의 상세조회 불가로 결론 내리지 않았다.

## KBL 요청 근거

[KBL 공식 홈페이지](https://www.kbl.or.kr/)의 공개 `/assets/index-1R37IDQA.js`에서 다음 구현 확인 후 실제 호출했다. 번들명은 변경 가능하다.
- `getMatchList`: GET `/match/list`, `fromDate/toDate` YYYYMMDD, `tcodeList=all` 또는 팀 코드.
- `getMatchInfo`: GET `/match/${gmkey}`.
- 헤더: `Channel=WEB`, `TeamCode=XX`.
- 목록은 날짜 범위를 로컬에서도 검사한다. 알 수 없는 시작 시각은 null을 유지한다.

따라서 F3003의 식별자 기반 **외부** 상세조회 구현이 가능하다. 목록 캐시를 상세조회로 가장하지 않는다.

## Mock와 실제 검증 구분

`tests/test_tool_contracts.py`의 외부 응답은 모두 합성 mock이다. 정상 Kakao/KMA 응답, 키 누락 무통신, 타임아웃, HTTP 오류, HTTP 200 내부 실패, 비 JSON, 필드 변경, 빈 결과, KBL ID 전달·불일치, 날짜/타임존·좌표·발표 경계 및 공통 응답 스키마를 검증한다.
이 테스트 통과 자체는 Kakao/KMA 실제 API 성공 증거가 아니다. 별도 13:41 실제 실행에서 인증·격자 `(60,127)`·선택 발표 기준의 대상 예보 존재를 확인했다. 모든 발표 경계 및 마지막 제공 시각은 여전히 미검증이다.

독립 코드 검토에서 upstream의 인증키 반사 응답이 메타데이터로 전파될 수 있는 문제를 발견했다. 원문/URL 인코딩 키 반사 회귀 테스트 2개 실패를 확인한 후 공통 `invoke` 반환 경계에서 모든 문자열과 필드명을 정제하도록 수정했다. 최종 전체 테스트 27개 통과. 실제 인증키 노출 사고는 없었다.

## 미검증·설계 결정 필요

- KBL 목록은 정규리그 외 EASL(`EA`)·D리그(`D1`)를 포함했다. 실제 값을 `season_grade/season_category`에 보존하고 경고한다. **추천 대상 대회 정책은 미확정**이며 다음 Agent 작업 전 결정 필요.
- KBL 사용 허가·호출 한도·구조 안정성 미확인. 공식 웹 앱의 공개 번들은 API 사용 허가 근거가 아니다.
- 카카오 검색 장소와 실제 KBL 경기장 일치 검증 미실행. `verified_kbl_arena=false` 유지.
- KMA 키 일반/인코딩 처리, 발표시간 여유, 예보 가능한 마지막 시각, API 서비스 오류 XML 형태, 계정별 한도 실측 미검증. 현재 XML/비 JSON은 안전한 `UPSTREAM_ERROR`로 처리한다.
- [Kakao 개발 가이드](https://developers.kakao.com/docs/ko/local/dev-guide), [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota), [이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common) 확인. 앱별 무료 대상·결제 설정·잔여 쿼터는 미확인.
- [기상청 포털](https://www.data.go.kr/data/15084084/openapi.do)에서 HTTPS 엔드포인트, 글피 예보 및 출처표시 조건 확인. 계정별 승인량은 미확인.
- 기존 설계 §7의 모호한 KBL 요청 인자를 실측 결과로 구체화할 근거가 생겼다. 원문은 유지하고 §15에 증거와 후속 승인 필요 사항만 기록했다.
- LangGraph/UI/CRUD/RAG/로깅 Agent는 범위 밖으로 미구현. 기존 브랜치는 push되었고 PR #2가 열려 있다. merge는 미실행이다.
