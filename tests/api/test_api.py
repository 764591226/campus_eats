"""HTTP 接口测试。负责人：A（项目 / 产品，兼 UI 与文档）。

后端用参考实现，验证 URL、请求 / 响应 JSON、错误映射。界面交互在 05 号文档 §5 手工验收。
"""
from __future__ import annotations

import pytest

from campus_eats.web.api import create_app

OWNER = "A 产品/UI"


@pytest.fixture
def client(ref_system):
    app = create_app(ref_system)
    app.testing = True
    return app.test_client()


def error_code(resp):
    return resp.get_json()["error"]["code"]


def test_meta(client):
    data = client.get("/api/meta").get_json()
    assert [c["id"] for c in data["campuses"]] == ["ms", "nh"]
    assert "辣" in data["tags"]
    assert "WHEEL" in [m for m in ("WHEEL", "LOTTERY")]
    assert data["meal_periods"] == ["BREAKFAST", "LUNCH", "DINNER", "LATE_NIGHT"]


def test_venues_and_filters(client):
    data = client.get("/api/venues?campus_id=nh").get_json()
    assert len(data) == 2
    data = client.get("/api/venues?kinds=TAKEOUT").get_json()
    assert [v["id"] for v in data] == ["nh_takeout"]
    data = client.get("/api/venues?meal_period=BREAKFAST").get_json()
    assert [v["id"] for v in data] == ["ms_east", "nh_main"]


def test_dishes_and_detail(client):
    data = client.get("/api/dishes?q=辣").get_json()
    assert data and all(any("辣" in tag for tag in d["tags"]) for d in data)
    detail = client.get("/api/dishes/ms_east_tomato_egg").get_json()
    assert detail["dish"]["name"] == "番茄炒蛋盖饭"
    assert detail["rating"]["count"] == 1
    assert detail["venue"]["name"] == "东院食堂"
    assert client.get("/api/dishes/nope").status_code == 404


def test_decide(client):
    resp = client.post("/api/decisions", json={
        "filters": {"campus_id": "nh", "categories": ["DRINK"]},
        "mode": "WHEEL",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["winner"]["dish"]["id"] == "nh_takeout_milk_tea"
    assert data["decision"]["mode"] == "WHEEL"
    assert data["reason"]
    history = client.get("/api/decisions?limit=5").get_json()
    assert history[0]["decision"]["decision_id"] == data["decision"]["decision_id"]


def test_decide_errors(client):
    resp = client.post("/api/decisions", json={"filters": {"campus_id": "nope"}})
    assert resp.status_code == 400
    assert error_code(resp) == "INVALID_FILTER"
    resp = client.post("/api/decisions", json={"filters": {"include_tags": ["没有"]}})
    assert resp.status_code == 409
    assert error_code(resp) == "NO_CANDIDATE"
    resp = client.post("/api/decisions", json={"filters": {}, "mode": "NOPE"})
    assert resp.status_code == 400


def test_reviews_endpoint(client):
    resp = client.post("/api/reviews", json={
        "dish_id": "nh_takeout_milk_tea", "rating": 5, "comment": "三分糖好喝",
        "author": "接口测试同学",
    })
    assert resp.status_code == 201
    review = resp.get_json()
    assert review["rating"] == 5
    rating = client.get("/api/dishes/nh_takeout_milk_tea/rating").get_json()
    assert rating["count"] == 1 and rating["average"] == 5.0
    again = client.post("/api/reviews", json={
        "dish_id": "nh_takeout_milk_tea", "rating": 4, "author": "接口测试同学"})
    assert again.status_code == 429
    assert error_code(again) == "RATE_LIMITED"


def test_vote_flow(client):
    resp = client.post("/api/votes", json={
        "title": "周五聚餐",
        "options": [{"option_id": "a", "label": "一食堂"},
                    {"option_id": "b", "label": "二食堂"}],
        "minutes": 30, "creator": "接口测试同学",
    })
    assert resp.status_code == 201
    code = resp.get_json()["code"]
    assert len(code) == 6

    state = client.get(f"/api/votes/{code}").get_json()
    assert state["total_votes"] == 0

    resp = client.post(f"/api/votes/{code}/ballots", json={
        "voter_token": "token-aaaa", "option_id": "a"})
    assert resp.get_json()["total_votes"] == 1

    resp = client.post(f"/api/votes/{code}/close", json={"operator": "接口测试同学"})
    assert resp.get_json()["room"]["status"] == "CLOSED"

    resp = client.post(f"/api/votes/{code}/ballots", json={
        "voter_token": "token-bbbb", "option_id": "b"})
    assert resp.status_code == 409
    assert client.get("/api/votes/ZZZZZZ").status_code == 404


def test_admin_endpoints(client):
    dish = {
        "id": "api_new_dish", "venue_id": "ms_east", "name": "接口新菜",
        "category": "RICE", "price_fen": 1234, "tags": ["测试"],
        "description": "管理后台新增", "source": "SURVEY",
    }
    resp = client.post("/api/admin/dishes", json=dish)
    assert resp.status_code == 201
    assert resp.get_json()["updated_at"] > 0

    resp = client.post("/api/admin/dishes/api_new_dish/availability",
                       json={"available": False, "operator": "管理员"})
    assert resp.get_json()["available"] is False
    public_ids = [d["id"] for d in client.get("/api/dishes?venue_id=ms_east").get_json()]
    assert "api_new_dish" not in public_ids
    all_ids = [d["id"] for d in client.get(
        "/api/dishes?venue_id=ms_east&include_unavailable=1").get_json()]
    assert "api_new_dish" in all_ids

    resp = client.post("/api/admin/venues", json={
        "id": "api_venue", "campus_id": "nh", "name": "接口窗口",
        "kind": "WINDOW", "location": "南湖·五楼",
        "open_periods": ["LUNCH"], "tags": ["测试"],
    })
    assert resp.status_code == 201

    summary = client.get("/api/admin/summary").get_json()
    assert summary["review_count"] == 5
    assert client.get("/api/admin/popular").status_code == 200


def test_admin_summary_filters(client, clock):
    resp = client.post("/api/decisions", json={
        "filters": {"campus_id": "nh", "categories": ["DRINK"]},
    })
    assert resp.status_code == 201

    nh = client.get("/api/admin/summary?campus_id=nh").get_json()
    assert nh["decision_count"] == 1
    ms = client.get("/api/admin/summary?campus_id=ms").get_json()
    assert ms["decision_count"] == 0
    future = clock.now_ms() + 1
    after = client.get(f"/api/admin/summary?since_ms={future}").get_json()
    assert after["decision_count"] == 0
    assert client.get("/api/admin/summary?campus_id=nope").status_code == 400


def test_admin_delete_review(client):
    resp = client.post("/api/reviews", json={
        "dish_id": "nh_main_sour_noodle", "rating": 3, "comment": "待删",
        "author": "待删同学"})
    review_id = resp.get_json()["review_id"]
    resp = client.post(f"/api/admin/reviews/{review_id}/delete",
                       json={"operator": "管理员"})
    assert resp.status_code == 200
    assert resp.get_json()["review_id"] == review_id
    assert client.post(f"/api/admin/reviews/{review_id}/delete",
                       json={"operator": "管理员"}).status_code == 404


def test_json_errors(client):
    assert client.get("/api/nope").status_code == 404
    assert client.post("/api/decisions", data="not json",
                       content_type="application/json").status_code == 400


def test_pages_are_served(client):
    for path in ("/", "/admin", "/vote/ABC234"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.content_type
