# KBL GO

한국프로농구 AI 직관 플래너. 현재는 Issue #1의 FastAPI 최소 구조와 외부 API 검증 기반만 구현했다.
설계 기준은 [PROJECT_PLAN](docs/PROJECT_PLAN.md), 작업 범위는 [CODEX_TASK_01](docs/CODEX_TASK_01.md)이다.

## Windows / PowerShell 실행

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# .env가 없는 경우에만 예시를 복사한다. 기존 .env는 덮어쓰지 않는다.
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.venv\Scripts\python -m uvicorn backend.main:app --reload
```

- 상태: http://127.0.0.1:8000/api/health
- Swagger: http://127.0.0.1:8000/docs
- 외부 API Tool은 아직 HTTP 라우트로 공개하지 않았다. Python의 `invoke(name, arguments)`로 호출한다.
- `.env`에 `KAKAO_REST_API_KEY`, `KMA_SERVICE_KEY`를 로컬에서 입력한다. 기상청 키는 일반/URL 인코딩 키 모두 입력할 수 있으나 실제 인증 성공은 아직 미검증이다.
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
카카오 결과는 장소 후보이며 실제 KBL 경기장으로 확정하지 않는다. KBL 목록은 EASL/D리그 포함 가능성을 경고하며 실제 대회 구분값을 보존한다.
LangGraph State/Node/Edge, 재계획, 세션, DB CRUD, 로깅 Agent, UI는 아직 구현하지 않았다.

## API 출처와 현재 상태 (2026-11-18)

| API | 출처 | 실측/정책 확인 |
|---|---|---|
| KBL | [공식 웹 앱](https://www.kbl.or.kr/) / `api.kbl.or.kr` | 목록·gmkey 상세 HTTP 200. 공개 API 문서/사용 허가/호출 한도 미확인. 웹 앱 구현은 사용 허가를 뜻하지 않는다. |
| Kakao | [로컬 개발 가이드](https://developers.kakao.com/docs/ko/local/dev-guide), [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota), [이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common) | 인증 키 없음, 실측 미실행. 무료 적용/유료 활성화 조건은 앱별 확인 필요. 앱 잔여 한도 미확인. |
| KMA | [공공데이터포털 15084084](https://www.data.go.kr/data/15084084/openapi.do) | 인증 키 없음, 실측 미실행. 포털에서 글피까지 예보·출처표시 조건 확인. 발급 계정별 호출 한도 미확인. |

실제 명령/환경 버전/응답 증거/제약은 [검증 기록](docs/VERIFICATION.md)에 정리했다.
명세 PDF가 현재 저장소에 없어 LangChain 등 명세 고정 버전 대조는 보류했다. LangGraph 1.2.10은 `pip install --dry-run` 의존성 해석만 확인했으며 설치·실행 검증은 다음 작업 범위다.
