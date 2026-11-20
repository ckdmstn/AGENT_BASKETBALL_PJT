const byId = (id) => document.getElementById(id);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

const sessionKey = "kbl-go.session";
const chatForm = byId("chat-form");
const messageInput = byId("message");
let sessionId = null;
let pending = false;
let retryMessage = null;
let teamPermission = "unknown";
try {
  const saved = localStorage.getItem(sessionKey);
  if (saved && /^[a-zA-Z0-9_-]{1,100}$/.test(saved)) sessionId = saved;
} catch {
  // Session continuity still works in memory when browser storage is blocked.
}

function setSession(id) {
  sessionId = id;
  try {
    if (id) localStorage.setItem(sessionKey, id);
    else localStorage.removeItem(sessionKey);
  } catch {
    // Storage is optional.
  }
}

function bubble(message, fromUser = false) {
  const list = byId("messages");
  const entry = element("p", null, fromUser ? "bubble user" : "bubble");
  entry.append(element("strong", fromUser ? "나" : "KBL GO"), document.createTextNode("\n" + message));
  list.append(entry);
  list.scrollTop = list.scrollHeight;
}

function busyChat(busy) {
  pending = busy;
  for (const id of ["new-chat", "send", "message", "retry-chat"]) byId(id).disabled = busy;
  byId("send").textContent = busy ? "추천 요청 중…" : "보내기";
  updatePermissionButtons();
}

const permissionLabels = new Map([
  ["denied", ["미허용", "선호 팀 조건을 유지합니다.", ""]],
  ["allowed", ["허용됨", "원하는 팀 경기가 없을 때만 다른 팀도 검토할 수 있습니다.", "met"]],
  ["confirmation_required", ["확인 필요", "다른 팀 추천을 허용하시겠어요? 원하는 팀 경기가 없을 때 다른 팀도 추천받으려면 ‘다른 팀도 허용’을 선택하세요.", "unknown"]],
  ["unknown", ["상태 미확인", "아직 서버의 권한 상태를 확인하지 못했습니다.", ""]],
]);

function updatePermissionButtons() {
  byId("allow-team").disabled = pending || teamPermission === "allowed";
  byId("revoke-team").disabled = pending || teamPermission === "denied" || teamPermission === "confirmation_required";
}

function showPermission(response = null) {
  teamPermission = permissionLabels.has(response?.team_permission) ? response.team_permission
    : response || sessionId ? "unknown" : "denied";
  const [label, help, style] = permissionLabels.get(teamPermission);
  const badge = byId("team-permission");
  badge.textContent = label;
  badge.className = ["status", style].filter(Boolean).join(" ");
  byId("team-permission-help").textContent = help;
  const relaxation = byId("team-relaxation");
  const teamRelaxed = response?.conditions?.preferred_team && response.active_conditions?.preferred_team === null
    && response.relaxation_history?.some(({ changes }) => changes?.preferred_team === null);
  relaxation.textContent = teamRelaxed ? "이번 실행에서 선호 팀 조건이 완화됐습니다." : "";
  relaxation.hidden = !teamRelaxed;
  updatePermissionButtons();
}

async function sendChat(message, { retry = false, preserveDraft = false } = {}) {
  if (!message || pending) return;
  if (!retry) bubble(message, true);
  if (!retry && !preserveDraft) messageInput.value = "";
  byId("retry-chat").hidden = true;
  retryMessage = null;
  busyChat(true);
  notice("chat-status", "Agent가 요청을 처리하고 있습니다.");
  try {
    const response = await api("/api/chat", "POST", { session_id: sessionId, message });
    if (!response || typeof response.answer !== "string" || !response.session_id) {
      throw new Error("추천 결과를 읽을 수 없습니다. 다시 시도해 주세요.");
    }
    setSession(response.session_id);
    showPermission(response);
    bubble(response.answer);
    document.dispatchEvent(new CustomEvent("chat-result", { detail: response }));
    const failed = response.events.some((event) => event.event_type === "RUN_FAILED");
    notice("chat-status", failed ? "추천 요청을 완료하지 못했습니다. 다시 시도할 수 있습니다."
      : response.errors.length ? "일부 조회가 실패했습니다. 추천과 제외 후보의 상태를 확인해 주세요." : "", failed ? "error" : "warning");
    if (failed) retryMessage = message;
  } catch (error) {
    showPermission({});
    notice("chat-status", error.message, "error");
    retryMessage = message;
  } finally {
    busyChat(false);
    byId("retry-chat").hidden = !retryMessage;
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendChat(messageInput.value.trim());
});
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});
byId("retry-chat").addEventListener("click", () => sendChat(retryMessage, { retry: true }));
byId("allow-team").addEventListener("click", () => sendChat("다른 팀도 괜찮아.", { preserveDraft: true }));
byId("revoke-team").addEventListener("click", () => sendChat("다른 팀은 안 돼.", { preserveDraft: true }));
byId("new-chat").addEventListener("click", () => {
  setSession(null);
  showPermission();
  retryMessage = null;
  byId("retry-chat").hidden = true;
  messageInput.value = "";
  byId("messages").replaceChildren();
  bubble("새 대화를 시작했어요. 원하는 날짜, 지역, 팀을 알려주세요.");
  notice("chat-status", "");
  document.dispatchEvent(new CustomEvent("chat-result", { detail: null }));
  messageInput.focus();
});
if (sessionId) bubble("이전 대화의 조건을 이어갈 수 있어요.");
showPermission();

function button(text, action) {
  const node = element("button", text);
  node.type = "button";
  node.addEventListener("click", () => action(node));
  return node;
}

const errors = {
  400: "요청을 확인해 주세요.",
  404: "항목을 찾을 수 없습니다. 목록을 새로고침해 주세요.",
  422: "입력한 내용이나 시각을 확인해 주세요.",
  500: "서버에서 요청을 처리하지 못했습니다.",
  503: "저장소를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
};

async function api(path, method = "GET", data) {
  let response;
  try {
    response = await fetch(path, {
      method,
      ...(data === undefined ? {} : {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    });
  } catch {
    throw new Error("서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도해 주세요.");
  }
  if (!response.ok) throw new Error(errors[response.status] ?? "요청을 완료하지 못했습니다.");
  if (response.status === 204) return;
  try {
    return await response.json();
  } catch {
    throw new Error("서버 응답을 읽을 수 없습니다. 다시 시도해 주세요.");
  }
}

function notice(id, message, kind = "") {
  const node = byId(id);
  node.hidden = !message;
  node.className = ["notice", kind].filter(Boolean).join(" ");
  node.textContent = message;
  return node;
}

const clock = new Intl.DateTimeFormat("ko-KR", {
  dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Seoul",
});

function dateLabel(value) {
  const date = value && new Date(value);
  return date && Number.isFinite(date.getTime()) ? clock.format(date) : "시각 미확인";
}

const fieldLabels = new Map(Object.entries({
  date_range: "날짜", start_after: "이후 시작", region: "지역", preferred_team: "선호 팀",
  weather_preference: "날씨 선호", max_precipitation_probability_pct: "최대 강수확률",
  fallback_teams_allowed: "다른 팀 허용", alternative_date_ranges: "대체 날짜",
  date: "날짜", time: "시각", team: "팀", weather: "날씨", detail: "경기 상세", competition: "대회", venue: "경기장",
}));
const statuses = new Map([["met", "조건 충족"], ["unmet", "조건 불충족"], ["unknown", "정보 미확인"]]);
const results = byId("results");

function safeLink(value) {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return null;
    const link = element("a", "지도에서 경기장 보기");
    link.href = url.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
  } catch {
    return null;
  }
}

function statusBadge(value) {
  const status = statuses.has(value) ? value : "unknown";
  return element("span", statuses.get(status), "status " + status);
}

function match(assessment) {
  const { game, detail, arena } = assessment;
  return {
    match_id: assessment.match_id,
    home_team: detail?.home_team ?? game.home_team,
    away_team: detail?.away_team ?? game.away_team,
    venue_name: detail?.venue_name ?? game.venue_name,
    start_at: detail?.start_at ?? game.start_at,
    venue_address: arena?.verified_kbl_arena ? (arena.road_address || arena.address || null) : null,
  };
}

function matchTitle(game) {
  return game.home_team + " vs " + game.away_team;
}

function gameCard(assessment, recommended, owner) {
  const info = match(assessment);
  const card = element("article", null, recommended ? "entry game" : "entry");
  const heading = element("div", null, "section-head");
  heading.append(element("h3", matchTitle(info)), statusBadge(assessment.status));
  card.append(heading, element("p", dateLabel(info.start_at)),
    element("p", info.venue_name || "경기장 미확인"),
    element("p", info.venue_address || "검증된 주소 미확인", "muted"));
  const link = assessment.arena?.verified_kbl_arena && safeLink(assessment.arena.place_url);
  if (link) card.append(link);

  const weather = assessment.weather;
  if (weather?.available === true) {
    const pop = weather.precipitation_probability_pct;
    const temp = weather.temperature_c;
    const amount = String(weather.precipitation_mm ?? "").trim();
    const amountLabel = /^\d+(?:\.\d+)?$/.test(amount) ? amount + " mm" : amount;
    const weatherText = "강수확률 " + (pop == null ? "미확인" : pop + "%")
      + " · 기온 " + (temp == null ? "미확인" : temp + " ℃")
      + " · 강수량 " + (amountLabel || "미확인");
    card.append(element("p", "예보 대상 " + dateLabel(weather.forecast_at), "muted"),
      element("p", weatherText));
  } else if (weather) {
    card.append(element("p", "제공된 예보 없음", "muted"));
  } else {
    card.append(element("p", "날씨 예보 미확인", "muted"));
  }
  if (assessment.checks.weather?.status === "unknown") {
    card.append(element("p", "해당 경기 시각의 강수 조건을 확인하지 못했습니다.", "muted"));
  }

  const checks = element("ul", null, "checks");
  for (const [key, check] of Object.entries(assessment.checks)) {
    const item = element("li");
    item.append(statusBadge(check.status), document.createTextNode(" " + (fieldLabels.get(key) ?? "검증 항목") + " · " + check.reason));
    checks.append(item);
  }
  if (checks.children.length) {
    card.append(element("h4", recommended ? "추천 근거" : "제외 사유"), checks);
  }

  if (recommended) {
    const save = button("계획 저장", () => document.dispatchEvent(new CustomEvent("plan-from-match", {
      detail: { ...info, session_id: owner },
    })));
    save.disabled = !info.match_id || !info.home_team || !info.away_team || !info.venue_name || !info.start_at;
    card.append(save);
    if (save.disabled) card.append(element("p", "필수 경기 정보가 확인되면 저장할 수 있습니다.", "muted"));
  }
  return card;
}

function rangeLabel(value) {
  return value.from_date === value.to_date ? value.from_date : value.from_date + " ~ " + value.to_date;
}

function conditionLabel(key, value) {
  if (value == null || (Array.isArray(value) && !value.length)) return "미지정";
  if (key === "date_range") return rangeLabel(value);
  if (key === "alternative_date_ranges") return value.map(rangeLabel).join(", ");
  if (key === "fallback_teams_allowed") return value ? "허용" : "미허용";
  if (key === "weather_preference" && value === "low_rain") return "낮은 강수확률 선호";
  if (key === "max_precipitation_probability_pct") return value + "% 이하";
  return String(value);
}

function conditionList(title, values, includeCleared = false) {
  const group = element("div");
  const list = element("ul");
  for (const [key, value] of Object.entries(values)) {
    if (fieldLabels.has(key) && (includeCleared || (value != null && (!Array.isArray(value) || value.length)))) {
      const label = includeCleared && value == null ? "조건 해제" : conditionLabel(key, value);
      list.append(element("li", fieldLabels.get(key) + " · " + label));
    }
  }
  group.append(element("h4", title), list.children.length ? list : element("p", "지정된 조건 없음", "muted"));
  return group;
}

document.addEventListener("chat-result", ({ detail: response }) => {
  results.replaceChildren();
  byId("result-count").textContent = response ? response.recommendations.length + "경기" : "";
  if (!response) {
    results.append(element("p", "채팅을 보내면 추천 경기와 조건 검증 결과가 여기에 표시됩니다.", "empty"));
    return;
  }
  if (!response.recommendations.length) {
    const unavailable = response.events.some((event) => event.event_type === "RUN_FAILED");
    const lookedUp = response.events.some((event) => event.event_type === "TOOL_RESPONDED");
    const emptyMessage = unavailable ? "추천을 완료하지 못했습니다."
      : response.errors.some((error) => error.code !== "NO_RESULT") ? "조회 실패로 추천 경기를 확인하지 못했습니다."
      : lookedUp ? "조건에 맞는 추천 경기가 없습니다." : "이번 대화에서 경기 조회를 실행하지 않았습니다.";
    results.append(element("p", emptyMessage, "empty"));
  }
  for (const recommendation of response.recommendations) {
    results.append(gameCard(recommendation, true, response.session_id));
  }
  for (const warning of response.warnings) results.append(element("p", warning, "notice warning"));

  const conditions = element("details");
  conditions.open = response.replan_count > 0;
  const grid = element("div", null, "condition-grid");
  grid.append(conditionList("원래 요청한 조건", response.conditions),
    conditionList("실제 적용된 조건", response.active_conditions));
  conditions.append(element("summary", "요청 조건 및 재계획 " + response.replan_count + "회"), grid);
  for (const step of response.relaxation_history) {
    const action = conditionList("재계획 " + step.attempt + "회차", step.changes, true);
    action.className = "replan-step";
    conditions.append(action);
  }
  results.append(conditions);

  if (response.excluded.length) {
    const excluded = element("details");
    excluded.append(element("summary", "제외 후보 " + response.excluded.length + "경기"));
    for (const assessment of response.excluded) excluded.append(gameCard(assessment, false));
    results.append(excluded);
  }
});

const planDialog = byId("plan-dialog");
const planForm = byId("plan-form");
const planEnd = byId("end-at");
const planNote = byId("plan-note");
let selectedPlan = null;
let planBusy = false;
let planLoad = 0;

function kstInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  return new Date(date.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 16);
}

function openPlan(plan) {
  if (planDialog.open || planBusy) return;
  selectedPlan = plan;
  byId("plan-title").textContent = plan.id ? "저장한 계획 상세" : "직관 계획 저장";
  const summary = byId("plan-summary");
  summary.replaceChildren(element("h3", matchTitle(plan)),
    element("p", dateLabel(plan.start_at) + " · " + plan.venue_name));
  if (plan.venue_address) summary.append(element("p", plan.venue_address));
  if (plan.id) summary.append(element("small", "저장 " + dateLabel(plan.created_at) + " · 수정 " + dateLabel(plan.updated_at)));
  planEnd.value = kstInput(plan.end_at);
  planNote.value = plan.note ?? "";
  byId("delete-plan").hidden = !plan.id;
  notice("plan-error", "");
  planDialog.showModal();
}

function setPlanBusy(value) {
  planBusy = value;
  for (const id of ["close-plan", "delete-plan", "save-plan", "end-at", "plan-note"]) byId(id).disabled = value;
}

async function loadPlans() {
  const request = ++planLoad;
  const list = byId("plan-list");
  if (!list.children.length) list.append(element("p", "계획을 불러오는 중…", "muted"));
  try {
    const plans = await api("/api/plans");
    if (request !== planLoad) return;
    list.replaceChildren();
    if (!plans.length) list.append(element("p", "아직 저장한 직관 계획이 없습니다.", "empty"));
    for (const plan of plans) {
      const entry = element("article", null, "entry");
      entry.append(element("h3", matchTitle(plan)), element("p", dateLabel(plan.start_at) + " · " + plan.venue_name));
      if (plan.note) entry.append(element("p", plan.note, "muted"));
      entry.append(button("계획 상세", async (trigger) => {
        trigger.disabled = true;
        notice("plan-notice", "");
        try {
          openPlan(await api("/api/plans/" + plan.id));
        } catch (error) {
          notice("plan-notice", error.message, "error");
        } finally {
          trigger.disabled = false;
        }
      }));
      list.append(entry);
    }
  } catch (error) {
    if (request === planLoad) {
      const errorMessage = element("p", error.message, "notice error");
      list.replaceChildren(errorMessage);
    }
  }
}

document.addEventListener("plan-from-match", ({ detail }) => openPlan(detail));
byId("refresh-plans").addEventListener("click", loadPlans);
byId("close-plan").addEventListener("click", () => planDialog.close());
planDialog.addEventListener("cancel", (event) => {
  if (planBusy) event.preventDefault();
});

planForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (planBusy || !selectedPlan) return;
  const plan = selectedPlan;
  const changed = {};
  const end = planEnd.value ? planEnd.value + ":00+09:00" : null;
  const note = planNote.value.trim() || null;
  if (planEnd.value !== kstInput(plan.end_at)) changed.end_at = end;
  if (planNote.value !== (plan.note ?? "") && note !== (plan.note ?? null)) changed.note = note;
  if (plan.id && !Object.keys(changed).length) {
    notice("plan-error", "변경된 항목이 없습니다.");
    return;
  }
  const effectiveEnd = Object.hasOwn(changed, "end_at") ? end : (plan.end_at ?? end);
  if (effectiveEnd && Date.parse(effectiveEnd) <= Date.parse(plan.start_at)) {
    notice("plan-error", "종료 시각은 경기 시작보다 늦어야 합니다.", "error");
    return;
  }
  setPlanBusy(true);
  try {
    const saved = plan.id ? await api("/api/plans/" + plan.id, "PATCH", changed)
      : await api("/api/plans", "POST", { ...plan, end_at: end, note });
    planDialog.close();
    const confirmation = notice("plan-notice", plan.id ? "계획을 수정했습니다." : "계획을 저장했습니다.", "success");
    if (saved.overlap_warnings.length || saved.overlapping_plan_ids.length) {
      const warning = element("div", null, "notice warning");
      warning.append(element("strong", "일정 경고"));
      for (const message of saved.overlap_warnings) warning.append(element("p", message));
      if (saved.overlapping_plan_ids.length) {
        warning.append(element("p", "겹치는 계획 ID " + saved.overlapping_plan_ids.join(", ")));
      }
      confirmation.append(warning);
    }
    await loadPlans();
  } catch (error) {
    notice("plan-error", error.message, "error");
  } finally {
    setPlanBusy(false);
  }
});

byId("delete-plan").addEventListener("click", async () => {
  if (planBusy || !selectedPlan?.id || !confirm("이 직관 계획을 삭제할까요?")) return;
  setPlanBusy(true);
  try {
    await api("/api/plans/" + selectedPlan.id, "DELETE");
    planDialog.close();
    notice("plan-notice", "계획을 삭제했습니다.");
    await loadPlans();
  } catch (error) {
    notice("plan-error", error.message, "error");
  } finally {
    setPlanBusy(false);
  }
});
loadPlans();

const eventLabels = new Map(Object.entries({
  NODE_STARTED: "단계 시작", NODE_COMPLETED: "단계 완료", TOOL_REQUESTED: "Tool 요청",
  TOOL_RESPONDED: "Tool 응답", LLM_DECISION: "판단", REPLAN_STARTED: "재계획",
  RUN_COMPLETED: "실행 완료", RUN_FAILED: "실행 실패",
}));
const nodeLabels = new Map(Object.entries({
  analyze: "요청 분석", plan: "조회 계획", execute_tools: "경기·장소·날씨 조회",
  evaluate: "조건 검증", replan: "조건 조정", respond: "응답 작성",
}));
const toolLabels = new Map(Object.entries({
  search_kbl_games: "KBL 일정", get_kbl_game_detail: "경기 상세", search_arena: "경기장 검색", get_weather: "기상청 예보",
}));
const reasons = new Map(Object.entries({
  intent_and_condition_extraction: "요청 의도와 조건을 추출했습니다.",
  tools_for_condition_verification: "조건 검증에 필요한 Tool과 실행 순서를 선택했습니다.",
  verified_facts_rendering: "검증된 정보로 응답을 작성했습니다.",
  authorized_condition_relaxation: "사용자가 허용한 범위에서 조건을 조정했습니다.",
}));
let logListRequest = 0;
let logDetailRequest = 0;

function timelineEvent(event) {
  const payload = event.payload ?? {};
  const item = element("li", null, event.event_type === "REPLAN_STARTED" ? "replan" : "");
  item.value = event.sequence_no;
  const state = [];
  if (payload.ok === true) state.push("성공");
  if (payload.ok === false) state.push("실패");
  if (payload.cached === true) state.push("캐시 재사용");
  const title = [eventLabels.get(event.event_type) ?? "이벤트", nodeLabels.get(event.node_name),
    toolLabels.get(event.tool_name), ...state].filter(Boolean).join(" · ");
  item.append(element("strong", title), element("div", dateLabel(event.timestamp), "muted"));
  const reason = reasons.get(payload.reason_code);
  if (reason) item.append(element("div", reason));
  else if (event.event_type === "LLM_DECISION" || event.event_type === "REPLAN_STARTED") {
    item.append(element("div", "기록된 판단 사유를 표시할 수 없습니다.", "muted"));
  }
  if (Array.isArray(payload.tools)) {
    const tools = payload.tools.map((name) => toolLabels.get(name)).filter(Boolean);
    if (tools.length) item.append(element("div", "Tool 순서 " + tools.join(" · "), "muted"));
  }
  if (Number.isInteger(payload.attempt)) item.append(element("div", "재계획 " + payload.attempt + "회차"));
  return item;
}

async function readLog(id) {
  const request = ++logDetailRequest;
  const panel = byId("log-detail");
  notice("log-status", "");
  panel.replaceChildren(element("p", "실행 기록을 불러오는 중…", "muted"));
  try {
    const result = await api("/api/logs/" + encodeURIComponent(id));
    if (request !== logDetailRequest) return;
    panel.replaceChildren(element("h3", "세션 " + result.session_id));
    for (const run of result.runs) {
      const detail = element("details");
      const timeline = element("ol", null, "timeline");
      for (const event of [...run.events].sort((a, b) => a.sequence_no - b.sequence_no)) {
        timeline.append(timelineEvent(event));
      }
      detail.append(element("summary", "실행 " + run.run_id + " · 이벤트 " + run.events.length + "개"), timeline);
      panel.append(detail);
    }
    if (panel.lastElementChild?.tagName === "DETAILS") panel.lastElementChild.open = true;
  } catch (error) {
    if (request !== logDetailRequest) return;
    panel.replaceChildren();
    notice("log-status", error.message, "error");
  }
}

async function loadLogs() {
  const request = ++logListRequest;
  const list = byId("log-list");
  if (!list.children.length) list.append(element("p", "실행 기록을 불러오는 중…", "muted"));
  try {
    const summaries = await api("/api/logs");
    if (request !== logListRequest) return;
    list.replaceChildren();
    if (!summaries.length) list.append(element("p", "아직 저장된 실행 기록이 없습니다.", "empty"));
    for (const summary of summaries) {
      const id = summary.session_id;
      const card = element("article", null, "entry");
      const head = element("div", null, "section-head");
      head.append(element("h3", id === sessionId ? "현재 채팅 세션" : "다른 채팅 세션"),
        element("span", "실행 " + summary.run_count + "회 · 이벤트 " + summary.event_count + "개", "count"));
      card.append(head, element("p", id, "muted"),
        element("p", "마지막 이벤트 " + dateLabel(summary.last_event_at)));
      const actions = element("div", null, "actions");
      const remove = button("로그 삭제", async (trigger) => {
        if (!confirm("이 세션의 실행 기록을 삭제할까요?")) return;
        trigger.disabled = true;
        try {
          await api("/api/logs/" + encodeURIComponent(id), "DELETE");
          ++logDetailRequest;
          byId("log-detail").replaceChildren();
          notice("log-status", "실행 기록을 삭제했습니다.");
          await loadLogs();
        } catch (error) {
          notice("log-status", error.message, "error");
        } finally {
          trigger.disabled = false;
        }
      });
      remove.classList.add("danger");
      actions.append(button("실행 상세", () => readLog(id)), remove);
      card.append(actions);
      list.append(card);
    }
  } catch (error) {
    if (request === logListRequest) list.replaceChildren(element("p", error.message, "notice error"));
  }
}

document.addEventListener("chat-result", loadLogs);
byId("refresh-logs").addEventListener("click", loadLogs);
loadLogs();
