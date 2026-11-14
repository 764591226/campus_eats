"""StatsService 契约测试。负责人：C（后端）。"""
from __future__ import annotations

import pytest

from campus_eats.model import CampusError, DecisionFilters, DishCategory, ErrorCode
from tests.helpers import options

COMPONENT = "stats"

SINGLE_TOMATO = DecisionFilters(campus_id="ms", venue_ids=("ms_east",),
                                categories=(DishCategory.RICE,),
                                exclude_tags=("微辣",))


def test_initial_summary(system):
    summary = system.stats.summary()
    assert summary.decision_count == 0
    assert summary.top_dishes == ()
    assert summary.review_count == 5
    assert summary.avg_rating == 4.2


def test_summary_counts_decisions(system):
    system.decision.decide(SINGLE_TOMATO)
    system.decision.decide(SINGLE_TOMATO)
    summary = system.stats.summary(campus_id="ms")
    assert summary.decision_count == 2
    assert summary.top_dishes[0].dish_id == "ms_east_tomato_egg"
    assert summary.top_dishes[0].count == 2
    assert summary.by_campus == {"ms": 2}
    assert summary.by_category == {"RICE": 2}


def test_summary_filters_campus(system):
    system.decision.decide(SINGLE_TOMATO)
    summary = system.stats.summary(campus_id="nh")
    assert summary.decision_count == 0
    assert summary.review_count == 1          # 只有外卖沙拉有评价
    assert summary.avg_rating == 3.0


def test_summary_time_range(system):
    system.decision.decide(SINGLE_TOMATO)
    system.clock.advance(1000)
    assert system.stats.summary(since_ms=system.clock.now_ms()).decision_count == 0
    assert system.stats.summary(until_ms=system.clock.now_ms()).decision_count == 1


def test_summary_votes(system):
    room = system.vote.create_room("吃什么", options(("a", "A"), ("b", "B")),
                                   600_000, "发起人")
    system.vote.cast_vote(room.code, "token-aaaa", "a")
    summary = system.stats.summary()
    assert summary.vote_room_count == 1
    assert summary.ballot_count == 1


def test_popular_dishes(system):
    system.decision.decide(SINGLE_TOMATO)
    top = system.stats.popular_dishes(limit=3)
    assert top[0].dish_id == "ms_east_tomato_egg"
    assert "东院食堂" in top[0].label


def test_invalid_summary_args(system):
    with pytest.raises(CampusError) as exc:
        system.stats.summary(campus_id="nope")
    assert exc.value.code == ErrorCode.INVALID_FILTER
    with pytest.raises(CampusError) as exc:
        system.stats.summary(since_ms=10_000, until_ms=5_000)
    assert exc.value.code == ErrorCode.INVALID_FILTER
