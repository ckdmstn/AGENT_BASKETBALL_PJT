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

