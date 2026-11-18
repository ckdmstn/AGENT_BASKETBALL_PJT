# 작업 01 검증 기록

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
이 테스트 통과는 Kakao/KMA 실제 API 성공 증거가 아니다. KMA 서울 격자 `(60,127)` 및 발표 10분 여유는 단위 테스트만 통과했다. 실제 인증·운영 시각·누락 없는 페이지·대상 예보 존재를 키 발급 후 검사해야 한다.

독립 코드 검토에서 upstream의 인증키 반사 응답이 메타데이터로 전파될 수 있는 문제를 발견했다. 원문/URL 인코딩 키 반사 회귀 테스트 2개 실패를 확인한 후 공통 `invoke` 반환 경계에서 모든 문자열과 필드명을 정제하도록 수정했다. 최종 전체 테스트 27개 통과. 실제 인증키 노출 사고는 없었다.

## 미검증·설계 결정 필요

- KBL 목록은 정규리그 외 EASL(`EA`)·D리그(`D1`)를 포함했다. 실제 값을 `season_grade/season_category`에 보존하고 경고한다. **추천 대상 대회 정책은 미확정**이며 다음 Agent 작업 전 결정 필요.
- KBL 사용 허가·호출 한도·구조 안정성 미확인. 공식 웹 앱의 공개 번들은 API 사용 허가 근거가 아니다.
- 카카오 검색 장소와 실제 KBL 경기장 일치 검증 미실행. `verified_kbl_arena=false` 유지.
- KMA 키 일반/인코딩 처리, 발표시간 여유, 예보 가능한 마지막 시각, API 서비스 오류 XML 형태, 계정별 한도 실측 미검증. 현재 XML/비 JSON은 안전한 `UPSTREAM_ERROR`로 처리한다.
- [Kakao 개발 가이드](https://developers.kakao.com/docs/ko/local/dev-guide), [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota), [이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common) 확인. 앱별 무료 대상·결제 설정·잔여 쿼터는 미확인.
- [기상청 포털](https://www.data.go.kr/data/15084084/openapi.do)에서 HTTPS 엔드포인트, 글피 예보 및 출처표시 조건 확인. 계정별 승인량은 미확인.
- 기존 설계 §7의 모호한 KBL 요청 인자를 실측 결과로 구체화할 근거가 생겼다. 원문은 유지하고 §15에 증거와 후속 승인 필요 사항만 기록했다.
- LangGraph/UI/CRUD/RAG/로깅 Agent는 범위 밖으로 미구현. PR 생성·push·merge는 미실행.
