"""全组共用的数据结构。负责人：C（后端 / 数据结构）。

约定：
- 金额一律整数“分”（*_fen），界面负责格式化成“元”。
- 时间一律 epoch 毫秒（*_ms / *_at）。
- 主键一律稳定的英文 ID（"nh_main"、"tomato_egg"），不用中文名做主键。
- 实体都是不可变的（frozen），要修改用 dataclasses.replace() 生成新对象。
- 集合字段（tags、open_periods、options……）用 tuple；JSON 里是数组，
  Repository 读回时必须还原成 tuple，否则相等比较会失败。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (DecisionMode, DishCategory, DishSource, MealPeriod,
                    VenueKind, VoteStatus)


# ---------- 校区 / 就餐点 / 菜品 ----------

@dataclass(frozen=True)
class Campus:
    id: str
    name: str
    aliases: tuple[str, ...] = ()       # 口语叫法，搜索用


@dataclass(frozen=True)
class Venue:
    """一个能吃饭的地方：食堂、档口、外卖商家。"""
    id: str
    campus_id: str
    name: str
    kind: VenueKind
    location: str = ""                                   # “东院·一楼”“南湖校区周边”
    open_periods: tuple[MealPeriod, ...] = (MealPeriod.LUNCH, MealPeriod.DINNER)
    tags: tuple[str, ...] = ()
    available: bool = True                               # False = 暂停营业 / 假期歇业


@dataclass(frozen=True)
class Dish:
    """一道具体的菜 / 套餐。price_fen 是整数分。"""
    id: str
    venue_id: str
    name: str
    category: DishCategory
    price_fen: int
    tags: tuple[str, ...] = ()          # “辣”“清淡”“素”“招牌”……
    description: str = ""
    available: bool = True              # False = 售罄 / 今日不做
    source: DishSource = DishSource.DEMO
    updated_at: int = 0                 # 最近一次维护时间


# ---------- 评价 ----------

@dataclass(frozen=True)
class Review:
    review_id: int
    dish_id: str
    rating: int                          # 1–5
    comment: str
    author: str                          # 昵称，不做账号体系
    created_at: int


@dataclass(frozen=True)
class RatingSummary:
    dish_id: str
    count: int
    average: float                       # 无评价时为 0.0
    histogram: dict[int, int]            # {1: 0, 2: 1, ...}，1–5 都有键


@dataclass(frozen=True)
class DishOption:
    """抽签时的一个候选：菜品 + 它所在的地点 + 当前评分。"""
    dish: Dish
    venue: Venue
    campus: Campus
    rating: RatingSummary
    recent: bool = False                 # 最近 N 天是否已经吃过


@dataclass(frozen=True)
class DishDetail:
    dish: Dish
    venue: Venue
    campus: Campus
    rating: RatingSummary
    reviews: tuple[Review, ...] = ()


# ---------- 决策 ----------

@dataclass(frozen=True)
class DecisionFilters:
    campus_id: str | None = None
    venue_ids: tuple[str, ...] = ()
    kinds: tuple[VenueKind, ...] = ()
    meal_period: MealPeriod | None = None
    max_price_fen: int | None = None
    categories: tuple[DishCategory, ...] = ()
    include_tags: tuple[str, ...] = ()       # 必须同时包含这些标签
    exclude_tags: tuple[str, ...] = ()       # 包含任一标签就排除（如“辣”）
    exclude_dish_ids: tuple[str, ...] = ()   # 明确不想再看到的菜（“再抽一次”）
    exclude_recent: bool = True              # 跳过最近 recent_days 天吃过的
    recent_days: int = 7


@dataclass(frozen=True)
class Decision:
    decision_id: str
    dish_id: str
    venue_id: str
    mode: DecisionMode
    created_at: int


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    winner: DishOption
    alternatives: tuple[DishOption, ...]
    reason: str                               # 给用户看的“为什么抽到它”


@dataclass(frozen=True)
class HistoryEntry:
    decision: Decision
    dish: Dish
    venue: Venue
    campus: Campus


# ---------- 投票 ----------

@dataclass(frozen=True)
class VoteOption:
    """投票选项。前端可以把食堂 / 菜品 / 外卖店包装成任意选项。"""
    option_id: str
    label: str


@dataclass(frozen=True)
class VoteRoom:
    code: str                                # 6 位分享码
    title: str
    options: tuple[VoteOption, ...]
    creator: str
    created_at: int
    closes_at: int
    status: VoteStatus = VoteStatus.OPEN


@dataclass(frozen=True)
class VoteBallot:
    room_code: str
    voter_token: str                         # 前端生成并存在 localStorage 的匿名编号
    option_id: str
    created_at: int


@dataclass(frozen=True)
class VoteTally:
    option_id: str
    label: str
    count: int


@dataclass(frozen=True)
class VoteResult:
    room: VoteRoom
    tallies: tuple[VoteTally, ...]
    total_votes: int
    winners: tuple[str, ...]                 # 票数最高的选项 ID，可能多个（平票）
    tie: bool


# ---------- 统计 ----------

@dataclass(frozen=True)
class TopDish:
    dish_id: str
    label: str                               # “番茄炒蛋盖饭 · 东院食堂”
    count: int


@dataclass(frozen=True)
class StatsSummary:
    campus_id: str | None
    since_ms: int
    until_ms: int
    decision_count: int
    vote_room_count: int
    ballot_count: int
    top_dishes: tuple[TopDish, ...]
    by_campus: dict[str, int]
    by_category: dict[str, int]
    avg_rating: float
    review_count: int
