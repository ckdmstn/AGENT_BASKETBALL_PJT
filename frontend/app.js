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
}

async function sendChat(message, retry = false) {
  if (!message || pending) return;
  if (!retry) bubble(message, true);
  messageInput.value = "";
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
    bubble(response.answer);
    document.dispatchEvent(new CustomEvent("chat-result", { detail: response }));
    const failed = response.events.some((event) => event.event_type === "RUN_FAILED");
    notice("chat-status", failed ? "추천 요청을 완료하지 못했습니다. 다시 시도할 수 있습니다."
      : response.errors.length ? "일부 조회가 실패했습니다. 추천과 제외 후보의 상태를 확인해 주세요." : "", failed ? "error" : "warning");
    if (failed) retryMessage = message;
  } catch (error) {
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
byId("retry-chat").addEventListener("click", () => sendChat(retryMessage, true));
byId("new-chat").addEventListener("click", () => {
  setSession(null);
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
  date: "날짜", time: "시각", team: "팀", weather: "날씨", detail: "경기 상세", league: "대회", arena: "경기장",
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
  if (weather) {
    const pop = weather.precipitation_probability_pct;
    const temp = weather.temperature_c;
    const weatherText = (weather.available ? "예보 제공" : "제공된 예보 없음")
      + " · 강수확률 " + (pop == null ? "미확인" : pop + "%")
      + " · 기온 " + (temp == null ? "미확인" : temp + " ℃")
      + (weather.precipitation_mm ? " · 강수량 " + weather.precipitation_mm : "");
    card.append(element("p", weatherText), element("small", "예보 대상 " + dateLabel(weather.forecast_at)));
  } else {
    card.append(element("p", "날씨 예보 미확인", "muted"));
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

function conditionList(title, values) {
  const group = element("div");
  const list = element("ul");
  for (const [key, value] of Object.entries(values)) {
    if (fieldLabels.has(key) && value != null && (!Array.isArray(value) || value.length)) {
      list.append(element("li", fieldLabels.get(key) + " · " + conditionLabel(key, value)));
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
    conditions.append(conditionList("재계획 " + step.attempt + "회차", step.changes));
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
  if (planDialog.open) return;
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
  if (planNote.value !== (plan.note ?? "")) changed.note = note;
  if (plan.id && !Object.keys(changed).length) {
    notice("plan-error", "변경된 항목이 없습니다.");
    return;
  }
  if (end && Date.parse(end) <= Date.parse(plan.start_at)) {
    notice("plan-error", "종료 시각은 경기 시작보다 늦어야 합니다.", "error");
    return;
  }
  setPlanBusy(true);
  try {
    const saved = plan.id ? await api("/api/plans/" + plan.id, "PATCH", changed)
      : await api("/api/plans", "POST", { ...plan, end_at: end, note });
    planDialog.close();
    const confirmation = notice("plan-notice", plan.id ? "계획을 수정했습니다." : "계획을 저장했습니다.");
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

