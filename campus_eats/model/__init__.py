"""全组共用的数据模型。负责人：C（后端 / 数据结构）。

其他模块统一从 `campus_eats.model` 导入实体、枚举和错误，不直接 import 子模块，
这样 C 以后调整文件拆分时不会影响别人。
"""
from . import seed
from .clock import Clock, FakeClock, SystemClock
from .entities import (Campus, Decision, DecisionFilters, DecisionResult,
                       Dish, DishDetail, DishOption, HistoryEntry, RatingSummary,
                       Review, StatsSummary, TopDish, Venue, VoteBallot,
                       VoteOption, VoteResult, VoteRoom, VoteTally)
from .enums import (DecisionMode, DishCategory, DishSource, MealPeriod,
                    VenueKind, VoteStatus)
from .errors import HTTP_STATUS, CampusError, ErrorCode
from .repository import Repository, SqliteRepository

__all__ = [
    "seed", "Clock", "FakeClock", "SystemClock",
    "Campus", "Decision", "DecisionFilters", "DecisionResult", "Dish", "DishDetail",
    "DishOption", "HistoryEntry", "RatingSummary", "Review", "StatsSummary", "TopDish",
    "Venue", "VoteBallot", "VoteOption", "VoteResult", "VoteRoom", "VoteTally",
    "DecisionMode", "DishCategory", "DishSource", "MealPeriod", "VenueKind", "VoteStatus",
    "HTTP_STATUS", "CampusError", "ErrorCode", "Repository", "SqliteRepository",
]
