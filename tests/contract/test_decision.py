"""DecisionService 契约测试。负责人：B（技术负责人，兼后端开发）。"""
from __future__ import annotations

import pytest

from campus_eats.model import (CampusError, DecisionFilters, DecisionMode,
                               DishCategory, ErrorCode, MealPeriod)

COMPONENT = "decision"

SINGLE_MILK_TEA = DecisionFilters(campus_id="nh", venue_ids=("nh_takeout",),
                                  categories=(DishCategory.DRINK,))


def test_candidates_respect_filters(system):
    options = system.decision.candidates(DecisionFilters(campus_id="nh"))
    assert options
    assert all(o.venue.campus_id == "nh" and o.campus.id == "nh" for o in options)


def test_candidates_respect_price_and_tags(system):
    cheap = system.decision.candidates(DecisionFilters(max_price_fen=1000))
    assert cheap and all(o.dish.price_fen <= 1000 for o in cheap)

    no_spicy = system.decision.candidates(DecisionFilters(exclude_tags=("辣",)))
    assert no_spicy
    assert all("辣" not in o.dish.tags for o in no_spicy)

    veggie = system.decision.candidates(DecisionFilters(include_tags=("素",)))
    assert veggie and all({"素"} <= set(o.dish.tags) for o in veggie)


def test_candidates_respect_meal_period(system):
    options = system.decision.candidates(
        DecisionFilters(campus_id="nh", meal_period=MealPeriod.BREAKFAST))
    assert {o.venue.id for o in options} == {"nh_main"}


def test_no_candidate(system):
    with pytest.raises(CampusError) as exc:
        system.decision.candidates(DecisionFilters(include_tags=("不存在的标签",)))
    assert exc.value.code == ErrorCode.NO_CANDIDATE


def test_decide_and_history(system):
    filters = DecisionFilters(campus_id="ms")
    candidates = system.decision.candidates(filters)
    result = system.decision.decide(filters)

    assert result.winner in candidates
    assert result.decision.dish_id == result.winner.dish.id
    assert result.decision.venue_id == result.winner.venue.id
    assert len(result.alternatives) == 2
    assert len({o.dish.id for o in result.alternatives}) == 2
    assert result.winner.dish.id not in {o.dish.id for o in result.alternatives}
    assert result.reason

    history = system.decision.history(limit=10)
    assert history[0].decision.decision_id == result.decision.decision_id
    assert history[0].dish.name == result.winner.dish.name


def test_fallback_when_everything_is_recent(system):
    first = system.decision.decide(SINGLE_MILK_TEA)
    assert first.winner.dish.id == "nh_takeout_milk_tea"

    for _ in range(2):
        again = system.decision.decide(SINGLE_MILK_TEA)
        assert again.winner.dish.id == "nh_takeout_milk_tea"
        assert "最近都吃过了" in again.reason


def test_exclude_recent_can_be_turned_off(system):
    system.decision.decide(SINGLE_MILK_TEA)
    options = system.decision.candidates(
        DecisionFilters(campus_id="nh", venue_ids=("nh_takeout",),
                        categories=(DishCategory.DRINK,), exclude_recent=False))
    assert len(options) == 1 and options[0].recent is True


def test_exclude_specific_dish(system):
    filters = DecisionFilters(campus_id="nh", venue_ids=("nh_takeout",),
                              categories=(DishCategory.DRINK,),
                              exclude_dish_ids=("nh_takeout_milk_tea",))
    with pytest.raises(CampusError) as exc:
        system.decision.decide(filters)
    assert exc.value.code == ErrorCode.NO_CANDIDATE


def test_mode_is_persisted(system):
    filters = DecisionFilters(campus_id="ms", venue_ids=("ms_west",))
    result = system.decision.decide(filters, mode=DecisionMode.LOTTERY)
    assert result.decision.mode == DecisionMode.LOTTERY
    assert system.decision.history(limit=1)[0].decision.mode == DecisionMode.LOTTERY


def test_history_limit_validation(system):
    with pytest.raises(CampusError) as exc:
        system.decision.history(limit=0)
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_unknown_campus(system):
    with pytest.raises(CampusError) as exc:
        system.decision.candidates(DecisionFilters(campus_id="nope"))
    assert exc.value.code == ErrorCode.INVALID_FILTER
