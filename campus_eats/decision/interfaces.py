"""决策与投票的接口。负责人：B（技术负责人，兼后端开发）。

改动任何方法签名或行为约定，必须先在组里讨论，并同步修改 docs/04-接口契约.md 和契约测试。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from campus_eats.model import (DecisionFilters, DecisionMode, DecisionResult,
                               DishOption, HistoryEntry, VoteOption, VoteResult,
                               VoteRoom)


class DecisionService(ABC):
    """“今天吃什么”：筛选候选 → 加权随机 → 记录历史。"""

    @abstractmethod
    def candidates(self, filters: DecisionFilters) -> list[DishOption]:
        """按 filters 返回候选（已排除不可售 / 不符合条件 / 最近吃过的）。
        filters.exclude_recent=True 时 recent=True 的候选会被排除；
        排除后为空但本来有候选 → 不报错，返回全部候选（由 decide() 做兜底）。
        完全没有候选 → NO_CANDIDATE。"""

    @abstractmethod
    def decide(self, filters: DecisionFilters,
               mode: DecisionMode = DecisionMode.WHEEL) -> DecisionResult:
        """加权随机抽一个，返回 winner + 最多 2 个备选，并写入决策历史。

        权重 = 20 + round(平均评分 × 10) + min(近 30 天被抽中次数, 30)；
        无评分按 0 算。备选从剩余候选里按同样权重重抽，不重复。
        如果候选全部是“最近吃过”的，则忽略 recent 限制兜底，并在 reason 里说明。
        """

    @abstractmethod
    def history(self, limit: int = 20) -> list[HistoryEntry]:
        """决策历史，最新在前。菜品 / 地点被删掉的历史记录跳过。"""


class VoteService(ABC):
    """群体投票：发起房间 → 分享 6 位码 → 每人一票（可改票）→ 结果。"""

    @abstractmethod
    def create_room(self, title: str, options: tuple[VoteOption, ...],
                    closes_in_ms: int, creator: str) -> VoteRoom:
        """校验：title 1–40 字；options 2–8 个且 option_id 不重复、label 1–30 字；
        closes_in_ms 在 1 分钟到 7 天之间；creator 1–20 字。
        生成不与已有房间重复的 6 位分享码。"""

    @abstractmethod
    def get_room(self, code: str) -> VoteResult:
        """查询房间和实时结果。房间不存在 → NOT_FOUND；
        超过 closes_at 自动置为 CLOSED。"""

    @abstractmethod
    def cast_vote(self, code: str, voter_token: str, option_id: str) -> VoteResult:
        """投票。voter_token 8–64 字；同一 token 再投是“改票”，覆盖旧选择。
        房间已截止 → INVALID_STATE；选项不存在 → INVALID_ARGUMENT。"""

    @abstractmethod
    def close_room(self, code: str, operator: str) -> VoteResult:
        """手动结束投票。operator 不能为空；已结束 → INVALID_STATE。"""

    @abstractmethod
    def list_rooms(self, limit: int = 20) -> list[VoteRoom]:
        """最近的房间（管理后台 / 首页入口用）。"""
