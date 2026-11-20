# 작업 01 검증 기록

## Task 09 — 계획 저장 간소화 (2026-11-20 KST)

- PR #16 병합을 포함한 `main`의 `0873e3a` 기준 174개 통과. 변경 후 `.\.venv\Scripts\python.exe -m pytest -q` **178 passed in 7.87s**. `pip check`, `node --check frontend/app.js`, Git 공백 검사도 통과했다.
- 임시 SQLite로 종료 시각·메모 생략 시 `null`, 동일 경기, 시간대가 다른 동일 시작 시각, 기존 구간 내 시작과 종료 경계, 중복 ID 제거·저장 성공, 자기 자신 제외, 메모 PATCH 후 기존 종료 시각 보존 및 삭제를 확인했다.
- `node .verification/browser/plan-save.cjs`에서 1440px·390px 모달의 종료 입력 제거, 추천 카드에서 메모 있는 계획과 없는 계획 저장, 실제 전송된 `end_at: null`, 메모 수정·삭제, 동일 경기와 동일 시작 경고를 확인했다. 추천·로그와 `node .verification/browser/cards-permission.cjs`의 권한·세션 회귀도 통과했다.
- Chromium 테스트는 Mock LLM·Tool 및 임시 SQLite를 사용했다. 실제 외부 API·LLM과 다른 브라우저는 검증하지 않았다. 기존 데이터베이스는 사용하지 않았다. 종료 시각이 없는 경기는 시작점으로만 평가하므로 이후 구간의 중복 여부를 판단할 수 없다.
- 로컬 캡처는 `.verification/browser/plan-save-desktop.png`, `.verification/browser/plan-save-mobile.png`에 있다.

## Task 08 — 추천 채팅 요약과 접기·펼치기 (2026-11-20 KST)

- PR #14가 포함된 `main`의 `8001299`를 기준으로 시작했다. 변경 전 pytest 174개, 변경 후 `.\.venv\Scripts\python.exe -m pytest -q` **174 passed in 7.79s**. `pip check`, `node --check frontend/app.js`, Git 공백 검사 통과.
- 로컬 Chromium `node .verification/browser/cards-smoke.cjs`에서 추천 1건·2건·0건, 제외 후보만 있는 응답, 일부 Tool 오류·권한 확인 필요, 인사말·503 재시도·새 대화·후속 대화를 확인했다. 카드 데이터는 구조화된 추천을 사용하며 긴 근거를 채팅에 반복하지 않는다.
- 1440px와 390px에서 카드 기본 접힘, 상세 열기·닫기와 여러 카드 독립 토글, 제외 후보 72개 그룹의 초기 높이 제한, 긴 이름과 HTML 형태 메모의 안전한 표시를 확인했다. Tab·Enter·Space 및 포커스, 주소·링크·날씨·조건 체크·계획 저장 및 중복 경고, 계획 CRUD와 로그를 확인했다.
- 별도 `node .verification/browser/cards-permission.cjs`로 권한 선택, 입력 초안 보존, 실패 후 재시도, 새로고침과 서버 재시작도 재검증했다. 두 Chromium 테스트는 임시 SQLite와 Mock LLM·Tool을 사용했고, 대량 후보·일부 오류는 합성 응답으로 재현했다. 실제 외부 API·LLM과 다른 브라우저는 확인하지 않았다.
- 두 해상도의 캡처는 `.verification/browser/cards-desktop.png`, `.verification/browser/cards-mobile.png`에 있다.

## Task 07 — 공식 경기장 주소 확대 (2026-11-20 KST)

12월 1~14일 KBL 정규리그 일정에 나타난 10개 홈 구단과 9개 고유 경기장을 대상으로 조사했다. 카카오 검색에서 아래 이름·도로명주소와 유효한 좌표를 확인했고, 각 표의 등록 결과는 해당 조회 범위 기준이다.

| 홈 구단 | KBL API 표기 | 공식 시설명·허용 별칭 | 공식 도로명주소 | 카카오 일치 후보 / 등록 | 공식 출처 |
| --- | --- | --- | --- | --- | --- |
| 창원 LG | 창원체육관 | 창원체육관, 창원스포츠파크 창원체육관 | 경상남도 창원시 성산구 원이대로 450 | 창원스포츠파크 창원체육관 / 신규 | [구단](https://sakers.kbl.or.kr/team/stadium), [창원시설공단 시설](https://www.cwsisul.or.kr/_chsports/_sub01/sub01_02.html), [주소](https://www.cwsisul.or.kr/_chsports/_sub04/sub04_01.html) |
| 서울 SK·서울 삼성 | 잠실학생체육관 | 서울특별시교육청 학생체육관, 잠실학생체육관 | 서울 송파구 올림픽로 25 | 서울특별시교육청 학생체육관 / 유지 | [서울시교육청](https://ssg.sen.go.kr/fus/MI000000000000000366/html/cont0010v.do), [서울 삼성](https://thunders.kbl.or.kr/team/stadium) |
| 안양 정관장 | 안양 정관장 아레나 | 안양 정관장 아레나 | 경기 안양시 동안구 평촌대로 389 | 안양정관장아레나 / 유지 | [정관장](https://www.kgc.co.kr/intro/kgc-introduction/affiliate.do) |
| 수원 KT | 수원 KT 소닉붐 아레나 | 수원 KT 소닉붐 아레나, KT 소닉붐 아레나, 서수원칠보체육관 | 경기 수원시 권선구 서수원로577번길 171 | 수원KT소닉붐아레나 / 유지 | [KBL 미디어 가이드](https://www.kbl.or.kr/upfiles/ebook/2425_media_guidebook.pdf) |
| 고양 소노 | 고양소노아레나 | 고양 소노 아레나, 고양체육관 | 경기 고양시 일산서구 중앙로 1601 | 고양체육관 / 신규 | [구단](https://skygunners.kbl.or.kr/team/stadium), [고양도시관리공사](https://yeyak.gys.or.kr/fmcs/11) |
| 부산 KCC | 부산사직체육관 | 사직종합운동장 실내체육관, 부산 사직실내체육관, 부산사직종합운동장 실내체육관 | 부산 동래구 사직로 55-32 | 부산사직종합운동장 실내체육관 / 신규 | [부산시 주소](https://www.busan.go.kr/sports/main/3?action=view&no=127), [운영기관](https://www.busan.go.kr/stadium/sfcimplexindoors), [KBL 경기 기록](https://www.kbl.or.kr/match/record/S49G01N52/20261103) |
| 대구 한국가스공사 | 대구체육관 | 대구체육관, 대구실내체육관 | 대구 북구 대구체육관로 39 | 대구실내체육관 / 신규 | [대구시 자료](https://www.daegu.go.kr/Images/2014_FIN.pdf), [KBL 미디어 가이드](https://www.kbl.or.kr/upfiles/ebook/2425_media_guidebook.pdf) |
| 울산 현대모비스 | 울산동천체육관 | 울산동천체육관, 동천체육관 | 울산 중구 염포로 85 | 동천체육관 / 신규 | [구단](https://phoebus.kbl.or.kr/team/stadium), [울산시](https://www.ulsan.go.kr/tour/kor/unit/attrctn/view.do?mId=001002008000000000&unqId=38) |
| 원주 DB | 원주DB프로미아레나 | 원주DB프로미아레나, 원주종합체육관 | 강원특별자치도 원주시 서원대로 281 | 원주DB프로미아레나 / 신규 | [구단](https://promy.kbl.or.kr/team/stadium), [원주시설관리공단](https://cms.wfmc.kr/web/lay1/S1T156C179/contents.do) |

- 조사 범위에서 미등록 홈 구단은 없다. 잠실실내체육관은 동일 도로명주소의 다른 시설이며 조사 기간 KBL 홈경기장 표기에 없어서 등록하지 않았다. 부산·울산 보조경기장과 기타 부속 시설을 허용 별칭으로 사용하지 않는다.
- 부산은 API 표기 그대로 검색하면 HTTP 200/`NO_RESULT`였다. 공식 일정에 쓰인 `부산 사직실내체육관`을 검색어로 사용하면 본시설이 조회되며, 검증에는 원래 KBL 이름과 주소 대조를 계속 사용한다.
- 창원은 창원시설공단 운영 시설과 구단 홈코트 안내를 대조했다. 실제 카카오 위치는 위도 35.2327367366309, 경도 128.666283189427이다. [카카오 장소](http://place.map.kakao.com/17808355)
- 실제 KBL 목록·상세와 카카오는 모두 HTTP 200. 2026-12-03 19:00 `S49G01N79` 창원 LG–안양 정관장의 시작 시각·팀·장소가 일치했다. 이 도구 응답과 Mock LLM을 조합했을 때 주소·창원 지역·LG·정규리그·날짜가 각각 `met`이고 날씨 조건 없는 요청에서 최종 추천됐다. 서울 지역 `unmet`, 검색 실패 시 지역 `unknown`은 오프라인 회귀 테스트에서 확인했다.
- 경기 시각에 검증 좌표를 전달한 기상청 Tool은 범위 밖 `UNSUPPORTED_DATE`를 반환했으며 외부 HTTP 요청은 발생하지 않았다. 날씨 조건을 요청하면 해당 조건은 `unknown`이며 날씨가 확인된 추천으로 처리되지 않는다.
- `.verification/arena_probe.py`와 `.verification/changwon_graph.py`는 로컬 실제 Tool 검증에 사용했다. 전체 pytest **174 passed in 5.44s**(기존 151개, 신규 23개), `pip check`, `node --check frontend/app.js`, `git diff --check` 통과. Mock Chromium 스모크에서 개선된 사유의 추천·제외 카드 표시, 계획 CRUD, 로그 UI를 재검증했다. 실제 LLM과 경기 시각 예보 성공은 이번 검증에서 확인하지 않았다.

## PR #12 리뷰 보완 — 권한 전용 명령 (2026-11-20 KST)

- 기존 세션의 독립 허용·철회 문장과 첫 대화의 정확한 버튼 문장을 Analyze LLM 호출 전에 분류한다. 권한 판정은 기존 `verify_permissions()`가 수행한다. 기존 조건, 철회 선반영·세션 저장, 일반 자연어 분석은 유지한다. Analyze LLM을 호출하지 않은 턴은 분석 단계의 시작·완료 이벤트만 남긴다.
- 첫 대화의 버튼 명령은 권한을 처리한 뒤 날짜를 안내하며 경기 조회를 실행하지 않는다. 날짜가 있는 권한 전용 요청의 계획·응답 단계는 기존과 같이 LLM을 사용할 수 있다.
- Analyze 실패가 설정된 모의 모델에서 권한 명령은 분석을 건너뛰고 일반 후속 발화는 기존 분석을 실행했다. 새 버튼 문장 2건, 철회 뒤 재계획 차단, 모호한 허용 차단을 검증했다.
- `.\.venv\Scripts\python.exe -m pytest -q` **151 passed in 6.82s**, `pip check`·JavaScript 구문·Git 공백 검사 통과. Chromium의 권한 버튼과 기존 전체 스모크도 통과했다. 브라우저에는 임시 SQLite와 Mock LLM·Tool을 사용했으며 실제 외부 API·LLM은 재호출하지 않았다.

## Task 06 — 딥 네이비 및 팀 완화 권한 (2026-11-20 KST)

- PR #10 병합을 포함한 `main`의 `ea32c1e`에서 시작했다. 변경 전 pytest 147개, 변경 후 `.\.venv\Scripts\python.exe -m pytest -q` **149 passed in 4.71s**. 기존 SQLite 철회 테스트에도 응답 상태 확인을 추가했다. `pip check`, `node --check frontend/app.js`, Git 공백 검사 통과.
- Chromium 권한 스모크 `node .verification/browser/permission.cjs`에서는 초기 미허용, 모호한 표현 확인 요청, 독립 허용·철회 메시지, 대기 중 잠금과 초안 보존, 직접 입력, 503 후 상태 미확인·재시도, 새 대화 분리, 새로고침·동일 DB 서버 재시작 후 상태 확인을 검증했다. 허용됐지만 실제 완화하지 않은 실행과 팀 조건을 해제한 실행을 구분했다.
- 1440px와 390px에서 빈 결과·추천 카드 두 건·계획 모달·로그 타임라인을 확인했다. 키보드 Tab과 Enter로 권한 버튼을 선택·실행했고 포커스 표시를 확인했다. 흰색과 딥 네이비 버튼은 13.75:1, 연한 채팅 배경과 본문은 13.26:1, 밝은 전체 배경과 강조 보조 텍스트는 5.82:1이다. 전체 접근성 감사는 수행하지 않았다.
- 기존 `node .verification/browser/smoke.cjs`도 통과했다. 두 브라우저 검증 모두 임시 SQLite와 Mock LLM 및 Tool을 사용했으며 실제 외부 API와 LLM은 재호출하지 않았다. 최종 화면은 `.verification/deep-navy-WnCcDN/desktop.png`와 `mobile.png`에 보관했다.

## Task 05 — 실제 통합 검증 (2026-11-20 KST)

기준은 PR #8 병합 커밋 `136c7a1`의 `origin/main`이다. Python 3.12.10을 사용했다. Kakao·KMA·LLM에 필요한 환경변수의 설정 여부를 확인했고 값은 공개하지 않았다. 로컬 FastAPI와 실제 LLM·Tool을 사용한 Chromium 실행에 별도 SQLite 파일을 연결했다.

| 실제 검증 | HTTP / 반환 코드 | 확인한 결과 |
| --- | --- | --- |
| KBL 11월 20~23일과 20일 단일 조회 | 200 / `NO_RESULT` | 경기 없음이 안전하게 반환됐다. |
| KBL 11월 18~25일 | 200 / 성공 | 7개 일정에서 정규리그 `R/1`, EASL `EA/1`, D리그 `D1/2`를 확인했다. |
| KBL 상세 `S49G01N76` | 200 / 성공 | 11월 19일 19:00 KST, 안양 정관장 vs 부산 KCC, 안양 정관장 아레나가 목록과 일치했다. |
| 카카오 장소 검색 및 검증 | 200 / 성공 | 안양정관장아레나, 경기 안양시 동안구 평촌대로 389. 공식 주소 대조 통과, HTTP(S) 장소 링크 및 유효한 좌표 확인. |
| 해당 경기 시각의 기상청 예보 | 외부 HTTP 요청 없음 / `UNSUPPORTED_DATE` | 이미 지난 경기 시각이라 Tool이 호출 전에 거부했다. LangGraph 강수 조건은 `unknown`으로 유지됐다. |
| 같은 경기장 좌표의 별도 기상청 예보 | 200 / 서비스 `00` | 11월 20일 11:00 발표, 13:00 대상. 기온 2 °C, 강수확률 0%, 강수없음. 해당 경기 시각의 예보로 사용하지 않았다. |
| 실제 LLM | 10회 HTTP 200 | 기존 설정의 모델로 구조화 응답을 수신했다. |

### 실제 Chromium·FastAPI·SQLite

| 브라우저 요청 | 결과 |
| --- | --- |
| 안양, 11월 19일 18시 이후 부산 KCC | `/api/chat` 200, 8.87초. 실제 일정·상세·장소 Tool 성공. `S49G01N76` 카드의 조건 충족과 다른 후보의 API 제외 판정을 확인했다. 이 턴에는 날씨 조건을 지정하지 않았다. |
| 같은 세션에서 창원 LG로 변경, 강수확률 100% 이하, 다른 팀 명시 허용 | 200, 16.22초. 날짜·시각·지역 유지. 선호 팀만 1회 완화됐고 일정 캐시를 재사용했다. 추천 0건, 제외 2건, 날씨 `unknown`, 수원 경기 지역 `unmet`. UI에서 해제된 선호 팀을 확인했다. |
| 로그 삭제 및 서버 재시작 후 같은 세션에서 다른 팀 허용 철회 | 200, 8.40초. 날짜·지역·선호 팀·강수 상한 복원, 팀 완화 권한 해제, 재계획 0회, 추천 0건. |

- 웹 루트와 `/api/health`, `/docs`, `/openapi.json`은 200. 실제 추천 카드에서 계획 저장·목록·상세·수정·삭제를 수행했고 중복 계획의 저장 성공 및 경고를 확인했다.
- 두 실제 실행의 로그 상세에서 서로 다른 실행 ID, 연속 이벤트 순번, 고정 `reason_code`, 재계획 설명을 확인했다. 저장 payload에 자유 텍스트 판단 이유와 Tool 인자가 없었다. 시연 로그 삭제 직후 상세는 404였고 계획 1건이 남았다. 이후 서버 재시작·권한 철회 요청 뒤 DB에 계획 1건, 세션 1건, 새 이벤트 16건, 팀 완화 권한 0이 저장됐다. 설정된 인증값과 그 인코딩 표현을 최종 DB에서 찾지 못했다.
- 실제 두 번째 요청 후 제외 후보 요약을 여는 자동화에서 동일 문구가 포함된 경고까지 선택하는 문제가 있었다. API의 제외 판정과 원조건·활성조건 UI까지 확인한 뒤, 실제 요청을 반복하지 않고 같은 DB에서 로그와 재시작 검증을 재개했다. 해당 턴의 제외 카드 확장 검증은 Mock 스모크에서 확인했으며 실제 턴에서는 미확인이다. 제품 코드 변경은 없었다.

### 실행 명령과 남은 한계

| 명령 | 모드 / 결과 |
| --- | --- |
| `.\.venv\Scripts\python.exe .verification/live_probe.py` | 실제 KBL·카카오·기상청 |
| `node .verification/browser/live.cjs` 및 `node .verification/browser/live.cjs .verification/live-3nwUC4` | 실제 Chromium·LLM·Tool·임시 SQLite. 첫 실행은 브라우저 선택자 오류로 중단했고 동일 DB에서 이어서 검증했다. |
| `node .verification/browser/smoke.cjs` | 별도 Mock LLM·Tool로 스모크 통과. 강수확률 null 보존, 예보 대상 시각 불일치, 빈 결과, 503 재시도, 모바일·HTML 입력 방어 포함. |
| `.\.venv\Scripts\python.exe -m pytest -q` | 오프라인 **147 passed in 7.45s** |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found |
| `node --check frontend/app.js`, `git diff --check` | 통과 |

검증용 스크립트와 화면은 로컬 Git 제외 경로에 보관했다. 실제 화면은 `.verification/live-3nwUC4/real-recommendation.png`와 `real-timeline.png`다. 실제 경기 시각의 예보 성공·실제 예보의 강수확률 누락·실제 LLM 실패·날짜 완화 권한의 실제 호출은 이번에 관측하지 못했다. 시연 순서와 Mock 대체 절차는 README에 있다.

## PR #8 최종 리뷰 — 날씨 표시 (2026-11-20)

- 예보 미제공 시 강수확률·기온·강수량을 숨긴다. 제공된 예보는 대상 시각과 함께 표시하며, 서버가 강수 조건을 `unknown`으로 판정하면 해당 경기 시각의 조건을 확인하지 못했다고 별도로 안내한다. 강수확률 `null`과 강수량 `0 mm`를 구분한다.
- Chromium 스모크에서 정상 예보 및 조건 충족, 값이 남아 있는 미제공 예보, 강수확률 `null`, 예보 대상 시각 불일치, 강수량 0과 누락을 확인했다. 기존 채팅·세션, 추천·제외 카드, 계획 CRUD·중복 경고, 로그, HTML 형태 메모 처리도 다시 통과했다.
- 로컬 `node .verification/browser/smoke.cjs`는 임시 SQLite와 모의 LLM·Tool을 사용했다. 일부 날씨 경계값은 브라우저에서 API 응답을 바꿔 재현했다. 실제 외부 API·LLM과 Chromium 외 브라우저는 이번 리뷰에서 확인하지 않았다.
- `.\.venv\Scripts\python.exe -m pytest -q` **147 passed in 5.31s**, `.\.venv\Scripts\python.exe -m pip check` **No broken requirements found**, `node --check frontend/app.js` 및 `git diff --check` 통과.

## Task 04 — Issue #7 웹 UI (2026-11-20)

| 검증 | 결과 |
| --- | --- |
| 변경 전 `.\.venv\Scripts\python.exe -m pytest -q` | 143 passed |
| 변경 후 동일 명령 | **147 passed in 7.21s**. 기존 143개와 신규 정적 경로 테스트 4개 |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found |
| `node --check frontend/app.js` 및 `git diff --check` | 통과 |
| `node .verification/browser/smoke.cjs` | Playwright 1.52 및 Chromium Headless Shell에서 통과 |

- 브라우저는 로컬 Uvicorn의 실제 FastAPI 경로와 임시 SQLite를 사용했다. Agent의 LLM과 외부 Tool 응답만 모의 처리했다. 실제 LLM과 KBL·카카오·기상청 API는 재호출하지 않았다.
- Enter 전송과 Shift+Enter 줄바꿈, 로딩 중 전송 잠금, 503 안내 및 재시도, 세션 ID 새로고침 유지와 새 대화 분리를 확인했다.
- 추천·제외 카드와 충족·불충족·미확인 상태, 강수확률 null, 원조건과 활성조건, 재계획에서 해제된 선호 팀 표시를 확인했다.
- 계획 저장·목록·상세·수정·삭제, 수정 시 메모 필드만 전송, 중복 저장과 경고, HTML 형태 메모의 텍스트 렌더링을 확인했다. 세션별 로그 상세의 캐시 재사용·재계획 설명과 로그 삭제 뒤 계획·다른 세션 로그의 보존을 확인했다.
- 데스크톱 1440px 및 모바일 390px 레이아웃을 브라우저에서 확인했다. 로컬 화면 캡처는 Git 제외 경로 `.verification/browser/desktop.png` 및 `.verification/browser/mobile.png`에 있다. Edge 자동 실행이 종료되어 브라우저 검증은 Chromium에서 수행했다. 기타 브라우저 및 실제 모바일 기기는 별도로 확인하지 않았다.

시연은 웹 UI에서 날짜와 팀을 입력한 뒤 추천 근거를 확인하고, 같은 경기를 종료 시각을 지정해 두 번 저장해 중복 경고를 확인하는 순서로 진행한다. 이후 저장한 계획의 메모를 수정하고 실행 로그를 열어 처리 과정과 재계획 내역을 확인할 수 있다. 실제 경기 조회 결과는 입력 시점과 외부 서비스 응답에 따라 달라진다.

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
