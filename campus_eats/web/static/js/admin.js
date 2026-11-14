/* 管理后台：看板、菜品 / 窗口维护、评价管理。负责人：A（项目 / 产品 + UI & 文档）。
   只调用 HTTP 接口，不在前端写业务规则；所有用户输入都用 textContent 插入。 */
const $ = (sel) => document.querySelector(sel);

const OPERATOR_KEY = "campus_eats_operator";
const SOURCE_LABELS = { DEMO: "演示", SURVEY: "调研", TAKEOUT: "外卖" };

const state = {
  campuses: [],
  venues: [],
  dishes: [],
  campusNames: new Map(),
  venueNames: new Map(),
  dishNames: new Map(),
  editingDish: null,
  editingVenue: null,
};

const els = {
  operator: $("#operator"),
  statCampus: $("#statCampus"),
  statRange: $("#statRange"),
  statScope: $("#statScope"),
  statDecisions: $("#statDecisions"),
  statReviews: $("#statReviews"),
  statRating: $("#statRating"),
  statRooms: $("#statRooms"),
  statBallots: $("#statBallots"),
  topDishes: $("#topDishes"),
  dishesBody: $("#dishesBody"),
  venuesBody: $("#venuesBody"),
  reviews: $("#adminReviews"),
  adminMessage: $("#adminMessage"),
  reviewMessage: $("#reviewMessage"),
  dishMessage: $("#dishMessage"),
  venueMessage: $("#venueMessage"),
  venueListMessage: $("#venueListMessage"),
  dishFormTitle: $("#dishFormTitle"),
  dishFormHint: $("#dishFormHint"),
  dishEditingNote: $("#dishEditingNote"),
  dishEditingName: $("#dishEditingName"),
  dishId: $("#dishId"), dishName: $("#dishName"), dishVenue: $("#dishVenue"),
  dishCategory: $("#dishCategory"), dishPrice: $("#dishPrice"),
  dishSource: $("#dishSource"), dishTags: $("#dishTags"), dishDesc: $("#dishDesc"),
  dishAvailable: $("#dishAvailable"), addDishBtn: $("#addDishBtn"),
  venueFormTitle: $("#venueFormTitle"),
  venueFormHint: $("#venueFormHint"),
  venueEditingNote: $("#venueEditingNote"),
  venueEditingName: $("#venueEditingName"),
  venueId: $("#venueId"), venueName: $("#venueName"), venueCampus: $("#venueCampus"),
  venueKind: $("#venueKind"), venueLocation: $("#venueLocation"),
  venueTags: $("#venueTags"), addVenueBtn: $("#addVenueBtn"),
};

function operator() {
  return els.operator.value.trim();
}

function needOperator(messageEl) {
  if (!operator()) {
    setMessage(messageEl, "请先在左侧“数据看板”里填写操作人昵称", "error");
    els.operator.focus();
    return false;
  }
  return true;
}

function parseTags(text) {
  return text.split(/[,，、]/).map((s) => s.trim()).filter(Boolean);
}

function fillSelect(select, rows, valueKey, labelKey, placeholder = null,
                    selected = null) {
  const keep = selected === null ? select.value : selected;
  clear(select);
  if (placeholder) {
    const opt = el("option", null, placeholder);
    opt.value = "";
    select.appendChild(opt);
  }
  for (const row of rows) {
    const opt = el("option", null, row[labelKey]);
    opt.value = row[valueKey];
    if (row[valueKey] === keep) opt.selected = true;
    select.appendChild(opt);
  }
}

function summaryQuery() {
  const params = new URLSearchParams();
  if (els.statCampus.value) params.set("campus_id", els.statCampus.value);
  const range = els.statRange.value;
  if (range === "today") {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    params.set("since_ms", String(start.getTime()));
  } else if (range === "7" || range === "30") {
    params.set("since_ms", String(Date.now() - Number(range) * 24 * 60 * 60 * 1000));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function updateStatScope() {
  const campus = els.statCampus.selectedOptions[0]?.textContent || "全部校区";
  const range = els.statRange.selectedOptions[0]?.textContent || "全部时间";
  els.statScope.textContent = `${range} · ${campus}`;
}

function renderStats(summary) {
  els.statDecisions.textContent = summary.decision_count;
  els.statReviews.textContent = summary.review_count;
  els.statRating.textContent = summary.review_count ? summary.avg_rating.toFixed(1) : "—";
  els.statRooms.textContent = summary.vote_room_count;
  els.statBallots.textContent = summary.ballot_count;
  updateStatScope();

  clear(els.topDishes);
  if (!summary.top_dishes.length) {
    els.topDishes.appendChild(el("p", "hint", "这个范围内还没有抽签数据。"));
    return;
  }
  for (const row of summary.top_dishes) {
    const line = el("div", "top-row");
    line.appendChild(el("strong", null, row.label));
    line.appendChild(el("span", null, `${row.count} 次`));
    els.topDishes.appendChild(line);
  }
}

function emptyRow(colspan, text) {
  const tr = document.createElement("tr");
  const td = el("td", "empty-cell", text);
  td.colSpan = colspan;
  tr.appendChild(td);
  return tr;
}

function renderDishes() {
  clear(els.dishesBody);
  if (!state.dishes.length) {
    els.dishesBody.appendChild(emptyRow(7, "还没有菜品。先在上方表单添加一道。"));
    return;
  }
  for (const dish of state.dishes) {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, dish.name));
    tr.appendChild(el("td", null, state.venueNames.get(dish.venue_id) || dish.venue_id));
    tr.appendChild(el("td", null, yen(dish.price_fen)));
    tr.appendChild(el("td", null, CATEGORY_LABELS[dish.category] || dish.category));
    tr.appendChild(el("td", null, SOURCE_LABELS[dish.source] || dish.source));

    const status = el("td");
    status.appendChild(el("span",
      `badge ${dish.available ? "badge-green" : "badge-danger"}`,
      dish.available ? "在售" : "已下架"));
    tr.appendChild(status);

    const actions = el("td", "table-actions");
    const edit = el("button", "btn btn-small btn-ghost", "编辑");
    edit.type = "button";
    edit.addEventListener("click", () => fillDishForm(dish));
    actions.appendChild(edit);

    const toggle = el("button", `btn btn-small ${dish.available ? "btn-danger" : ""}`,
      dish.available ? "下架" : "上架");
    toggle.type = "button";
    toggle.addEventListener("click", () => toggleDish(dish));
    actions.appendChild(toggle);
    tr.appendChild(actions);
    els.dishesBody.appendChild(tr);
  }
}

function renderVenues() {
  clear(els.venuesBody);
  if (!state.venues.length) {
    els.venuesBody.appendChild(emptyRow(6, "还没有可管理的窗口。"));
    return;
  }
  for (const venue of state.venues) {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, venue.name));
    tr.appendChild(el("td", null,
      state.campusNames.get(venue.campus_id) || venue.campus_id));
    tr.appendChild(el("td", null, KIND_LABELS[venue.kind] || venue.kind));
    tr.appendChild(el("td", null, venue.location || "—"));
    tr.appendChild(el("td", null,
      venue.open_periods.map((p) => MEAL_LABELS[p] || p).join(" / ")));

    const actions = el("td", "table-actions");
    const edit = el("button", "btn btn-small btn-ghost", "编辑");
    edit.type = "button";
    edit.addEventListener("click", () => fillVenueForm(venue));
    actions.appendChild(edit);
    tr.appendChild(actions);
    els.venuesBody.appendChild(tr);
  }
}

function renderReviews(reviews) {
  clear(els.reviews);
  if (!reviews.length) {
    els.reviews.appendChild(el("p", "hint", "还没有评价。"));
    return;
  }
  for (const review of reviews) {
    const item = el("div", "review-admin-item");
    const head = el("div", "review-admin-head");
    const left = el("span");
    left.appendChild(el("strong", null,
      state.dishNames.get(review.dish_id) || review.dish_id));
    left.appendChild(el("span", "badge badge-amber", ` ${review.rating} 星`));
    head.appendChild(left);
    const right = el("span", "hint", `${review.author} · ${formatTime(review.created_at)}`);
    head.appendChild(right);
    item.appendChild(head);
    item.appendChild(el("div", "review-admin-body",
      review.comment || "（没有写评论）"));
    const actions = el("div", "table-actions");
    const del = el("button", "btn btn-small btn-danger", "删除");
    del.type = "button";
    del.addEventListener("click", () => deleteReview(review));
    actions.appendChild(del);
    item.appendChild(actions);
    els.reviews.appendChild(item);
  }
}

function refreshMaps() {
  state.campusNames = new Map(state.campuses.map((c) => [c.id, c.name]));
  state.venueNames = new Map(state.venues.map((v) => [v.id, v.name]));
  state.dishNames = new Map(state.dishes.map((d) => [d.id, d.name]));
}

async function loadAll() {
  try {
    const meta = await api("/api/meta");
    state.campuses = meta.campuses;
    fillSelect(els.statCampus, meta.campuses, "id", "name", "全部校区");
    fillSelect(els.venueCampus, meta.campuses, "id", "name");

    const [venues, dishes, summary, reviews] = await Promise.all([
      api("/api/venues"),
      api("/api/dishes?include_unavailable=1"),
      api(`/api/admin/summary${summaryQuery()}`),
      api("/api/admin/reviews?limit=30"),
    ]);
    state.venues = venues;
    state.dishes = dishes;
    refreshMaps();

    fillSelect(els.dishVenue, venues, "id", "name");
    renderStats(summary);
    renderDishes();
    renderVenues();
    renderReviews(reviews);
    setMessage(els.adminMessage, "");
  } catch (err) {
    setMessage(els.adminMessage, err.message, "error");
  }
}

async function loadSummary() {
  try {
    renderStats(await api(`/api/admin/summary${summaryQuery()}`));
    setMessage(els.adminMessage, "");
  } catch (err) {
    setMessage(els.adminMessage, err.message, "error");
  }
}

async function reloadDishes() {
  try {
    const [dishes, summary] = await Promise.all([
      api("/api/dishes?include_unavailable=1"),
      api(`/api/admin/summary${summaryQuery()}`),
    ]);
    state.dishes = dishes;
    state.dishNames = new Map(dishes.map((d) => [d.id, d.name]));
    renderDishes();
    renderStats(summary);
  } catch (err) {
    setMessage(els.adminMessage, err.message, "error");
  }
}

async function reloadVenues() {
  try {
    const venues = await api("/api/venues");
    state.venues = venues;
    state.venueNames = new Map(venues.map((v) => [v.id, v.name]));
    const selected = els.dishVenue.value;
    fillSelect(els.dishVenue, venues, "id", "name", null, selected);
    renderVenues();
    setMessage(els.venueListMessage, "");
  } catch (err) {
    setMessage(els.venueListMessage, err.message, "error");
  }
}

function setDishEditing(on) {
  els.dishId.readOnly = on;
  els.dishId.classList.toggle("readonly", on);
  els.dishEditingNote.classList.toggle("hidden", !on);
  els.dishFormTitle.textContent = on ? "编辑菜品" : "添加 / 修改菜品";
  els.dishFormHint.textContent = on ? "保存后按 ID 覆盖" : "按 ID 覆盖";
  els.addDishBtn.textContent = on ? "更新菜品" : "保存菜品";
}

function resetDishForm() {
  state.editingDish = null;
  els.dishId.value = "";
  els.dishName.value = "";
  els.dishPrice.value = "12";
  els.dishCategory.value = "RICE";
  els.dishSource.value = "DEMO";
  els.dishTags.value = "";
  els.dishDesc.value = "";
  els.dishAvailable.checked = true;
  els.dishVenue.selectedIndex = 0;
  setDishEditing(false);
  setMessage(els.dishMessage, "");
}

function fillDishForm(dish) {
  state.editingDish = dish;
  els.dishId.value = dish.id;
  els.dishName.value = dish.name;
  els.dishVenue.value = dish.venue_id;
  els.dishCategory.value = dish.category;
  els.dishPrice.value = String(dish.price_fen / 100);
  els.dishSource.value = dish.source;
  els.dishTags.value = dish.tags.join(", ");
  els.dishDesc.value = dish.description;
  els.dishAvailable.checked = dish.available;
  setDishEditing(true);
  els.dishEditingName.textContent = `${dish.name}（${dish.id}）`;
  setMessage(els.dishMessage, "");
  els.dishId.scrollIntoView({ behavior: "smooth", block: "center" });
}

function setVenueEditing(on) {
  els.venueId.readOnly = on;
  els.venueId.classList.toggle("readonly", on);
  els.venueEditingNote.classList.toggle("hidden", !on);
  els.venueFormTitle.textContent = on ? "编辑窗口" : "添加 / 修改窗口";
  els.venueFormHint.textContent = on ? "保存后按 ID 覆盖" : "按 ID 覆盖";
  els.addVenueBtn.textContent = on ? "更新窗口" : "保存窗口";
}

function resetVenueForm() {
  state.editingVenue = null;
  els.venueId.value = "";
  els.venueName.value = "";
  els.venueKind.value = "CANTEEN";
  els.venueLocation.value = "";
  els.venueTags.value = "";
  if (els.venueCampus.options.length) els.venueCampus.selectedIndex = 0;
  for (const box of document.querySelectorAll(".period")) {
    box.checked = box.value === "LUNCH" || box.value === "DINNER";
  }
  setVenueEditing(false);
  setMessage(els.venueMessage, "");
}

function fillVenueForm(venue) {
  state.editingVenue = venue;
  els.venueId.value = venue.id;
  els.venueName.value = venue.name;
  els.venueCampus.value = venue.campus_id;
  els.venueKind.value = venue.kind;
  els.venueLocation.value = venue.location;
  els.venueTags.value = venue.tags.join(", ");
  for (const box of document.querySelectorAll(".period")) {
    box.checked = venue.open_periods.includes(box.value);
  }
  setVenueEditing(true);
  els.venueEditingName.textContent = `${venue.name}（${venue.id}）`;
  setMessage(els.venueMessage, "");
  els.venueId.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function toggleDish(dish) {
  if (!needOperator(els.adminMessage)) return;
  try {
    await api(`/api/admin/dishes/${encodeURIComponent(dish.id)}/availability`, {
      method: "POST",
      body: { available: !dish.available, operator: operator() },
    });
    setMessage(els.adminMessage, `${dish.name} 已${dish.available ? "下架" : "上架"}`, "ok");
    await reloadDishes();
  } catch (err) {
    setMessage(els.adminMessage, err.message, "error");
  }
}

async function saveDish() {
  setMessage(els.dishMessage, "");
  if (!needOperator(els.dishMessage)) return;
  if (!els.dishId.value.trim() || !els.dishName.value.trim()) {
    setMessage(els.dishMessage, "菜品 ID 和菜名不能为空", "error");
    return;
  }
  if (!els.dishVenue.value) {
    setMessage(els.dishMessage, "请先选择所在窗口 / 食堂", "error");
    return;
  }
  const priceYuan = Number(els.dishPrice.value);
  if (!Number.isFinite(priceYuan) || priceYuan < 0 || priceYuan > 1000) {
    setMessage(els.dishMessage, "价格需要在 0–1000 元之间", "error");
    return;
  }
  const payload = {
    id: els.dishId.value.trim(),
    venue_id: els.dishVenue.value,
    name: els.dishName.value.trim(),
    category: els.dishCategory.value,
    price_fen: Math.round(priceYuan * 100),
    tags: parseTags(els.dishTags.value),
    description: els.dishDesc.value.trim(),
    available: els.dishAvailable.checked,
    source: els.dishSource.value,
  };
  try {
    await api("/api/admin/dishes", { method: "POST", body: payload });
    const wasEditing = Boolean(state.editingDish);
    resetDishForm();
    setMessage(els.dishMessage, wasEditing ? "菜品已更新" : "菜品已添加", "ok");
    await reloadDishes();
  } catch (err) {
    setMessage(els.dishMessage, err.message, "error");
  }
}

async function saveVenue() {
  setMessage(els.venueMessage, "");
  if (!needOperator(els.venueMessage)) return;
  if (!els.venueId.value.trim() || !els.venueName.value.trim()) {
    setMessage(els.venueMessage, "窗口 ID 和名称不能为空", "error");
    return;
  }
  const periods = [...document.querySelectorAll(".period:checked")].map((b) => b.value);
  if (!periods.length) {
    setMessage(els.venueMessage, "至少选择一个营业时段", "error");
    return;
  }
  const payload = {
    id: els.venueId.value.trim(),
    campus_id: els.venueCampus.value,
    name: els.venueName.value.trim(),
    kind: els.venueKind.value,
    location: els.venueLocation.value.trim(),
    open_periods: periods,
    tags: parseTags(els.venueTags.value),
    available: state.editingVenue ? state.editingVenue.available : true,
  };
  try {
    await api("/api/admin/venues", { method: "POST", body: payload });
    const wasEditing = Boolean(state.editingVenue);
    resetVenueForm();
    setMessage(els.venueMessage, wasEditing ? "窗口已更新" : "窗口已添加", "ok");
    await reloadVenues();
    await reloadDishes();
  } catch (err) {
    setMessage(els.venueMessage, err.message, "error");
  }
}

async function deleteReview(review) {
  if (!needOperator(els.reviewMessage)) return;
  try {
    await api(`/api/admin/reviews/${review.review_id}/delete`, {
      method: "POST",
      body: { operator: operator() },
    });
    setMessage(els.reviewMessage, "评价已删除", "ok");
    renderReviews(await api("/api/admin/reviews?limit=30"));
    await reloadDishes();
  } catch (err) {
    setMessage(els.reviewMessage, err.message, "error");
  }
}

async function refreshReviews() {
  try {
    renderReviews(await api("/api/admin/reviews?limit=30"));
    setMessage(els.reviewMessage, "");
  } catch (err) {
    setMessage(els.reviewMessage, err.message, "error");
  }
}

function loadOperator() {
  try {
    const saved = localStorage.getItem(OPERATOR_KEY);
    if (saved) els.operator.value = saved;
  } catch { /* 隐私模式 */ }
}

function saveOperator() {
  try { localStorage.setItem(OPERATOR_KEY, els.operator.value); } catch { /* 忽略 */ }
}

els.addDishBtn.addEventListener("click", saveDish);
els.addVenueBtn.addEventListener("click", saveVenue);
$("#resetDishBtn").addEventListener("click", resetDishForm);
$("#cancelDishEdit").addEventListener("click", resetDishForm);
$("#resetVenueBtn").addEventListener("click", resetVenueForm);
$("#cancelVenueEdit").addEventListener("click", resetVenueForm);
$("#refreshDishes").addEventListener("click", () => reloadDishes());
$("#refreshVenues").addEventListener("click", async () => {
  await reloadVenues();
  await reloadDishes();
});
$("#refreshReviews").addEventListener("click", refreshReviews);
$("#refreshStats").addEventListener("click", loadSummary);
els.statCampus.addEventListener("change", loadSummary);
els.statRange.addEventListener("change", loadSummary);
els.operator.addEventListener("input", saveOperator);

loadOperator();
loadAll();
