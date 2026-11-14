/* 管理后台：看板、菜品上下架、新增菜品 / 窗口、评价管理。负责人：A（产品 / UI）。 */
const $ = (sel) => document.querySelector(sel);

const state = {
  campuses: [],
  venues: [],
  dishes: [],
  venueNames: new Map(),
  dishNames: new Map(),
};

const els = {
  operator: $("#operator"),
  statDecisions: $("#statDecisions"),
  statReviews: $("#statReviews"),
  statRating: $("#statRating"),
  statRooms: $("#statRooms"),
  statBallots: $("#statBallots"),
  topDishes: $("#topDishes"),
  dishesBody: $("#dishesBody"),
  reviews: $("#adminReviews"),
  adminMessage: $("#adminMessage"),
  reviewMessage: $("#reviewMessage"),
  dishMessage: $("#dishMessage"),
  venueMessage: $("#venueMessage"),
  dishId: $("#dishId"), dishName: $("#dishName"), dishVenue: $("#dishVenue"),
  dishCategory: $("#dishCategory"), dishPrice: $("#dishPrice"),
  dishSource: $("#dishSource"), dishTags: $("#dishTags"), dishDesc: $("#dishDesc"),
  dishAvailable: $("#dishAvailable"),
  venueId: $("#venueId"), venueName: $("#venueName"), venueCampus: $("#venueCampus"),
  venueKind: $("#venueKind"), venueLocation: $("#venueLocation"), venueTags: $("#venueTags"),
};

function operator() {
  return els.operator.value.trim();
}

function needOperator(messageEl) {
  if (!operator()) {
    setMessage(messageEl, "请先在左边填写操作人昵称", "error");
    return false;
  }
  return true;
}

function parseTags(text) {
  return text.split(/[,，、]/).map((s) => s.trim()).filter(Boolean);
}

function fillSelect(select, rows, valueKey, labelKey, placeholder = null) {
  clear(select);
  if (placeholder) {
    const opt = el("option", null, placeholder);
    opt.value = "";
    select.appendChild(opt);
  }
  for (const row of rows) {
    const opt = el("option", null, row[labelKey]);
    opt.value = row[valueKey];
    select.appendChild(opt);
  }
}

function renderStats(summary) {
  els.statDecisions.textContent = summary.decision_count;
  els.statReviews.textContent = summary.review_count;
  els.statRating.textContent = summary.review_count ? summary.avg_rating.toFixed(1) : "—";
  els.statRooms.textContent = summary.vote_room_count;
  els.statBallots.textContent = summary.ballot_count;

  clear(els.topDishes);
  if (!summary.top_dishes.length) {
    els.topDishes.appendChild(el("p", "hint", "还没有抽签数据。"));
    return;
  }
  for (const row of summary.top_dishes) {
    const line = el("div", "top-row");
    line.appendChild(el("strong", null, row.label));
    line.appendChild(el("span", null, `${row.count} 次`));
    els.topDishes.appendChild(line);
  }
}

function renderDishes() {
  clear(els.dishesBody);
  for (const dish of state.dishes) {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, dish.name));
    tr.appendChild(el("td", null, state.venueNames.get(dish.venue_id) || dish.venue_id));
    tr.appendChild(el("td", null, yen(dish.price_fen)));
    tr.appendChild(el("td", null, CATEGORY_LABELS[dish.category] || dish.category));
    tr.appendChild(el("td", null, dish.source));

    const status = el("td");
    status.appendChild(el("span",
      `badge ${dish.available ? "badge-green" : "badge-danger"}`,
      dish.available ? "在售" : "已下架"));
    tr.appendChild(status);

    const actions = el("td", "table-actions");
    const toggle = el("button", `btn btn-small ${dish.available ? "btn-danger" : ""}`,
      dish.available ? "下架" : "上架");
    toggle.type = "button";
    toggle.addEventListener("click", () => toggleDish(dish));
    actions.appendChild(toggle);
    tr.appendChild(actions);
    els.dishesBody.appendChild(tr);
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

async function loadAll() {
  try {
    const [meta, venues, dishes, summary, reviews] = await Promise.all([
      api("/api/meta"),
      api("/api/venues"),
      api("/api/dishes?include_unavailable=1"),
      api("/api/admin/summary"),
      api("/api/admin/reviews?limit=30"),
    ]);
    state.campuses = meta.campuses;
    state.venues = venues;
    state.dishes = dishes;
    state.venueNames = new Map(venues.map((v) => [v.id, v.name]));
    state.dishNames = new Map(dishes.map((d) => [d.id, d.name]));

    fillSelect(els.dishVenue, venues, "id", "name");
    fillSelect(els.venueCampus, meta.campuses, "id", "name");
    renderStats(summary);
    renderDishes();
    renderReviews(reviews);
  } catch (err) {
    setMessage(els.adminMessage, err.message, "error");
  }
}

async function reloadDishes() {
  const [dishes, summary] = await Promise.all([
    api("/api/dishes?include_unavailable=1"),
    api("/api/admin/summary"),
  ]);
  state.dishes = dishes;
  state.dishNames = new Map(dishes.map((d) => [d.id, d.name]));
  renderDishes();
  renderStats(summary);
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

async function addDish() {
  setMessage(els.dishMessage, "");
  if (!needOperator(els.dishMessage)) return;
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
    setMessage(els.dishMessage, "已保存", "ok");
    els.dishId.value = "";
    els.dishName.value = "";
    els.dishTags.value = "";
    els.dishDesc.value = "";
    await reloadDishes();
  } catch (err) {
    setMessage(els.dishMessage, err.message, "error");
  }
}

async function addVenue() {
  setMessage(els.venueMessage, "");
  if (!needOperator(els.venueMessage)) return;
  const checked = [...document.querySelectorAll(".period:checked")].map((b) => b.value);
  if (!checked.length) {
    setMessage(els.venueMessage, "至少选择一个营业时段", "error");
    return;
  }
  const payload = {
    id: els.venueId.value.trim(),
    campus_id: els.venueCampus.value,
    name: els.venueName.value.trim(),
    kind: els.venueKind.value,
    location: els.venueLocation.value.trim(),
    open_periods: checked,
    tags: parseTags(els.venueTags.value),
  };
  try {
    await api("/api/admin/venues", { method: "POST", body: payload });
    setMessage(els.venueMessage, "已保存", "ok");
    els.venueId.value = "";
    els.venueName.value = "";
    els.venueLocation.value = "";
    els.venueTags.value = "";
    const venues = await api("/api/venues");
    state.venues = venues;
    state.venueNames = new Map(venues.map((v) => [v.id, v.name]));
    fillSelect(els.dishVenue, venues, "id", "name");
    renderDishes();
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
    const reviews = await api("/api/admin/reviews?limit=30");
    renderReviews(reviews);
    await reloadDishes();
  } catch (err) {
    setMessage(els.reviewMessage, err.message, "error");
  }
}

async function refreshReviews() {
  try {
    renderReviews(await api("/api/admin/reviews?limit=30"));
    setMessage(els.reviewMessage, "", "");
  } catch (err) {
    setMessage(els.reviewMessage, err.message, "error");
  }
}

$("#addDishBtn").addEventListener("click", addDish);
$("#addVenueBtn").addEventListener("click", addVenue);
$("#refreshDishes").addEventListener("click", () => reloadDishes().catch(
  (err) => setMessage(els.adminMessage, err.message, "error")));
$("#refreshReviews").addEventListener("click", refreshReviews);

loadAll();
