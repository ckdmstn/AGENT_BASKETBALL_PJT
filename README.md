# KBL GO

한국프로농구 AI 직관 플래너. 현재는 Issue #1의 FastAPI 최소 구조와 외부 API 검증 기반만 구현했다.
설계 기준은 [PROJECT_PLAN](docs/PROJECT_PLAN.md)이며, 작업 범위는 Issue #1의 최소 서버·외부 API 검증이다.

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
- `OPENAI_*`는 다음 작업용 이름만 예약했으며 현재 호출하지 않는다.

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
LangGraph State/Node/Edge, 재계획, 세션, DB CRUD, 로깅 Agent, UI는 아직 구현하지 않았다.

## 날씨 필드 정책

- `forecast_at`: 실제 예보 대상 시각. 요청 시각을 KST로 변환한 뒤 분·초를 내린 정시의 응답을 조회한다. 예: 15:45 요청은 15:00 예보를 의미한다.
- `issued_at`: 조회에 사용한 발표 기준시각 (`base_date/base_time`). 대상 시각과 다르다.
- `available=true`: 해당 대상 시각의 기온·강수확률·강수량 중 하나 이상이 제공됨을 뜻한다. 강수 조건 통과를 뜻하지 않는다.
- `precipitation_probability_pct=null`: 강수확률 미확인. 0%로 대체하거나 기온·`available`·강수량 표현만으로 강수확률 조건을 충족시켜서는 안 된다. 다른 제공 데이터는 그대로 사용할 수 있다.
- 강수확률이 숫자로 있어도 사용자 임계값과 비교하는 조건 판정은 DAY 2 Agent 범위다. 이번 작업에는 판정 로직이 없다.

## 문서 관리

공유 설계 `docs/PROJECT_PLAN.md`와 검증 증거 `docs/VERIFICATION.md`는 Git에서 관리한다. 내부 작업 전달서·구현 체크리스트·PR 초안은 로컬에 유지하고 Git 추적에서 제외한다. 다음 작업도 기존 로컬 파일을 재사용하며 번호를 붙인 새 교환 문서를 추가하지 않는다. Git 추적 제외는 과거 커밋 이력을 삭제하는 작업은 아니다.

## API 출처와 현재 상태 (2026-11-18)

| API | 출처 | 실측/정책 확인 |
|---|---|---|
| KBL | [공식 웹 앱](https://www.kbl.or.kr/) / `api.kbl.or.kr` | 목록·gmkey 상세 HTTP 200. 공개 API 문서/사용 허가/호출 한도 미확인. 웹 앱 구현은 사용 허가를 뜻하지 않는다. |
| Kakao | [로컬 개발 가이드](https://developers.kakao.com/docs/ko/local/dev-guide), [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota), [이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common) | 실제 HTTP 200, 장소 후보의 주소·좌표·링크 확인. 무료 적용/유료 활성화 조건은 앱별 확인 필요. 앱 잔여 한도 미확인. |
| KMA | [공공데이터포털 15084084](https://www.data.go.kr/data/15084084/openapi.do) | 실제 HTTP 200 / 서비스 00, 대상 시각의 기온·강수확률·강수량 확인. 예보 마지막 시각·발급 계정별 한도 미확인. |

실제 명령/환경 버전/응답 증거/제약은 [검증 기록](docs/VERIFICATION.md)에 정리했다.
명세 PDF가 현재 저장소에 없어 LangChain 등 명세 고정 버전 대조는 보류했다. LangGraph 1.2.10은 `pip install --dry-run` 의존성 해석만 확인했으며 설치·실행 검증은 다음 작업 범위다.
