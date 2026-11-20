const byId = (id) => document.getElementById(id);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

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

