"""端到端集成测试。负责人：B（技术负责人）。

[reference] 参考实现全流程；
[real]      全组正式实现 —— 最终演示前必须全绿。
"""
from __future__ import annotations

from campus_eats.model import DecisionFilters, MealPeriod
from tests.helpers import options

ALL_REAL = True
OWNER = "B 技术负责人（集成）"


def test_full_flow(system):
    # 1. 抽签
    result = system.decision.decide(
        DecisionFilters(campus_id="nh", meal_period=MealPeriod.LUNCH))
    dish_id = result.winner.dish.id
    assert result.winner.campus.id == "nh"

    # 2. 评价这道菜
    review = system.reviews.add_review(dish_id, 5, "集成测试好吃", "集成同学")
    assert review.dish_id == dish_id
    assert system.reviews.summary(dish_id).count >= 1

    # 3. 发起投票并投票
    room = system.vote.create_room(
        "周五聚餐", options(("a", "一食堂"), ("b", "二食堂")),
        30 * 60_000, "集成同学")
    state = system.vote.cast_vote(room.code, "integration-token", "a")
    assert state.total_votes == 1
    assert state.winners == ("a",)

    # 4. 看板
    summary = system.stats.summary()
    assert summary.decision_count >= 1
    assert summary.vote_room_count == 1
    assert summary.ballot_count == 1
    assert summary.review_count >= 1
    assert any(row.dish_id == dish_id for row in summary.top_dishes)
