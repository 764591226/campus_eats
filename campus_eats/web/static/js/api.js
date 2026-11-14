/* 前后端之间的薄封装。所有页面共用。
   只负责请求和显示工具，不写业务规则（价格、能否抽签由后端决定）。 */
async function api(path, options = {}) {
  const init = { ...options };
  init.headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const res = await fetch(path, init);
  let data = null;
  try { data = await res.json(); } catch { /* 空响应 */ }
  if (!res.ok) {
    const info = data && data.error ? data.error : {};
    const err = new Error(info.message || `请求失败（${res.status}）`);
    err.code = info.code || "HTTP_ERROR";
    err.status = res.status;
    err.details = info.details || {};
    throw err;
  }
  return data;
}

const yen = (fen) => `¥${(fen / 100).toFixed(2).replace(/\.00$/, "")}`;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function setMessage(node, text, kind = "") {
  if (!node) return;
  node.textContent = text || "";
  node.className = `message${kind ? ` ${kind}` : ""}`;
}

function formatTime(ms) {
  try {
    return new Date(ms).toLocaleString("zh-CN", {
      month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return "";
  }
}

const MEAL_LABELS = {
  BREAKFAST: "早餐", LUNCH: "午餐", DINNER: "晚餐", LATE_NIGHT: "夜宵",
};

const KIND_LABELS = { CANTEEN: "食堂", WINDOW: "窗口", TAKEOUT: "外卖" };

const CATEGORY_LABELS = {
  RICE: "盖饭", NOODLE: "面食", SNACK: "小吃", SET: "套餐",
  DRINK: "饮品", OTHER: "其他",
};

function stars(average) {
  const rounded = Math.round(average || 0);
  return "★".repeat(rounded) + "☆".repeat(Math.max(0, 5 - rounded));
}
