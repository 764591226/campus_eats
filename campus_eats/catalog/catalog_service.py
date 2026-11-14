"""数据管理 + 统计的正式实现。负责人：C（后端 / 数据结构）。

TODO(C)：把每个方法里的 NotImplementedError 换成实现。
契约见 docs/04-接口契约.md，验收标准是 tests/contract/test_catalog.py、test_stats.py。
也可以对照 campus_eats/testing/reference.py 里的参考实现——它只差“数据存 SQLite”。
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from campus_eats.catalog.interfaces import CatalogService, StatsService
from campus_eats.model import (Campus, Dish, DishCategory, DishDetail,
                               MealPeriod, StatsSummary, TopDish, Venue,
                               VenueKind)


class CatalogServiceImpl(CatalogService):

    def __init__(self, repo, reviews, clock):
        self.repo = repo
        self.reviews = reviews
        self.clock = clock

    def list_campuses(self) -> list[Campus]:
        raise NotImplementedError

    def list_venues(self, campus_id: str | None = None,
                    kinds: tuple[VenueKind, ...] | None = None,
                    meal_period: MealPeriod | None = None) -> list[Venue]:
        raise NotImplementedError

    def get_venue(self, venue_id: str) -> Venue:
        raise NotImplementedError

    def list_dishes(self, venue_id: str | None = None,
                    category: DishCategory | None = None,
                    keyword: str | None = None,
                    include_unavailable: bool = False) -> list[Dish]:
        raise NotImplementedError

    def get_dish(self, dish_id: str) -> Dish:
        raise NotImplementedError

    def dish_detail(self, dish_id: str) -> DishDetail:
        raise NotImplementedError

    def upsert_venue(self, data: Mapping[str, Any]) -> Venue:
        raise NotImplementedError

    def upsert_dish(self, dish: Dish) -> Dish:
        raise NotImplementedError

    def set_dish_availability(self, dish_id: str, available: bool,
                              operator: str) -> Dish:
        raise NotImplementedError


class StatsServiceImpl(StatsService):

    def __init__(self, repo, catalog, clock):
        self.repo = repo
        self.catalog = catalog
        self.clock = clock

    def summary(self, campus_id: str | None = None, since_ms: int | None = None,
                until_ms: int | None = None) -> StatsSummary:
        raise NotImplementedError

    def popular_dishes(self, limit: int = 10,
                       campus_id: str | None = None) -> list[TopDish]:
        raise NotImplementedError
