/* 投票页：分享码从 URL 取，每 3 秒刷新一次结果。负责人：D（前端）。 */
const $ = (sel) => document.querySelector(sel);

const code = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
const els = {
  title: $("#roomTitle"),
  meta: $("#roomMeta"),
  status: $("#roomStatus"),
  winner: $("#winnerBox"),
  options: $("#voteOptions"),
  message: $("#voteMessage"),
  total: $("#voteTotal"),
  refresh: $("#refreshBtn"),
  operator: $("#operator"),
  close: $("#closeBtn"),
};

function voterToken() {
  const key = "campus_eats_voter";
  let token = null;
  try { token = localStorage.getItem(key); } catch { /* 隐私模式 */ }
  if (!token) {
    token = (crypto.randomUUID && crypto.randomUUID()) ||
      `token-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    try { localStorage.setItem(key, token); } catch { /* 忽略 */ }
  }
  return token;
}

const token = voterToken();
const choiceKey = `campus_eats_vote_${code}`;

function myChoice() {
  try { return localStorage.getItem(choiceKey); } catch { return null; }
}

function setChoice(optionId) {
  try { localStorage.setItem(choiceKey, optionId); } catch { /* 忽略 */ }
}

function render(state) {
  const room = state.room;
  document.title = `${room.title} · 聚餐投票`;
  els.title.textContent = room.title;
  const closes = new Date(room.closes_at).toLocaleString("zh-CN", {
    month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
  els.meta.textContent = `发起人 ${room.creator} · 截止 ${closes}`;
  els.status.textContent = room.status === "OPEN" ? "进行中" : "已结束";
  els.status.className = `badge ${room.status === "OPEN" ? "badge-green" : "badge-amber"}`;
  els.total.textContent = `共 ${state.total_votes} 票`;

  els.winner.classList.remove("hidden");
  if (room.status === "CLOSED") {
    if (!state.winners.length) {
      els.winner.textContent = "投票结束，没有人投票。";
    } else if (state.tie) {
      const labels = state.tallies.filter((t) => state.winners.includes(t.option_id))
        .map((t) => `${t.label}（${t.count} 票）`);
      els.winner.textContent = `平票：${labels.join("、")}。再聊一轮吧。`;
    } else {
      const win = state.tallies.find((t) => t.option_id === state.winners[0]);
      els.winner.textContent = `结果：${win.label}（${win.count} 票）`;
    }
  } else if (!state.total_votes) {
    els.winner.textContent = "还没有人投票，先把链接发到群里吧。";
  } else if (state.tie) {
    els.winner.textContent = "当前平票，还差一票就能定下来。";
  } else {
    const lead = state.tallies.find((t) => t.option_id === state.winners[0]);
    els.winner.textContent = `当前领先：${lead.label}（${lead.count} 票）`;
  }

  const mine = myChoice();
  clear(els.options);
  const top = Math.max(0, ...state.tallies.map((t) => t.count));
  for (const tally of state.tallies) {
    const card = el("div", "result-card");
    const head = el("div", "section-head");
    head.style.marginBottom = "6px";
    const name = el("div");
    name.appendChild(el("strong", null, tally.label));
    if (tally.option_id === mine) name.appendChild(el("span", "badge badge-green", " 我已投"));
    head.appendChild(name);

    const count = el("span", "badge", `${tally.count} 票`);
    if (tally.count === top && top > 0) count.classList.add("badge-accent");
    head.appendChild(count);
    card.appendChild(head);

    const barWrap = el("div");
    barWrap.style.cssText = "height:10px;border-radius:999px;background:var(--surface-2);overflow:hidden";
    const bar = el("div");
    const percent = state.total_votes ? Math.round((tally.count / state.total_votes) * 100) : 0;
    bar.style.cssText = `height:100%;width:${percent}%;background:var(--accent);transition:width .4s ease`;
    barWrap.appendChild(bar);
    card.appendChild(barWrap);

    const actions = el("div", "result-actions");
    const voteBtn = el("button", "btn btn-primary btn-small", tally.option_id === mine ? "已投这一项" : "投它");
    voteBtn.type = "button";
    voteBtn.disabled = room.status !== "OPEN";
    voteBtn.addEventListener("click", () => cast(tally.option_id));
    actions.appendChild(voteBtn);
    actions.appendChild(el("span", "hint", `${percent}%`));
    card.appendChild(actions);
    els.options.appendChild(card);
  }
}

let current = null;

async function load() {
  try {
    const state = await api(`/api/votes/${encodeURIComponent(code)}`);
    current = state;
    render(state);
    setMessage(els.message, "");
  } catch (err) {
    setMessage(els.message, err.message, "error");
    els.title.textContent = "投票不存在";
  }
}

async function cast(optionId) {
  setMessage(els.message, "");
  try {
    const state = await api(`/api/votes/${encodeURIComponent(code)}/ballots`, {
      method: "POST",
      body: { voter_token: token, option_id: optionId },
    });
    setChoice(optionId);
    current = state;
    render(state);
    setMessage(els.message, "投票成功", "ok");
  } catch (err) {
    setMessage(els.message, err.message, "error");
  }
}

async function closeRoom() {
  try {
    const state = await api(`/api/votes/${encodeURIComponent(code)}/close`, {
      method: "POST",
      body: { operator: els.operator.value },
    });
    current = state;
    render(state);
    setMessage(els.message, "投票已结束", "ok");
  } catch (err) {
    setMessage(els.message, err.message, "error");
  }
}

els.refresh.addEventListener("click", load);
els.close.addEventListener("click", closeRoom);

if (!code) {
  setMessage(els.message, "链接里没有投票码", "error");
} else {
  load();
  setInterval(load, 3000);
}
