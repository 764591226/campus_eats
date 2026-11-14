/* 首页：筛选 → 转盘抽签 → 评价 / 历史 / 发起投票。负责人：D（前端）。 */
const $ = (sel) => document.querySelector(sel);

const state = {
  meta: null,
  venues: [],
  excluded: [],
  current: null,
  rating: 5,
  spinning: false,
  rotation: 0,
};

const els = {
  campus: $("#campus"),
  meal: $("#mealPeriod"),
  budget: $("#budget"),
  tags: $("#tagChips"),
  spicy: $("#excludeSpicy"),
  recent: $("#avoidRecent"),
  spin: $("#spinBtn"),
  clearExcluded: $("#clearExcluded"),
  excludedHint: $("#excludedHint"),
  filterMessage: $("#filterMessage"),
  wheel: $("#wheel"),
  resultEmpty: $("#resultEmpty"),
  resultCard: $("#resultCard"),
  resultName: $("#resultName"),
  resultMeta: $("#resultMeta"),
  resultPrice: $("#resultPrice"),
  resultTags: $("#resultTags"),
  resultRating: $("#resultRating"),
  resultReason: $("#resultReason"),
  resultAlts: $("#resultAlternatives"),
  reroll: $("#rerollBtn"),
  reviewForm: $("#reviewForm"),
  reviewAuthor: $("#reviewAuthor"),
  reviewComment: $("#reviewComment"),
  reviewMessage: $("#reviewMessage"),
  ratingStars: $("#ratingStars"),
  history: $("#historyList"),
  voteTitle: $("#voteTitle"),
  voteMinutes: $("#voteMinutes"),
  voteCreator: $("#voteCreator"),
  voteVenues: $("#voteVenues"),
  createVote: $("#createVoteBtn"),
  voteMessage: $("#voteMessage"),
  shareBox: $("#shareBox"),
  shareLink: $("#shareLink"),
  copyLink: $("#copyLinkBtn"),
  openLink: $("#openLink"),
};

function selectedTags() {
  return [...els.tags.querySelectorAll("[aria-pressed='true']")].map((b) => b.dataset.tag);
}

function buildFilters() {
  return {
    campus_id: els.campus.value || null,
    meal_period: els.meal.value || null,
    max_price_fen: els.budget.value ? Number(els.budget.value) : null,
    include_tags: selectedTags(),
    exclude_tags: els.spicy.checked ? ["辣"] : [],
    exclude_dish_ids: [...state.excluded],
    exclude_recent: els.recent.checked,
    recent_days: 7,
  };
}

function updateExcludedHint() {
  els.excludedHint.textContent = state.excluded.length
    ? `已排除 ${state.excluded.length} 个菜`
    : "还没排除任何菜";
}

function setRating(value) {
  state.rating = value;
  for (const btn of els.ratingStars.querySelectorAll("button")) {
    btn.setAttribute("aria-pressed", String(Number(btn.dataset.rating) <= value));
  }
}

function renderTags(tags) {
  clear(els.tags);
  for (const tag of tags) {
    const btn = el("button", "chip", tag);
    btn.type = "button";
    btn.dataset.tag = tag;
    btn.setAttribute("aria-pressed", "false");
    btn.addEventListener("click", () => {
      btn.setAttribute("aria-pressed", btn.getAttribute("aria-pressed") === "true" ? "false" : "true");
    });
    els.tags.appendChild(btn);
  }
}

function renderVoteVenues() {
  clear(els.voteVenues);
  for (const venue of state.venues) {
    const label = el("label", "check");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = venue.id;
    box.dataset.label = `${venue.name}（${venue.location || KIND_LABELS[venue.kind]}）`;
    label.appendChild(box);
    label.appendChild(document.createTextNode(
      `${venue.name} · ${venue.location || ""} ${KIND_LABELS[venue.kind] || ""}`.trim()));
    els.voteVenues.appendChild(label);
  }
}

async function loadMeta() {
  const [meta, venues] = await Promise.all([api("/api/meta"), api("/api/venues")]);
  state.meta = meta;
  state.venues = venues;

  clear(els.campus);
  const all = el("option", null, "全部校区");
  all.value = "";
  els.campus.appendChild(all);
  for (const campus of meta.campuses) {
    const opt = el("option", null, campus.name);
    opt.value = campus.id;
    els.campus.appendChild(opt);
  }

  renderTags(meta.tags);
  renderVoteVenues();
}

function spinWheel() {
  state.rotation += 900 + Math.floor(Math.random() * 480);
  els.wheel.style.transform = `rotate(${state.rotation}deg)`;
}

function showResult(result) {
  state.current = result;
  const w = result.winner;
  els.resultEmpty.classList.add("hidden");
  els.resultCard.classList.remove("hidden");

  els.resultName.textContent = w.dish.name;
  els.resultMeta.textContent = [
    w.campus.name,
    w.venue.name,
    w.venue.location,
    KIND_LABELS[w.venue.kind],
  ].filter(Boolean).join(" · ");
  els.resultPrice.textContent = yen(w.dish.price_fen);

  clear(els.resultTags);
  for (const tag of w.dish.tags) {
    els.resultTags.appendChild(el("span", "badge", tag));
  }
  if (w.recent) els.resultTags.appendChild(el("span", "badge badge-amber", "最近吃过 · 兜底"));
  if (w.dish.source === "DEMO") els.resultTags.appendChild(el("span", "badge", "演示数据"));
  if (w.dish.source === "TAKEOUT") els.resultTags.appendChild(el("span", "badge", "外卖样例"));
  if (!w.dish.available) els.resultTags.appendChild(el("span", "badge badge-danger", "已下架"));

  const rating = w.rating;
  els.resultRating.textContent = rating.count
    ? `${stars(rating.average)} ${rating.average.toFixed(1)} · ${rating.count} 条评价`
    : "还没有评价，抽完可以当第一个打分的人";

  els.resultReason.textContent = result.reason;

  clear(els.resultAlts);
  for (const alt of result.alternatives || []) {
    const row = el("div", "alt-item");
    row.appendChild(el("span", null, `${alt.dish.name} · ${alt.venue.name}`));
    row.appendChild(el("span", null, yen(alt.dish.price_fen)));
    els.resultAlts.appendChild(row);
  }

  els.reviewForm.classList.remove("hidden");
  els.reviewComment.value = "";
  setRating(5);
  setMessage(els.reviewMessage, "");
}

async function spin() {
  if (state.spinning) return;
  state.spinning = true;
  els.spin.disabled = true;
  els.reroll.disabled = true;
  setMessage(els.filterMessage, "正在转……");
  spinWheel();

  try {
    await new Promise((resolve) => setTimeout(resolve, 650));
    const result = await api("/api/decisions", {
      method: "POST",
      body: { filters: buildFilters(), mode: "WHEEL" },
    });
    showResult(result);
    setMessage(els.filterMessage, "");
    if (window.matchMedia("(max-width: 900px)").matches) {
      els.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    await loadHistory();
  } catch (err) {
    setMessage(els.filterMessage, err.message, "error");
  } finally {
    state.spinning = false;
    els.spin.disabled = false;
    els.reroll.disabled = false;
  }
}

async function loadHistory() {
  try {
    const rows = await api("/api/decisions?limit=8");
    clear(els.history);
    if (!rows.length) {
      els.history.appendChild(el("p", "hint", "还没抽过。"));
      return;
    }
    for (const row of rows) {
      const item = el("div", "history-item");
      item.appendChild(el("span", null, `${row.dish.name} · ${row.venue.name}`));
      item.appendChild(el("span", "history-time", formatTime(row.decision.created_at)));
      els.history.appendChild(item);
    }
  } catch (err) {
    setMessage(els.filterMessage, err.message, "error");
  }
}

async function submitReview(event) {
  event.preventDefault();
  if (!state.current) return;
  const dishId = state.current.winner.dish.id;
  setMessage(els.reviewMessage, "提交中……");
  try {
    await api("/api/reviews", {
      method: "POST",
      body: {
        dish_id: dishId,
        rating: state.rating,
        comment: els.reviewComment.value,
        author: els.reviewAuthor.value,
      },
    });
    setMessage(els.reviewMessage, "评价已提交，谢谢！", "ok");
    const detail = await api(`/api/dishes/${encodeURIComponent(dishId)}`);
    const rating = detail.rating;
    els.resultRating.textContent = rating.count
      ? `${stars(rating.average)} ${rating.average.toFixed(1)} · ${rating.count} 条评价`
      : "还没有评价";
  } catch (err) {
    setMessage(els.reviewMessage, err.message, "error");
  }
}

async function createVote() {
  setMessage(els.voteMessage, "");
  const checked = [...els.voteVenues.querySelectorAll("input:checked")];
  if (checked.length < 2 || checked.length > 8) {
    setMessage(els.voteMessage, "请选择 2–8 个候选地点", "error");
    return;
  }
  const options = checked.map((box) => ({
    option_id: box.value,
    label: box.dataset.label.slice(0, 30),
  }));
  try {
    const room = await api("/api/votes", {
      method: "POST",
      body: {
        title: els.voteTitle.value,
        options,
        minutes: Number(els.voteMinutes.value),
        creator: els.voteCreator.value,
      },
    });
    const link = `${location.origin}/vote/${room.code}`;
    els.shareLink.value = link;
    els.openLink.href = `/vote/${room.code}`;
    els.shareBox.classList.remove("hidden");
    setMessage(els.voteMessage, `投票已创建，分享码 ${room.code}`, "ok");
  } catch (err) {
    setMessage(els.voteMessage, err.message, "error");
  }
}

async function copyLink() {
  els.shareLink.select();
  try {
    await navigator.clipboard.writeText(els.shareLink.value);
    setMessage(els.voteMessage, "链接已复制", "ok");
  } catch {
    document.execCommand("copy");
    setMessage(els.voteMessage, "已选中，请手动复制", "ok");
  }
}

function bindEvents() {
  els.spin.addEventListener("click", spin);
  els.reroll.addEventListener("click", () => {
    if (!state.current) return;
    state.excluded.push(state.current.winner.dish.id);
    updateExcludedHint();
    spin();
  });
  els.clearExcluded.addEventListener("click", () => {
    state.excluded = [];
    updateExcludedHint();
    setMessage(els.filterMessage, "已清空排除列表");
  });
  els.reviewForm.addEventListener("submit", submitReview);
  els.ratingStars.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-rating]");
    if (btn) setRating(Number(btn.dataset.rating));
  });
  els.createVote.addEventListener("click", createVote);
  els.copyLink.addEventListener("click", copyLink);
}

async function init() {
  bindEvents();
  updateExcludedHint();
  setRating(5);
  try {
    await loadMeta();
    await loadHistory();
  } catch (err) {
    setMessage(els.filterMessage, err.message, "error");
  }
}

init();
