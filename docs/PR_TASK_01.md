# PR 제목

[Feat] 프로젝트 초기 설정 및 외부 API 검증 기반 구축

## Summary

Issue #1의 FastAPI 최소 서버와 외부 API 검증 기반을 구성했습니다. KBL 목록에서 받은 gmkey로 실제 상세조회까지 검증했습니다. 카카오·기상청은 인증 키가 없어 실제 통신 성공은 미검증입니다.

## Changes

- `backend/main.py`: `/api/health`, Swagger.
- `backend/config.py`, `.env.example`, `.gitignore`, `requirements.txt`: 로컬 설정·인증키 제외·개발 의존성.
- `backend/schemas.py`, `backend/tools/`: 네 Tool 입력·출력·공통 오류, 레지스트리, 외부 API 처리.
- `scripts/check_external_apis.py`: 실제 호출 검증, 후보 ID 전달, 안전한 최대 3개 샘플 보고.
- `tests/test_tool_contracts.py`: mock 계약 및 오류·날짜·ID 전달 테스트.
- `docs/PROJECT_PLAN.md`, `docs/VERIFICATION.md`, `docs/TASK_01_IMPLEMENTATION.md`, `README.md`: 설계 보존·진행 상태·실측 증거·실행 방법.
- LangGraph 전체, UI, CRUD, RAG는 포함하지 않았습니다.

## Testing

- `.venv/Scripts/python -m pytest -q`: 27 passed, 1 warning (Starlette TestClient httpx 폐기 예정).
- 독립 검토에서 발견한 upstream 키 반사 가능성을 공통 Tool 반환 경계에서 제거하고 회귀 테스트 2개 RED→GREEN 확인.
- `.venv/Scripts/python -m pip check`: 의존성 충돌 없음.
- 실제 Uvicorn 실행: `/api/health`, `/docs`, `/openapi.json` HTTP 200.
- `.venv/Scripts/python scripts/check_external_apis.py --from-date 2026-11-18 --to-date 2026-11-25 --output .verification/api-check.json`: 종료 1. KBL 목록 HTTP 200, 7개; 첫 gmkey 상세 HTTP 200. Kakao/KMA는 `MISSING_API_KEY`로 미호출.
- 실제 KBL 과거 날짜·팀 필터·빈 결과 확인. Kakao/KMA 실제 정상·인증 오류·예보 범위 검증은 미실행.
- `pip install --dry-run langgraph==1.2.10`: 의존성 해석 성공, 설치·실행 미실행.
- `.env` 미추적 및 ignore 확인. staged diff 공백 검사에서 설계 원문의 Markdown 줄바꿈 공백 2건만 유지했으며 나머지 파일은 통과.

## Related Issue

Refs #1

키 입력 후 실제 카카오·기상청 검증이 남아 있어 자동 종료하지 않습니다.

## Checklist

- [x] 구현한 최소 서버·KBL 조회 정상 동작 확인
- [x] 관련 오프라인 테스트 통과
- [x] API 키 및 민감정보 노출 없음 확인 (`.env` 미추적, 실제 키 미설정)
- [x] 설계 문서의 작업 01 범위와 구현 내용 대조
- [x] 범위 밖 기능 변경 없음
- [ ] 카카오·기상청 실제 인증 및 데이터 확인
- [ ] KBL 추천 대상 대회 범위 확정 및 API 이용 조건 확인
