"""组装：决定每个组件用正式实现还是参考实现。负责人：B（技术负责人）。

    build(real={"catalog", "stats"})   # 只有数据管理和统计用正式实现，其余用参考实现

每个人都可以“只把自己的模块换成正式实现”，在完整程序里看效果：
    python run.py --real decision
"""
from __future__ import annotations

from dataclasses import dataclass

from campus_eats.model import Clock, Repository, SystemClock, seed

COMPONENTS = ("repository", "catalog", "reviews", "decision", "vote", "stats")
OWNERS = {
    "repository": "C 后端",
    "catalog": "C 后端",
    "stats": "C 后端",
    "reviews": "E 测试/运维",
    "decision": "B 技术负责人",
    "vote": "B 技术负责人",
}


@dataclass
class System:
    clock: Clock
    repo: Repository
    reviews: object
    catalog: object
    decision: object
    vote: object
    stats: object
    real: frozenset[str]


def build(real=frozenset(), *, db_path: str = "data/campus_eats.db",
          clock: Clock | None = None, rng=None) -> System:
    from campus_eats.catalog.catalog_service import CatalogServiceImpl, StatsServiceImpl
    from campus_eats.decision.decision_service import (DecisionServiceImpl,
                                                       VoteServiceImpl)
    from campus_eats.model.repository import SqliteRepository
    from campus_eats.review.review_service import ReviewServiceImpl
    from campus_eats.testing import reference as ref

    real = frozenset(real)
    unknown = real - set(COMPONENTS)
    if unknown:
        raise ValueError(f"未知组件：{', '.join(sorted(unknown))}；可选 {', '.join(COMPONENTS)}")

    clock = clock or SystemClock()

    repo = SqliteRepository(db_path) if "repository" in real else ref.MemoryRepository()
    repo.initialize(seed.CAMPUSES, seed.VENUES, seed.DISHES, seed.REVIEWS)

    reviews = (ReviewServiceImpl if "reviews" in real else ref.RefReviewService)(repo, clock)
    catalog = (CatalogServiceImpl if "catalog" in real else ref.RefCatalogService)(
        repo, reviews, clock)
    decision = (DecisionServiceImpl if "decision" in real else ref.RefDecisionService)(
        repo, catalog, clock, rng)
    vote = (VoteServiceImpl if "vote" in real else ref.RefVoteService)(
        repo, clock, rng)
    stats = (StatsServiceImpl if "stats" in real else ref.RefStatsService)(
        repo, catalog, clock)
    return System(clock, repo, reviews, catalog, decision, vote, stats, real)
