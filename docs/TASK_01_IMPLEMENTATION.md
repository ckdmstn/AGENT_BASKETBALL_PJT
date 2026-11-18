# 작업 01 구현 계획

기준: `PROJECT_PLAN.md`, `CODEX_TASK_01.md`, GitHub Issue #1.
기존 설계 원문은 유지하고 진행 현황만 덧붙인다. 사용자가 지정한 현재 작업 폴더와 기능 브랜치에서 직접 진행한다.

## 범위와 구조
- `backend/main.py`: health와 Swagger만 제공.
- `backend/config.py`: 프로젝트 루트 .env 로딩, 키 비노출 설정.
- `backend/schemas.py`: 네 Tool 입력/출력, 판별 가능한 성공/실패 계약.
- `backend/tools/registry.py`: Tool 설명·외부 구분·입출력 JSON Schema·실행과 입력 오류 처리.
- `backend/tools/{kbl,kakao,weather}.py`: API 호출, 정규화, 명시적 실패. 공통 통신은 `http.py`에 둔다.
- `scripts/check_external_apis.py`: 실제 호출, 비밀 없는 메타데이터와 최소 필드 증거. 미검증 상세 경로는 추측하지 않는다.
- `tests/test_tool_contracts.py`: 네트워크 격리 mock 계약·오류·날짜 검증 및 health/docs 테스트.

## 실행 순서
- [x] 계약 및 오류 시나리오 테스트 작성 → 실패 확인.
- [x] 최소 앱·스키마·레지스트리·검증용 Tool 구현 → 테스트 통과 확인.
- [x] 실제 외부 API 및 로컬 HTTP 서버 검증, 결과 문서화. Kakao/KMA는 키 누락으로 미실행 기록.
- [x] 설계 진행 현황·README·PR 초안 갱신, 비밀 유출 및 diff 검사.

## 최종 검토
독립 리뷰에서 외부 서비스가 키를 응답에 되돌려 줄 때 메타데이터에 남는 문제를 발견했다. 회귀 테스트 실패 확인 후 `invoke` 반환 경계에서 원문/디코딩/URL 인코딩 키를 재귀 제거하도록 수정했다. 구현 범위 변경은 없다.

## 검증 초점
키 누락 시 무통신, HTTP 200 내부 서비스 실패, 비 JSON/잘못된 구조, 빈 결과, 타임아웃, 범위 밖 날짜, Asia/Seoul 시간, 키가 담긴 예외·URL의 출력 금지.

LangGraph 1.2.10은 설치 가능성만 별도 검사하며 이번 작업의 실행 의존성에는 추가하지 않는다. 명세 PDF는 현재 폴더에 없어 나머지 명세 고정 버전은 대조 불가하다. 임의 버전 대체 없이 그 사실을 기록한다.
