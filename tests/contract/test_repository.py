"""Repository 契约测试。负责人：C（后端 / 数据结构）。

参考实现（内存）和正式实现（SQLite）都要通过；正式实现从 NotImplementedError 开始。
"""
from __future__ import annotations

from campus_eats.model import (Decision, DecisionMode, Dish, DishCategory,
                               Review, VoteBallot, VoteOption, VoteRoom,
                               VoteStatus)
from campus_eats.wiring import build

COMPONENT = "repository"


def test_seed_catalog(system):
    repo = system.repo
    assert [c.id for c in repo.list_campuses()] == ["ms", "nh"]
    assert len(repo.list_venues()) == 4
    assert len(repo.list_venues(campus_id="nh")) == 2
    assert len(repo.list_dishes()) == 12
    assert repo.get_dish("ms_east_tomato_egg").name == "番茄炒蛋盖饭"
    assert repo.get_dish("no_such_dish") is None


def test_save_and_get_dish(system):
    repo = system.repo
    dish = Dish("tmp_dish", "nh_main", "临时菜", DishCategory.RICE, 1111,
                ("测试",), "只在测试里存在")
    repo.save_dish(dish)
    assert repo.get_dish("tmp_dish") == dish
    assert repo.get_dish("tmp_dish") in repo.list_dishes(venue_id="nh_main")


def test_reviews_are_newest_first(system):
    repo = system.repo
    first = repo.list_reviews(dish_id="ms_east_tomato_egg")
    assert len(first) == 1 and first[0].review_id == 1
    newer = repo.add_review("ms_east_tomato_egg", 3, "一般", "测试同学", 1_762_000_999_000)
    assert newer.review_id > 1
    rows = repo.list_reviews(dish_id="ms_east_tomato_egg")
    assert [r.review_id for r in rows][0] == newer.review_id
    assert len(repo.list_reviews(dish_id="ms_east_tomato_egg", limit=1)) == 1
    assert repo.get_review(newer.review_id) == newer
    repo.delete_review(newer.review_id)
    assert repo.get_review(newer.review_id) is None


def test_review_equal_roundtrip(system):
    repo = system.repo
    review = repo.add_review("nh_main_sour_noodle", 4, "酸辣够劲", "回锅同学",
                             1_762_000_888_000)
    assert repo.get_review(review.review_id) == review


def test_decisions_are_newest_first(system):
    repo = system.repo
    repo.save_decision(Decision("D1", "nh_main_sour_noodle", "nh_main",
                                DecisionMode.WHEEL, 1000))
    repo.save_decision(Decision("D2", "ms_east_tomato_egg", "ms_east",
                                DecisionMode.LOTTERY, 2000))
    rows = repo.list_decisions()
    assert [d.decision_id for d in rows] == ["D2", "D1"]
    assert [d.decision_id for d in repo.list_decisions(since_ms=1500)] == ["D2"]
    assert len(repo.list_decisions(limit=1)) == 1


def test_vote_room_and_ballot_upsert(system):
    repo = system.repo
    room = VoteRoom("ABC234", "聚餐", (VoteOption("a", "一食堂"),
                                       VoteOption("b", "二食堂")),
                    "发起人", 1000, 2000, VoteStatus.OPEN)
    repo.save_vote_room(room)
    assert repo.get_vote_room("ABC234") == room
    assert repo.get_vote_room("NOPE") is None
    repo.save_ballot(VoteBallot("ABC234", "token-aaaa", "a", 1100))
    repo.save_ballot(VoteBallot("ABC234", "token-aaaa", "b", 1200))
    ballots = repo.list_ballots("ABC234")
    assert len(ballots) == 1
    assert ballots[0].option_id == "b"
    assert repo.list_vote_rooms() == [room]


def test_data_survives_restart(tmp_path, clock):
    """正式实现专用：同一个 SQLite 文件重新 build 后数据还在。"""
    db = str(tmp_path / "persist.db")
    first = build({"repository"}, db_path=db, clock=clock)
    first.repo.save_dish(Dish("persist_dish", "ms_east", "持久菜",
                              DishCategory.OTHER, 500))
    first.repo.add_review("persist_dish", 5, "重启后还在", "持久同学", clock.now_ms())
    second = build({"repository"}, db_path=db, clock=clock)
    assert second.repo.get_dish("persist_dish").name == "持久菜"
    assert second.repo.list_reviews(dish_id="persist_dish")[0].rating == 5


def test_missing_campus_is_none(system):
    assert system.repo.get_campus("nope") is None
    assert system.repo.get_venue("nope") is None


def test_get_missing_review_is_none(system):
    assert system.repo.get_review(99999) is None
