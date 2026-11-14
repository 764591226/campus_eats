"""评价系统的正式实现。负责人：E（测试 / 运维，兼评价模块开发）。

TODO(E)：把每个方法里的 NotImplementedError 换成实现。
契约见 docs/04-接口契约.md，验收标准是 tests/contract/test_review.py。
重点：
- 同一作者 + 同一道菜 + 同一自然日（北京时间）只能评一次；
- 平均分四舍五入保留 1 位小数；histogram 的 1–5 五个键都要有；
- 删除评价要检查 operator，返回被删的那条。
"""
from __future__ import annotations

from campus_eats.model import RatingSummary, Review
from campus_eats.review.interfaces import ReviewService


class ReviewServiceImpl(ReviewService):

    def __init__(self, repo, clock):
        self.repo = repo
        self.clock = clock

    def add_review(self, dish_id: str, rating: int, comment: str,
                   author: str) -> Review:
        raise NotImplementedError

    def list_reviews(self, dish_id: str, limit: int = 20) -> list[Review]:
        raise NotImplementedError

    def list_recent(self, limit: int = 20) -> list[Review]:
        raise NotImplementedError

    def summary(self, dish_id: str) -> RatingSummary:
        raise NotImplementedError

    def delete_review(self, review_id: int, operator: str) -> Review:
        raise NotImplementedError
