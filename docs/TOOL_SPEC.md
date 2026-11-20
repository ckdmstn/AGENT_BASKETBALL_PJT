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

## 외부 이용 조건 재확인 · 2026-11-20 KST

### KBL 경기 데이터

최종 제출용 체크리스트 26번(NF3007)은 KBL API 외부 사용 허가와 호출 한도에 대해 미확인이다. 27번 PASS의 범위는 제출 자료 완결성이다. [최종 제출용 셀프체크리스트 Excel](셀프체크리스트.xlsx)

| 조사 항목 | 공식 자료에서 확인한 내용 |
| --- | --- |
| 공식 데이터 제공과 공개 API | 일반 사용자가 열람하는 경기 일정·결과 화면을 확인했다. 외부 개발자용 API 상품·이용 신청·명세는 이번 공개 자료에서 확인하지 못했다. [공식 일정 및 결과](https://www.kbl.or.kr/match/schedule) · [KBL 공식 홈페이지](https://www.kbl.or.kr/) |
| 외부 사용·교육·비상업적 사용 | `/match/list`와 `/match/{match_id}`에 대한 외부 프로젝트 사용 허가 또는 교육·비상업 예외는 공개 자료에서 확인하지 못했다. [KBL 웹 이용약관](https://kbl.or.kr/terms/usage) · [구단 공식 웹 이용약관](https://egis.kbl.or.kr/terms/usage) |
| 저장·재사용·재배포·출처 | 일정 데이터와 응답을 저장하거나 결과·로그·캡처로 제출할 때 적용되는 별도 허가 범위와 출처 표기 방식은 확인하지 못했다. 웹 약관 페이지의 일부 색인에는 구단 로고·선수 이미지 등 지식재산권 안내가 있었으며 API 데이터의 별도 이용 조항은 확인되지 않았다. [구단 공식 웹 이용약관](https://egis.kbl.or.kr/terms/usage) |
| 자동화·속도·호출량·인증·차단 | 외부 자동 조회 허용 여부, 초당·일일 한도, 인증 요건 및 접근 제한 대응 절차는 확인하지 못했다. 코드에 API 키 입력이 없고 이전 HTTP 호출에 성공했어도 외부 사용 조건은 공급자의 확인이 필요하다. [KBL 공식 홈페이지](https://www.kbl.or.kr/) · [웹 이용약관](https://kbl.or.kr/terms/usage) |

KBL 공식 사이트의 Contact Us 메뉴와 본사 대표번호 02-2106-3000을 확인했다. 사용자는 해당 채널에서 데이터 이용 담당 부서와 서면 답변을 요청할 수 있다. Task 14에서는 문의를 발송하지 않았으며 해당 웹 API에 추가 요청을 보내지 않았다. [KBL 공식 문의 채널 및 대표번호](https://pegasus.kbl.or.kr/contact/map)

#### 사용자 문의 문안

> 안녕하세요. 교육용 비상업 프로젝트에서 KBL 경기 일정을 조회해 직관 후보를 추천하고자 합니다. 필요한 데이터는 정규리그의 경기 식별자, 시작 일시 및 시간대, 홈·원정 팀과 경기장입니다. 외부 개발자가 사용할 수 있는 공식 API 또는 자료 제공 절차를 안내해 주실 수 있을까요?
>
> 별도 API가 없다면 `api.kbl.or.kr`의 `/match/list` 및 `/match/{match_id}`를 서버에서 저빈도로 자동 호출할 수 있는지 확인 부탁드립니다. 교육용 평가자 시연 및 Git 저장소에 결과의 일부를 문서·로그·캡처로 포함하는 경우까지 고려하고 있습니다. 허용 범위, 신청·인증 방법, 초당·일일 한도와 429·차단 시 처리 방식, 보관·재사용·재배포 조건, 출처 표기 방식 및 테스트용 허용 호출량을 알려 주시면 감사하겠습니다.

#### 대체 후보 검토

| 후보 | 필요한 필드·조건과 확인 결과 |
| --- | --- |
| Sportradar Global Basketball | 공식 커버리지 과거 자료에 한국 KBL이 있으며, 상품 문서에 라이선스된 대회의 경기 목록 제공 절차가 있다. 경기 식별자·시각·대진 제공을 확인할 후보이며 현 시즌 KBL 경기장 필드의 완전성, 계약·보관·공개 범위, 프로젝트 할당량은 계약 전 확인이 필요하다. [커버리지 자료](https://sportradar.com/wp-content/uploads/2022/06/Sportradar_Coverage.pdf) · [경기 API 문서](https://docs.sportradar.com/basketball-media/readme/apis) |
| API-Sports Basketball | 공식 Basketball API 문서가 있으나 이번 공개 자료에서 현 시즌 한국 KBL 경기 목록, 경기장 필드, 교육 프로젝트에 허용되는 데이터 활용 및 한도 조합을 확정하지 못했다. [공식 API 문서](https://api-sports.io/documentation/basketball/v1) |
| 공공데이터포털·KBL 공개 일정 | 이번 탐색에서 요구 필드와 재사용 조건, API 한도를 모두 충족하는 공식 공개 데이터셋을 찾지 못했다. KBL 공개 일정 페이지는 대진·시작·장소 수동 확인에 사용했다. [공공데이터포털](https://www.data.go.kr/) · [KBL 공식 일정](https://www.kbl.or.kr/match/schedule) |

### Kakao Local

- 공식 키워드 장소 검색은 `GET /v2/local/search/keyword.json`과 `KakaoAK` REST 인증을 사용한다. 코드의 요청 방식과 일치한다. 첫 활성화 앱의 무료 일간 키워드 검색 쿼터는 100,000건이다. 월간·일간 한도는 앱 통계에서 확인하며, 다른 앱 또는 초과 사용은 사용 설정과 요금 적용 여부를 확인한다. 이 프로젝트 계정의 실제 잔여량은 확인하지 않았다. [키워드 장소 검색](https://developers.kakao.com/docs/ko/local/dev-guide) · [쿼터](https://developers.kakao.com/docs/ko/getting-started/quota) · [카카오맵 이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common)
- 앱은 검색 후보와 Kakao 장소 상세 링크를 표시한다. 서비스 약관은 데이터의 별도 복사·제공을 제한한다. 공식 문서에서 키워드 검색 결과 전용 출처 표기 예외는 확인하지 못했다. 계획에 주소를 저장하고 문서·캡처를 공개하는 사용 범위는 앱 운영자가 확인해야 한다. 로고를 도입할 경우 디자인 가이드를 따른다. [서비스 약관](https://developers.kakao.com/terms/ko/site-terms) · [운영정책](https://developers.kakao.com/terms/ko/site-policies) · [카카오맵 이용 정책](https://developers.kakao.com/docs/ko/kakaomap/common)

### 기상청 단기예보

- 공공데이터포털에서 개발·운영 활용 신청과 인증키가 필요하다. 포털 표기 개발계정 신청 가능 트래픽은 10,000이며 운영계정은 활용사례를 등록해 증량을 신청할 수 있다. 프로젝트 계정의 승인량은 별도 확인 대상이다. 이용허락은 공공저작물 제1유형으로 출처를 표시한다. 이 문서와 검증 기록에 기상청 및 API 출처를 표기했다. [기상청 단기예보 조회서비스](https://www.data.go.kr/data/15084084/openapi.do)
- 코드상 KST 02·05·08·11·14·17·20·23시 기준 발표 후보에 10분 여유를 둔다. `base_date/base_time`은 발표 기준이며 `fcstDate/fcstTime`은 예보 대상 정시다. 좌표를 격자로 변환하고 대상 정시 행이 존재하는지 확인한다. 코드의 조회 상한은 KST 날짜 기준 +3일이며, 제공처의 상세 서비스 범위가 넓더라도 코드의 상한과 응답 대상을 확인해야 한다. [API 명세·활용가이드](https://www.data.go.kr/data/15084084/openapi.do) · [기상청 발표 안내](https://www.weather.go.kr/w/forecast/guide/fct-ann-guide.do)

GMS는 기존 SSAFY 설정으로 세션 인사에 사용했다. 검증에서는 호출 수를 집계했으며 계정별 잔여량은 조회하지 않았다. [SSAFY GMS](https://gms.ssafy.io/web/)
