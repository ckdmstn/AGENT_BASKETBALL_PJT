# Codex 작업 지시서 01 — 설계 문서 저장, 프로젝트 초기화 및 외부 API 검증 준비

## 작업 목표
KBL GO 3회차 프로젝트의 첫 작업이다. **Agent 전체 구현은 아직 하지 말고**, 확정 전 설계 초안을 프로젝트에 기록하고 FastAPI의 최소 골격 및 3개 외부 API 검증 가능한 스크립트/Tool 계약을 준비한다.

**확정된 설계 문서를 프로젝트의 `docs/PROJECT_PLAN.md`에 저장하고, 이후 구현에서는 이 문서를 기준으로 진행해 주세요.** 현재 제공 문서의 상태가 '초안 v0.1 / 외부 API 실측 검증 전'이므로, 미확인 항목은 실제 검증 후 사용자에게 보고하고 승인된 내용만 '확정'으로 수정한다.

## 생성/수정할 파일
`docs/PROJECT_PLAN.md`(내가 전달하는 원문을 그대로 저장), `.gitignore`, `.env.example`, `requirements.txt`, `backend/main.py`, `backend/config.py`, `backend/schemas.py`, `backend/tools/registry.py`, `backend/tools/kbl.py`, `backend/tools/kakao.py`, `backend/tools/weather.py`, `scripts/check_external_apis.py`, `tests/test_tool_contracts.py`, `README.md`(DAY 1 실행 방법).

## 구현 범위
1. VS Code/Windows 가상환경에서 Python 3.10+ 및 명세 필수 라이브러리 설치 가능 여부 확인. 설치 실패 시 이유와 실제 버전을 보고하고 임의의 버전 변경 금지.
2. `GET /api/health` 및 `/docs`가 열리는 최소 FastAPI 앱만 구현.
3. `.env.example`에 `OPENAI_API_KEY`(또는 실제 교육 환경 GMS 키), `KAKAO_REST_API_KEY`, `KMA_SERVICE_KEY`, KBL 사용 설정 등 **키 이름만** 기재. `.env`/DB/캐시/venv는 Git에서 무시.
4. KBL(`match/list`), Kakao keyword, KMA `getVilageFcst` 각각 실제 통신을 확인하는 검증 스크립트를 작성하되, 키가 없으면 명확한 `MISSING_API_KEY`로 종료하고 비밀을 출력하지 않는다. **KBL 매치 ID에서 개별 상세 조회가 가능한지 우선 조사**. 원본 응답에는 개인정보/키 제거, 저장도 샘플만.
5. 4개 Tool의 이름, 설명, 입력 스키마 및 공통 `ok/data/error/meta` 형식을 정의. 외부 응답 구조가 확인되기 전에는 임의 필드를 채우지 않는다. 성공·실패 mock 테스트는 실제 API 성공 테스트와 분리하여 표시.
6. 실제 라이브 호출 결과로 각 API의 HTTP 코드, 서비스 결과 코드, 필수 값 유무, 실제 조회한 날짜/범위, 응답 구조, 제한/약관 확인 근거를 기록.
7. **하지 말 것:** LangGraph 전체 개발, UI, CRUD, 기존 RAG 복사, 임의 날짜 경기·날씨 생성, 예제 API를 성공한 것처럼 보고.

## 연결 요구사항
F3001~F3004 사전 준비, F3017 앱 골격, NF3001/NF3002/NF3003/NF3006/NF3007. F3005~F3016, F3018~F3019는 다음 작업으로 넘긴다.

## 테스트 방법
- PowerShell에서 의존성 설치 및 `uvicorn backend.main:app --reload` 실행, `/docs`와 `/api/health` 확인.
- `python scripts/check_external_apis.py` 실행: 세 외부 API의 결과와 구체적 미확인 필드를 구분하여 보고. 키 없이 실행해도 traceback/키 출력 없음.
- `pytest tests/test_tool_contracts.py`로 Tool 스키마 및 mock 성공/실패 형태 점검.
- `git status`로 `.env`가 추적되지 않는지 확인.

## 완료 기준
- 설계 문서가 `docs/PROJECT_PLAN.md`에 존재하고 요구사항 표가 손실되지 않음.
- 골격 서버 실행·Swagger 확인, 검증 스크립트 및 Tool 인터페이스 테스트 준비.
- 실측되지 않은 부분은 '미검증'으로 기록, 키와 오류 내부 정보 노출 없음.
- 실측 결과가 상세조회 불가 등 설계와 충돌하면 **우선 보고**, 임의로 필수 요구사항을 축소하지 않음.

## 결과 보고 형식
1. 생성/수정 파일 목록
2. 실행 명령과 결과 (성공/실패 각각)
3. 외부 API별 HTTP/서비스 상태, 중요 응답 필드, 오류/미검증 항목
4. KBL 식별자→상세정보 Tool 구현 가능 여부 (증거)
5. 테스트 실행 수 / 통과 / 실패
6. 설계 문서에서 변경이 필요한 위치와 이유
7. 현재 미완료 항목 / 다음 구현 단계 제안

## GitHub 연동
- Related Issue: #1
- Branch: feat/project-setup-api-validation
- PR Title: [Feat] 프로젝트 초기 설정 및 외부 API 검증 기반 구축
구현 완료 후 변경 파일, 테스트 결과,
미검증 항목을 포함한 PR 본문 초안을
작성해 주세요.