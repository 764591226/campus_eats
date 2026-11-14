"""CatalogService / StatsService 契约测试。负责人：C（后端）。"""
from __future__ import annotations

import pytest

from campus_eats.model import (CampusError, Dish, DishCategory, ErrorCode,
                               MealPeriod, VenueKind)

COMPONENT = "catalog"

CAMPUSES = ("ms", "nh")


def ids(rows):
    return [row.id for row in rows]


def test_list_campuses(system):
    assert ids(system.catalog.list_campuses()) == list(CAMPUSES)


def test_list_venues_by_campus(system):
    assert ids(system.catalog.list_venues(campus_id="nh")) == [
        "nh_main", "nh_takeout"]


def test_list_venues_by_kind(system):
    assert ids(system.catalog.list_venues(kinds=(VenueKind.TAKEOUT,))) == ["nh_takeout"]
    assert set(ids(system.catalog.list_venues(kinds=(VenueKind.CANTEEN,)))) == {
        "ms_east", "ms_west", "nh_main"}


def test_list_venues_by_meal_period(system):
    breakfast = ids(system.catalog.list_venues(meal_period=MealPeriod.BREAKFAST))
    assert breakfast == ["ms_east", "nh_main"]
    late = ids(system.catalog.list_venues(meal_period=MealPeriod.LATE_NIGHT))
    assert late == ["nh_takeout"]


def test_unknown_campus_is_invalid_filter(system):
    with pytest.raises(CampusError) as exc:
        system.catalog.list_venues(campus_id="nope")
    assert exc.value.code == ErrorCode.INVALID_FILTER


def test_list_dishes_filters(system):
    dishes = system.catalog.list_dishes(venue_id="nh_main")
    assert len(dishes) == 3
    rice = system.catalog.list_dishes(category=DishCategory.RICE)
    assert rice and all(d.category == DishCategory.RICE for d in rice)
    spicy = system.catalog.list_dishes(keyword="辣")
    assert spicy and all(any("辣" in tag for tag in d.tags) for d in spicy)
    assert system.catalog.list_dishes(keyword="牛肉")[0].id == "ms_west_beef_noodle"
    with pytest.raises(CampusError) as exc:
        system.catalog.list_dishes(venue_id="nope")
    assert exc.value.code == ErrorCode.INVALID_FILTER


def test_dish_detail_includes_rating_and_reviews(system):
    detail = system.catalog.dish_detail("ms_east_tomato_egg")
    assert detail.dish.name == "番茄炒蛋盖饭"
    assert detail.venue.id == "ms_east"
    assert detail.campus.id == "ms"
    assert detail.rating.count == 1
    assert detail.rating.average == 5.0
    assert detail.reviews[0].author == "匿名同学1"


def test_upsert_dish(system):
    dish = Dish("new_dish", "ms_east", "新菜", DishCategory.RICE, 999,
                ("测试",), "管理后台添加")
    saved = system.catalog.upsert_dish(dish)
    assert saved.id == "new_dish"
    assert saved.updated_at == system.clock.now_ms()
    assert system.catalog.get_dish("new_dish").name == "新菜"


@pytest.mark.parametrize("price", [-1, 100_001])
def test_upsert_dish_rejects_bad_price(system, price):
    with pytest.raises(CampusError) as exc:
        system.catalog.upsert_dish(Dish("bad_dish", "ms_east", "坏菜",
                                        DishCategory.RICE, price))
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_upsert_dish_rejects_unknown_venue(system):
    with pytest.raises(CampusError) as exc:
        system.catalog.upsert_dish(Dish("bad_dish", "nope", "坏菜",
                                        DishCategory.RICE, 1000))
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_set_availability(system):
    saved = system.catalog.set_dish_availability("ms_east_soy_milk", False, "管理员A")
    assert saved.available is False
    assert "ms_east_soy_milk" not in ids(system.catalog.list_dishes(venue_id="ms_east"))
    assert "ms_east_soy_milk" in ids(system.catalog.list_dishes(
        venue_id="ms_east", include_unavailable=True))
    with pytest.raises(CampusError) as exc:
        system.catalog.set_dish_availability("ms_east_soy_milk", True, "")
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_upsert_venue(system):
    venue = system.catalog.upsert_venue({
        "id": "nh_new", "campus_id": "nh", "name": "新窗口",
        "kind": VenueKind.WINDOW, "location": "南湖·东侧",
        "open_periods": (MealPeriod.LUNCH,), "tags": ("测试",),
    })
    assert venue.id == "nh_new"
    assert "nh_new" in ids(system.catalog.list_venues(campus_id="nh"))
    with pytest.raises(CampusError) as exc:
        system.catalog.upsert_venue({"id": "bad", "campus_id": "nope",
                                     "name": "坏窗口", "kind": VenueKind.WINDOW,
                                     "open_periods": (MealPeriod.LUNCH,)})
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_get_missing_things(system):
    for call in (lambda: system.catalog.get_dish("nope"),
                 lambda: system.catalog.get_venue("nope"),
                 lambda: system.catalog.dish_detail("nope")):
        with pytest.raises(CampusError) as exc:
            call()
        assert exc.value.code == ErrorCode.NOT_FOUND
