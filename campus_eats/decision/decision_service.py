"""决策与投票的正式实现。负责人：B（技术负责人，兼后端开发）。

TODO(B)：把每个方法里的 NotImplementedError 换成实现。
契约见 docs/04-接口契约.md 与 docs/03-详细设计.md，验收标准是
tests/contract/test_decision.py、test_vote.py。

重点：
- DecisionService：筛选管线 → 最近 N 天去重 → 加权随机（权重公式在 03 号文档 §5）；
  全部“最近吃过”时兜底，不报错；备选按同样权重重抽且不重复；结果落库。
- VoteService：房间状态机、分享码不重复、同一 token 改票覆盖、截止自动关闭、平票规则。
"""
from __future__ import annotations

import random

from campus_eats.decision.interfaces import DecisionService, VoteService
from campus_eats.model import (DecisionFilters, DecisionMode, DecisionResult,
                               DishOption, HistoryEntry, VoteOption, VoteResult,
                               VoteRoom)


class DecisionServiceImpl(DecisionService):

    def __init__(self, repo, catalog, clock, rng: random.Random | None = None):
        self.repo = repo
        self.catalog = catalog
        self.clock = clock
        self.rng = rng or random.Random()

    def candidates(self, filters: DecisionFilters) -> list[DishOption]:
        raise NotImplementedError

    def decide(self, filters: DecisionFilters,
               mode: DecisionMode = DecisionMode.WHEEL) -> DecisionResult:
        raise NotImplementedError

    def history(self, limit: int = 20) -> list[HistoryEntry]:
        raise NotImplementedError


class VoteServiceImpl(VoteService):

    def __init__(self, repo, clock, rng: random.Random | None = None):
        self.repo = repo
        self.clock = clock
        self.rng = rng or random.Random()

    def create_room(self, title: str, options: tuple[VoteOption, ...],
                    closes_in_ms: int, creator: str) -> VoteRoom:
        raise NotImplementedError

    def get_room(self, code: str) -> VoteResult:
        raise NotImplementedError

    def cast_vote(self, code: str, voter_token: str, option_id: str) -> VoteResult:
        raise NotImplementedError

    def close_room(self, code: str, operator: str) -> VoteResult:
        raise NotImplementedError

    def list_rooms(self, limit: int = 20) -> list[VoteRoom]:
        raise NotImplementedError
