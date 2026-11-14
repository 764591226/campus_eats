"""VoteService 契约测试。负责人：B（技术负责人，兼后端开发）。"""
from __future__ import annotations

import pytest

from campus_eats.model import CampusError, ErrorCode, VoteOption, VoteStatus
from tests.helpers import options

COMPONENT = "vote"
MINUTE = 60_000


def make_room(system, closes_in_ms=30 * MINUTE):
    return system.vote.create_room(
        "周五聚餐去哪", options(("a", "一食堂"), ("b", "二食堂"), ("c", "外卖")),
        closes_in_ms, "发起人")


def test_create_and_get_room(system):
    room = make_room(system)
    assert len(room.code) == 6
    assert room.status == VoteStatus.OPEN
    state = system.vote.get_room(room.code)
    assert state.total_votes == 0
    assert state.winners == () and state.tie is False
    assert [t.count for t in state.tallies] == [0, 0, 0]
    assert [t.label for t in state.tallies] == ["一食堂", "二食堂", "外卖"]


def test_cast_vote_and_change_vote(system):
    room = make_room(system)
    first = system.vote.cast_vote(room.code, "token-aaaa", "a")
    assert first.total_votes == 1
    assert first.tallies[0].count == 1

    changed = system.vote.cast_vote(room.code, "token-aaaa", "b")
    assert changed.total_votes == 1
    assert changed.tallies[0].count == 0
    assert changed.tallies[1].count == 1


def test_tie(system):
    room = make_room(system)
    system.vote.cast_vote(room.code, "token-aaaa", "a")
    state = system.vote.cast_vote(room.code, "token-bbbb", "b")
    assert state.total_votes == 2
    assert state.tie is True
    assert set(state.winners) == {"a", "b"}


def test_manual_close(system):
    room = make_room(system)
    state = system.vote.close_room(room.code, "管理员")
    assert state.room.status == VoteStatus.CLOSED
    with pytest.raises(CampusError) as exc:
        system.vote.cast_vote(room.code, "token-aaaa", "a")
    assert exc.value.code == ErrorCode.INVALID_STATE
    with pytest.raises(CampusError) as exc:
        system.vote.close_room(room.code, "管理员")
    assert exc.value.code == ErrorCode.INVALID_STATE


def test_auto_close(system):
    room = make_room(system, closes_in_ms=MINUTE)
    system.clock.advance(MINUTE)
    state = system.vote.get_room(room.code)
    assert state.room.status == VoteStatus.CLOSED
    with pytest.raises(CampusError) as exc:
        system.vote.cast_vote(room.code, "token-aaaa", "a")
    assert exc.value.code == ErrorCode.INVALID_STATE


def test_validation(system):
    cases = [
        ("", options(("a", "A"), ("b", "B")), 1000, "发起人"),
        ("标题", options(("a", "A")), 1000, "发起人"),
        ("标题", options(("a", "A"), ("a", "B")), 1000, "发起人"),
        ("标题", options(("a", "A"), ("b", "B")), 0, "发起人"),
        ("标题", options(("a", "A"), ("b", "B")), 8 * 24 * 60 * MINUTE, "发起人"),
        ("标题", options(("a", "A"), ("b", "B")), 1000, ""),
    ]
    for title, opts, closes, creator in cases:
        with pytest.raises(CampusError) as exc:
            system.vote.create_room(title, opts, closes, creator)
        assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_invalid_token_and_option(system):
    room = make_room(system)
    with pytest.raises(CampusError) as exc:
        system.vote.cast_vote(room.code, "short", "a")
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT
    with pytest.raises(CampusError) as exc:
        system.vote.cast_vote(room.code, "token-aaaa", "nope")
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


def test_unknown_room(system):
    with pytest.raises(CampusError) as exc:
        system.vote.get_room("NOPE22")
    assert exc.value.code == ErrorCode.NOT_FOUND


def test_list_rooms(system):
    room = make_room(system)
    rooms = system.vote.list_rooms(limit=5)
    assert [r.code for r in rooms] == [room.code]
