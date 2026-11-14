"""评价系统的接口。负责人：E（测试 / 运维，兼评价模块开发）。

改动任何方法签名或行为约定，必须先在组里讨论，并同步修改 docs/04-接口契约.md 和契约测试。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from campus_eats.model import RatingSummary, Review


class ReviewService(ABC):
    """评分与评论。不做账号体系，作者只是昵称。"""

    @abstractmethod
    def add_review(self, dish_id: str, rating: int, comment: str, author: str) -> Review:
        """新增评价。规则：
        - 菜品不存在 → NOT_FOUND；
        - rating 必须是整数 1–5；
        - author 去掉首尾空格后 1–20 字；comment 可空，最多 200 字；
        - 同一作者对同一道菜，同一自然日（北京时间）只能评一次 → RATE_LIMITED。"""

    @abstractmethod
    def list_reviews(self, dish_id: str, limit: int = 20) -> list[Review]:
        """某道菜的评价，最新在前；菜品不存在 → NOT_FOUND。"""

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[Review]:
        """全站最新评价，给管理后台用。"""

    @abstractmethod
    def summary(self, dish_id: str) -> RatingSummary:
        """平均分、评价数、1–5 星分布（五个键都有，没有的为 0）。
        平均分保留 1 位小数；没有评价时 average=0.0、count=0。"""

    @abstractmethod
    def delete_review(self, review_id: int, operator: str) -> Review:
        """管理员删除评价。operator 不能为空；评价不存在 → NOT_FOUND。
        返回被删除的评价（便于界面提示和审计日志）。"""
