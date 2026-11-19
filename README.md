# KBL GO

한국프로농구 AI 직관 플래너. Issue #1의 외부 Tool에 Issue #3의 LangGraph Main Agent와 채팅 API를 연결했다.
설계 기준은 [PROJECT_PLAN](docs/PROJECT_PLAN.md)이다. SQLite CRUD·별도 Logging Agent·UI·RAG는 다음 작업 범위다.

## Windows / PowerShell 실행

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# 프로젝트 루트의 .env에 아래 환경변수를 설정한다.
.venv\Scripts\python -m uvicorn backend.main:app --reload
```

- 상태: http://127.0.0.1:8000/api/health
- Swagger: http://127.0.0.1:8000/docs
- 외부 API Tool은 아직 HTTP 라우트로 공개하지 않았다. Python의 `invoke(name, arguments)`로 호출한다.
- `.env`에 `KAKAO_REST_API_KEY`, `KMA_SERVICE_KEY`를 로컬에서 입력한다. 현재 설정된 키로 두 API의 실제 인증 성공을 확인했다. 기상청 키는 일반/URL 인코딩 형태를 처리하며, 두 형태 각각의 별도 실측은 하지 않았다.
- 현재 프로젝트는 `.env`를 직접 사용한다. 기존 파일은 덮어쓰지 않는다. 추가 설정 이름은 `KBL_BASE_URL`, `KBL_TEAM_CODE`, `API_TIMEOUT_SECONDS`이며 기본값은 각각 `https://api.kbl.or.kr`, `XX`, `15`다.
- 자연어 채팅은 `OPENAI_API_KEY`, `OPENAI_BASE_URL`(HTTPS OpenAI 호환 `/v1` 등 API 루트), `OPENAI_MODEL` 설정이 필요하다. 현재 GMS의 `gpt-6-sol`로 실제 JSON 모드 호출을 확인했다. URL 끝에 `/chat/completions`는 붙이지 않는다. 기존 프로세스 환경변수가 로컬 파일보다 우선하며 설정 변경 후 서버를 재시작한다.

## 채팅 실행

Swagger에서 `POST /api/chat`을 열고 다음 요청을 실행한다. 실제 날짜에 경기가 없으면 추천이 없을 수 있다.

```json
{"session_id":"demo-session","message":"2026년 11월 19일 오후 2시 이후 수원에서 서울 SK 경기를 추천해 줘. 강수확률 50% 이하면 좋겠어."}
```

같은 `session_id`로 `팀만 LG로 바꿔 줘. 없으면 다른 팀도 괜찮아.`를 요청하면 날짜·지역·시간·강수 조건을 유지한다. 세션 ID를 생략하면 새 ID를 발급한다. 응답의 `conditions`는 사용자가 요청한 원조건, `active_conditions`는 허용된 재계획 적용 조건이다. 완화한 조건이 다음 발화의 원조건을 덮어쓰지 않는다.

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

## 날씨 필드 정책

- `forecast_at`: 실제 예보 대상 시각. 요청 시각을 KST로 변환한 뒤 분·초를 내린 정시의 응답을 조회한다. 예: 15:45 요청은 15:00 예보를 의미한다.
- `issued_at`: 조회에 사용한 발표 기준시각 (`base_date/base_time`). 대상 시각과 다르다.
- `available=true`: 해당 대상 시각의 기온·강수확률·강수량 중 하나 이상이 제공됨을 뜻한다. 강수 조건 통과를 뜻하지 않는다.
- `precipitation_probability_pct=null`: 강수확률 미확인. 0%로 대체하거나 기온·`available`·강수량 표현만으로 강수확률 조건을 충족시켜서는 안 된다. 다른 제공 데이터는 그대로 사용할 수 있다.
- DAY 2 Agent는 강수확률이 확인된 경우에만 명시된 상한과 비교하며 예보 대상 시각이 실제 경기 정시와 일치하는지도 검사한다.

## 현재 제약

- `MemorySessions`는 프로세스 메모리의 최대 200개 조건·결과 요약을 저장한다. 재시작·eviction 후 복구되지 않으며 여러 worker 간 공유하지 않는다. 저장 책임은 별도 모듈로 분리했다.
- 동시 후속 발화의 갱신 충돌 방지를 위해 전체 실행에 세션 저장소 공통 잠금을 사용한다. 서로 다른 사용자도 대기할 수 있어 동시 처리 개선은 남은 항목이다.
- 단일 날짜 범위는 최대 31일, 명시적 대안 날짜 범위는 최대 3개다. 후보 목록 자체를 앞부분에서 잘라 적합 후보를 버리지 않는다. 넓은 기간은 외부 호출과 지연이 늘어난다.
- 공식 이름·도로명 주소 대조표는 현재 잠실학생체육관·안양 정관장 아레나·수원 KT 소닉붐 아레나 3곳이다. 그 외 구장이나 이름·주소가 모호한 후보는 `unknown`이고 임의 좌표로 날씨를 조회하지 않는다. 출처는 [검증 기록](docs/VERIFICATION.md)에 있다.
- 이벤트는 실행별 메모리 발행 및 응답 반환만 구현했다. 구독자 인터페이스는 있으나 별도 Logging Agent·SQLite 이벤트 저장·조회 API는 미구현이다.

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
