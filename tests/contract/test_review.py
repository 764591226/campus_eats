"""ReviewService 契约测试。负责人：E（测试 / 运维，兼评价模块）。"""
from __future__ import annotations

import pytest

from campus_eats.model import CampusError, ErrorCode, seed

COMPONENT = "reviews"
DAY_MS = 24 * 60 * 60 * 1000


def test_initial_summary(system):
    summary = system.reviews.summary("ms_east_tomato_egg")
    assert summary.count == 1
    assert summary.average == 5.0
    assert summary.histogram == {1: 0, 2: 0, 3: 0, 4: 0, 5: 1}


def test_add_review_and_summary(system):
    review = system.reviews.add_review("ms_east_tomato_egg", 3, "有点咸",
                                       "新同学")
    assert review.review_id > 0
    assert review.created_at == system.clock.now_ms()
    summary = system.reviews.summary("ms_east_tomato_egg")
    assert summary.count == 2
    assert summary.average == 4.0
    assert summary.histogram[3] == 1


@pytest.mark.parametrize("rating", [0, 6, -1, True, "5", 4.5])
def test_invalid_rating(system, rating):
    with pytest.raises(CampusError) as exc:
        system.reviews.add_review("ms_east_tomato_egg", rating, "", "测试同学")
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


@pytest.mark.parametrize("author", ["", "   ", "超" * (seed.REVIEW_MAX_AUTHOR + 1)])
def test_invalid_author(system, author):
    with pytest.raises(CampusError) as exc:
        system.reviews.add_review("ms_east_tomato_egg", 5, "", author)
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_comment_too_long(system):
    with pytest.raises(CampusError) as exc:
        system.reviews.add_review("ms_east_tomato_egg", 5,
                                  "长" * (seed.REVIEW_MAX_COMMENT + 1), "测试同学")
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_same_author_same_dish_same_day_is_limited(system):
    system.reviews.add_review("ms_east_tomato_egg", 5, "第一次", "重复同学")
    with pytest.raises(CampusError) as exc:
        system.reviews.add_review("ms_east_tomato_egg", 4, "第二次", "重复同学")
    assert exc.value.code == ErrorCode.RATE_LIMITED
    # 隔一天就可以再评
    system.clock.advance(DAY_MS)
    again = system.reviews.add_review("ms_east_tomato_egg", 4, "第二天", "重复同学")
    assert again.rating == 4


def test_different_dish_same_day_is_allowed(system):
    system.reviews.add_review("ms_east_tomato_egg", 5, "好吃", "多菜同学")
    second = system.reviews.add_review("ms_east_braised_chicken", 4, "也行",
                                       "多菜同学")
    assert second.dish_id == "ms_east_braised_chicken"


def test_list_reviews_and_recent(system):
    rows = system.reviews.list_reviews("ms_east_tomato_egg")
    assert len(rows) == 1
    assert rows[0].dish_id == "ms_east_tomato_egg"
    system.reviews.add_review("nh_main_sour_noodle", 4, "够酸", "测试同学")
    assert system.reviews.list_recent(limit=1)[0].dish_id == "nh_main_sour_noodle"
    with pytest.raises(CampusError) as exc:
        system.reviews.list_reviews("nope")
    assert exc.value.code == ErrorCode.NOT_FOUND


def test_delete_review(system):
    review = system.reviews.add_review("nh_main_sour_noodle", 5, "待删除",
                                       "测试同学")
    deleted = system.reviews.delete_review(review.review_id, "管理员")
    assert deleted.review_id == review.review_id
    assert all(r.review_id != review.review_id
               for r in system.reviews.list_recent(limit=100))
    with pytest.raises(CampusError) as exc:
        system.reviews.delete_review(review.review_id, "管理员")
    assert exc.value.code == ErrorCode.NOT_FOUND
    with pytest.raises(CampusError) as exc:
        system.reviews.delete_review(1, " ")
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_summary_for_unreviewed_dish(system):
    summary = system.reviews.summary("nh_takeout_burger")
    assert summary.count == 0
    assert summary.average == 0.0
    assert summary.histogram == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
