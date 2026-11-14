"""HTTP 接口层。负责人：A（项目 / 产品负责人，兼 UI 与文档）。

这一层只做三件事：解析请求 → 调服务 → 把结果转成 JSON。不写业务规则。
接口清单与示例见 docs/04-接口契约.md 第 3 节；验收标准是 tests/api/test_api.py。

错误统一返回：HTTP 状态码 + {"error": {"code": "...", "message": "...", "details": {...}}}
"""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Flask, jsonify, request, send_from_directory

from campus_eats.model import (CampusError, DecisionMode, DishCategory,
                               ErrorCode, MealPeriod, VenueKind)
from campus_eats.model.errors import HTTP_STATUS
from campus_eats.model.serialize import (dish_from_dict, filters_from_dict,
                                         to_jsonable, venue_from_dict,
                                         vote_options_from_list)
from campus_eats.wiring import System

STATIC_DIR = Path(__file__).parent / "static"


def ok(obj, status=200):
    return jsonify(to_jsonable(obj)), status


def body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, "请求体必须是 JSON 对象")
    return data


def int_arg(name: str, default=None):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{name} 必须是整数") from None


def enum_arg(cls, raw, name):
    try:
        return cls(raw)
    except (ValueError, TypeError):
        allowed = ", ".join(x.value for x in cls)
        raise CampusError(ErrorCode.INVALID_ARGUMENT,
                          f"{name} 取值不正确，可选 {allowed}") from None


def enum_list_arg(cls, name: str, single: str | None = None) -> tuple:
    raw = request.args.getlist(name)
    if single:
        raw += [x for chunk in request.args.getlist(single) for x in chunk.split(",")]
    return tuple(enum_arg(cls, x, name) for x in raw if x)


def bool_arg(name: str, default: bool = False) -> bool:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{name} 只接受 true / false")


def create_app(system: System) -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    app.json.ensure_ascii = False
    api = Blueprint("api", __name__, url_prefix="/api")
    s = system

    @app.errorhandler(CampusError)
    def on_campus_error(e: CampusError):
        return jsonify({"error": e.to_dict()}), HTTP_STATUS[e.code]

    @app.errorhandler(404)
    def on_404(e):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "没有这个地址"}}), 404

    @app.errorhandler(405)
    def on_405(e):
        return jsonify({"error": {"code": "INVALID_ARGUMENT",
                                  "message": "请求方法不对"}}), 405

    # ---------------- 页面 ----------------
    @app.get("/")
    def index_page():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/admin")
    def admin_page():
        return send_from_directory(STATIC_DIR, "admin.html")

    @app.get("/vote/<code>")
    def vote_page(code):
        return send_from_directory(STATIC_DIR, "vote.html")

    # ---------------- 元数据 ----------------
    @api.get("/meta")
    def meta():
        dishes = s.catalog.list_dishes(include_unavailable=True)
        tags = sorted({tag for dish in dishes for tag in dish.tags})
        categories = sorted({dish.category.value for dish in dishes})
        return ok({
            "campuses": s.catalog.list_campuses(),
            "venue_kinds": [x.value for x in VenueKind],
            "meal_periods": [x.value for x in MealPeriod],
            "categories": categories,
            "tags": tags,
        })

    @api.get("/campuses")
    def campuses():
        return ok(s.catalog.list_campuses())

    # ---------------- 地点与菜品 ----------------
    @api.get("/venues")
    def venues():
        return ok(s.catalog.list_venues(
            campus_id=request.args.get("campus_id") or None,
            kinds=enum_list_arg(VenueKind, "kind", "kinds") or None,
            meal_period=(enum_arg(MealPeriod, request.args.get("meal_period"),
                                  "meal_period")
                         if request.args.get("meal_period") else None),
        ))

    @api.get("/dishes")
    def dishes():
        category = request.args.get("category")
        return ok(s.catalog.list_dishes(
            venue_id=request.args.get("venue_id") or None,
            category=enum_arg(DishCategory, category, "category") if category else None,
            keyword=request.args.get("q") or None,
            include_unavailable=bool_arg("include_unavailable"),
        ))

    @api.get("/dishes/<dish_id>")
    def dish_detail(dish_id):
        return ok(s.catalog.dish_detail(dish_id))

    @api.get("/dishes/<dish_id>/rating")
    def dish_rating(dish_id):
        return ok(s.reviews.summary(dish_id))

    # ---------------- 决策 ----------------
    @api.post("/decisions")
    def decide():
        data = body()
        mode = (data.get("mode") or "WHEEL")
        return ok(s.decision.decide(filters_from_dict(data.get("filters")),
                                    enum_arg(DecisionMode, mode, "mode")), 201)

    @api.get("/decisions")
    def history():
        return ok(s.decision.history(int_arg("limit", 20)))

    # ---------------- 评价 ----------------
    @api.post("/reviews")
    def add_review():
        data = body()
        return ok(s.reviews.add_review(data.get("dish_id", ""), data.get("rating"),
                                       data.get("comment", ""), data.get("author", "")),
                  201)

    @api.get("/reviews")
    def list_reviews():
        dish_id = request.args.get("dish_id")
        if dish_id:
            return ok(s.reviews.list_reviews(dish_id, int_arg("limit", 20)))
        return ok(s.reviews.list_recent(int_arg("limit", 20)))

    # ---------------- 投票 ----------------
    @api.post("/votes")
    def create_vote():
        data = body()
        minutes = data.get("minutes", 30)
        if isinstance(minutes, bool) or not isinstance(minutes, int):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "minutes 必须是整数")
        return ok(s.vote.create_room(data.get("title", ""),
                                     vote_options_from_list(data.get("options")),
                                     minutes * 60_000, data.get("creator", "")), 201)

    @api.get("/votes/<code>")
    def get_vote(code):
        return ok(s.vote.get_room(code))

    @api.post("/votes/<code>/ballots")
    def cast_ballot(code):
        data = body()
        return ok(s.vote.cast_vote(code, data.get("voter_token", ""),
                                   data.get("option_id", "")))

    @api.post("/votes/<code>/close")
    def close_vote(code):
        return ok(s.vote.close_room(code, body().get("operator", "")))

    @api.get("/rooms")
    def rooms():
        return ok(s.vote.list_rooms(int_arg("limit", 20)))

    # ---------------- 管理后台 ----------------
    @api.get("/admin/summary")
    def admin_summary():
        return ok(s.stats.summary(request.args.get("campus_id") or None,
                                  int_arg("since_ms"), int_arg("until_ms")))

    @api.get("/admin/popular")
    def admin_popular():
        return ok(s.stats.popular_dishes(int_arg("limit", 10),
                                         request.args.get("campus_id") or None))

    @api.post("/admin/dishes")
    def upsert_dish():
        return ok(s.catalog.upsert_dish(dish_from_dict(body())), 201)

    @api.post("/admin/venues")
    def upsert_venue():
        return ok(s.catalog.upsert_venue(venue_from_dict(body())), 201)

    @api.post("/admin/dishes/<dish_id>/availability")
    def set_availability(dish_id):
        data = body()
        available = data.get("available")
        if not isinstance(available, bool):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "available 必须是布尔值")
        return ok(s.catalog.set_dish_availability(dish_id, available,
                                                  data.get("operator", "")))

    @api.get("/admin/reviews")
    def admin_reviews():
        return ok(s.reviews.list_recent(int_arg("limit", 30)))

    @api.post("/admin/reviews/<int:review_id>/delete")
    def delete_review(review_id):
        return ok(s.reviews.delete_review(review_id, body().get("operator", "")))

    app.register_blueprint(api)
    return app
