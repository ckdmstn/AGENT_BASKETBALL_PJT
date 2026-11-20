# Tool 정의

`tool_specs()`는 Tool 이름·설명·구분과 JSON Schema를 반환한다. `invoke(name, arguments, settings)`가 입력을 검증하고 등록 핸들러를 실행해 출력도 검증한다. 현재 등록된 네 Tool은 외부 API를 감싼다. 계획·로그용 로컬 API는 FastAPI 라우트에서 제공한다. [레지스트리](../backend/tools/registry.py) · [스키마](../backend/schemas.py)

| Tool | 입력 | 성공 데이터 | 출처 및 범위 |
| --- | --- | --- | --- |
| `search_kbl_games` | `from_date, to_date` 각 기본 KST 오늘, 선택 `team_code` | `GameCandidate[]` 경기 ID, 팀, 시작, 장소명, 대회 구분 | KBL `/match/list`. 요청 범위 밖 결과는 제외하고 경고 |
| `get_kbl_game_detail` | 필수 `match_id`, 선택 `date` | `GameDetail` 경기 ID, 시각, 홈·원정, 장소 | KBL `/match/{match_id}`. 다른 ID 응답은 실패 |
| `search_arena` | 필수 `venue_name`, 선택 `region_hint` | `Arena[]` 후보 이름, 주소, 좌표, 상세 링크 | Kakao 키워드 장소 검색. Agent에서 실제 경기장 검증 |
| `get_weather` | 시간대가 있는 `date_time`, `lat`, `lon` | `Weather` 대상·발표 시각, 기온, 강수확률·강수량, 제공 여부 | 기상청 `getVilageFcst`. 경기 시각과 시간 단위로 대조 |

성공은 `{ok: true, data, error: null, meta}`, 실패는 `{ok: false, data: null, error: {code, message}, meta}`다. `meta`에는 출처·실제 인자·HTTP/서비스 상태·필드·경고가 들어간다. 입력 오류, 키 누락, 결과 없음, 필드 누락, 조회 범위 밖 날짜, 상류 장애, 타임아웃, 내부 오류는 안전한 코드·문구로 구분한다. KBL 웹 엔드포인트는 별도 API 키를 사용하지 않는다.

새 Tool은 Pydantic 입출력 모델, 정규화 핸들러, 레지스트리 등록, 정상·오류 계약 테스트를 추가한다. Agent가 사용할 때는 계획의 허용 Tool과 의존성도 수정한다.

| 제공자 | 확인한 이용 조건 |
| --- | --- |
| KBL | 공식 웹 앱의 경기 자료를 사용한다. 웹 이용약관을 찾았으나 해당 엔드포인트의 별도 API 사용 허가와 호출 한도는 확인하지 못했다. [KBL](https://www.kbl.or.kr/) · [웹 이용약관](https://egis.kbl.or.kr/terms/usage) |
| Kakao | 키워드 장소 검색 일간 무료 100,000건. 첫 활성화 앱에 무료 쿼터가 적용되며 다른 앱이나 초과 이용은 앱 설정·과금 정책을 확인한다. [개발 가이드](https://developers.kakao.com/docs/ko/local/dev-guide) · [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota) · [이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common) |
| 기상청 | 무료, 공공저작물 제1유형 출처표시. 포털에 개발계정 트래픽 10,000으로 표시되며 운영계정은 활용사례 등록 후 증량을 신청할 수 있다. [공공데이터포털](https://www.data.go.kr/data/15084084/openapi.do) |
