"""数据管理与统计的接口。负责人：C（后端 / 数据结构）。

改动任何方法签名或行为约定，必须先在组里讨论，并同步修改 docs/04-接口契约.md 和契约测试。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from campus_eats.model import (Campus, Dish, DishCategory, DishDetail,
                               MealPeriod, StatsSummary, TopDish, Venue,
                               VenueKind)


class CatalogService(ABC):
    """数据管理：校区、食堂 / 窗口 / 外卖、菜品，以及管理后台的增改。"""

    # ----- 查询（所有人可用） -----
    @abstractmethod
    def list_campuses(self) -> list[Campus]: ...

    @abstractmethod
    def list_venues(self, campus_id: str | None = None,
                    kinds: tuple[VenueKind, ...] | None = None,
                    meal_period: MealPeriod | None = None) -> list[Venue]:
        """只返回 available=True 的就餐点；meal_period 表示“当前时段营业”。
        campus_id 不存在 → INVALID_FILTER。"""

    @abstractmethod
    def get_venue(self, venue_id: str) -> Venue:
        """不存在 → NOT_FOUND。"""

    @abstractmethod
    def list_dishes(self, venue_id: str | None = None,
                    category: DishCategory | None = None,
                    keyword: str | None = None,
                    include_unavailable: bool = False) -> list[Dish]:
        """默认只返回 available=True 的菜；keyword 匹配菜名 / 描述 / 标签（忽略大小写）。"""

    @abstractmethod
    def get_dish(self, dish_id: str) -> Dish:
        """不存在 → NOT_FOUND。"""

    @abstractmethod
    def dish_detail(self, dish_id: str) -> DishDetail:
        """菜品 + 地点 + 校区 + 评分汇总 + 最近 10 条评价。"""

    # ----- 管理后台 -----
    @abstractmethod
    def upsert_venue(self, data: Mapping[str, Any]) -> Venue:
        """新增或修改就餐点（按 id）。data 字段见 docs/04-接口契约.md。
        校验：id / name 非空，campus 存在，open_periods 非空。"""

    @abstractmethod
    def upsert_dish(self, dish: Dish) -> Dish:
        """新增或修改菜品（按 id）。校验：name 非空，venue 存在，
        price_fen 在 0–100000 之间；保存时 updated_at 设成当前时间。
        校验失败 → INVALID_ARGUMENT。"""

    @abstractmethod
    def set_dish_availability(self, dish_id: str, available: bool,
                              operator: str) -> Dish:
        """售罄 / 恢复上架。operator 不能为空；菜品不存在 → NOT_FOUND。"""


class StatsService(ABC):
    """数据看板：只读，不修改任何数据。"""

    @abstractmethod
    def summary(self, campus_id: str | None = None, since_ms: int | None = None,
                until_ms: int | None = None) -> StatsSummary:
        """决策次数、投票参与、热门菜、按校区 / 分类分布、平均评分。
        campus_id 只过滤决策与评价（投票选项不绑定校区）。
        since 含、until 不含；None 分别表示 0 和“当前时间”。
        campus_id 不存在 → INVALID_FILTER；since > until → INVALID_FILTER。"""

    @abstractmethod
    def popular_dishes(self, limit: int = 10,
                       campus_id: str | None = None) -> list[TopDish]:
        """全时间段的热门菜（按被抽中次数降序，同次数按 label 升序）。"""
