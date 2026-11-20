# FastAPI 계약

실행 중 `/docs`에서 Swagger, `/openapi.json`에서 전체 모델을 확인한다. [라우트](../backend/main.py) · [채팅 모델](../backend/agent/state.py) · [계획 모델](../backend/plans.py) · [로그 모델](../backend/logs.py)

| 메서드와 경로 | 요청 | 성공 | 오류 |
| --- | --- | --- | --- |
| GET /api/health | 없음 | 200 HealthResponse | — |
| POST /api/chat | ChatRequest | 200 ChatResponse | 422, 503 |
| POST /api/plans | PlanCreate | 201 PlanSaved | 409, 422, 503 |
| GET /api/plans | 없음 | 200 Plan[] | 503 |
| GET /api/plans/{plan_id} | 정수 ID | 200 Plan | 404, 422, 503 |
| PATCH /api/plans/{plan_id} | PlanPatch | 200 PlanSaved | 404, 409, 422, 503 |
| DELETE /api/plans/{plan_id} | 정수 ID | 204 | 404, 422, 503 |
| GET /api/logs | 없음 | 200 LogSummary[] | 503 |
| GET /api/logs/{session_id} | 세션 ID | 200 SessionLog | 404, 503 |
| DELETE /api/logs/{session_id} | 세션 ID | 204 | 404, 503 |

채팅 요청 예시

```json
{"message":"2026-12-03 창원에서 오후 6시 이후 정규리그 경기 추천해 줘","allow_other_teams":false}
```

`session_id`는 후속 대화에서 전달한다. 응답에는 `session_id, run_id, conditions, active_conditions, team_permission, answer, recommendations, excluded, replan_count, relaxation_history, events, errors, warnings, elapsed_ms`가 있다. 일부 조회 실패도 구조화된 `errors`로 반환한다.

계획 생성 요청 예시

```json
{"match_id":"demo-1","home_team":"창원 LG","away_team":"안양 정관장","venue_name":"창원체육관","start_at":"2026-12-03T19:00:00+09:00","end_at":null,"note":" 경기 시작 전 도착"}
```

`Plan`은 저장한 필드에 `id, game_date, created_at, updated_at`을 추가한다. 생성·수정 응답은 `{plan, overlapping_plan_ids, overlap_warnings}`다. 시각은 시간대가 있는 ISO 8601을 받고 KST로 정규화한다. PATCH는 바꿀 필드만 보낸다. 중복 경기 ID는 409, 시간 겹침은 저장과 함께 안내한다.

로그 목록은 세션별 `session_id, run_count, event_count, last_event_at`을 반환한다. 상세는 `{session_id, runs:[{run_id, events:[...]}]}`이며 실행별 순번이 유지된다. 로그 경로는 조회와 삭제를 제공한다.
