"""数据访问接口。负责人：C（后端 / 数据结构）。

其他模块不直接写 SQL，只通过 Repository 读写数据。
Repository 只负责“存取”，不做业务判断（例如“价格是否合法”由 CatalogService 判断）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .entities import (Campus, Decision, Dish, Review, Venue, VoteBallot,
                       VoteRoom)


class Repository(ABC):

    # ----- 初始化 -----
    @abstractmethod
    def initialize(self, campuses: Iterable[Campus], venues: Iterable[Venue],
                   dishes: Iterable[Dish], reviews: Iterable[Review] = ()) -> None:
        """建表；若还没有任何校区数据，则写入给定的初始数据。可重复调用（幂等）。"""

    # ----- 校区 / 就餐点 / 菜品 -----
    @abstractmethod
    def list_campuses(self) -> list[Campus]:
        """按初始化顺序返回。"""

    @abstractmethod
    def get_campus(self, campus_id: str) -> Campus | None: ...

    @abstractmethod
    def list_venues(self, *, campus_id: str | None = None) -> list[Venue]:
        """按初始化顺序返回；campus_id 为 None 表示全部。"""

    @abstractmethod
    def get_venue(self, venue_id: str) -> Venue | None: ...

    @abstractmethod
    def save_venue(self, venue: Venue) -> None:
        """按 id 插入或覆盖。"""

    @abstractmethod
    def list_dishes(self, *, venue_id: str | None = None) -> list[Dish]:
        """按初始化顺序返回；venue_id 为 None 表示全部。"""

    @abstractmethod
    def get_dish(self, dish_id: str) -> Dish | None: ...

    @abstractmethod
    def save_dish(self, dish: Dish) -> None:
        """按 id 插入或覆盖。"""

    # ----- 评价 -----
    @abstractmethod
    def add_review(self, dish_id: str, rating: int, comment: str, author: str,
                   created_at: int) -> Review:
        """新增评价；review_id 从 1 开始自增。"""

    @abstractmethod
    def list_reviews(self, *, dish_id: str | None = None,
                     limit: int | None = None) -> list[Review]:
        """按 created_at 降序；时间相同按 review_id 降序。None 表示全部。"""

    @abstractmethod
    def get_review(self, review_id: int) -> Review | None: ...

    @abstractmethod
    def delete_review(self, review_id: int) -> None:
        """不存在时什么也不做。"""

    # ----- 决策历史 -----
    @abstractmethod
    def save_decision(self, decision: Decision) -> None: ...

    @abstractmethod
    def list_decisions(self, *, since_ms: int | None = None,
                       limit: int | None = None) -> list[Decision]:
        """按 created_at 降序；since_ms 含。None 表示不限。"""

    # ----- 投票 -----
    @abstractmethod
    def save_vote_room(self, room: VoteRoom) -> None:
        """按 code 插入或覆盖。"""

    @abstractmethod
    def get_vote_room(self, code: str) -> VoteRoom | None: ...

    @abstractmethod
    def list_vote_rooms(self, limit: int = 50) -> list[VoteRoom]:
        """按 created_at 降序。"""

    @abstractmethod
    def save_ballot(self, ballot: VoteBallot) -> None:
        """按 (room_code, voter_token) 插入或覆盖——同一个 token 改票时覆盖。"""

    @abstractmethod
    def list_ballots(self, room_code: str) -> list[VoteBallot]:
        """按 created_at 升序。"""


class SqliteRepository(Repository):
    """正式实现：SQLite。负责人：C（后端）。

    建表语句见 schema.sql。TODO(C)：实现全部方法。提示：
    - 用标准库 sqlite3；check_same_thread=False，并用一把 threading.Lock 保护写操作（Flask 多线程）。
    - tags / open_periods / options 这类嵌套字段可以存 JSON 字符串（见 serialize.py），
      读回时必须还原成 tuple / 枚举，保证读回对象与存入对象完全相等。
    - 数据文件路径由 wiring.build >> run.py --db 决定，默认 data/campus_eats.db。
    - reviews 的 review_id 用 INTEGER PRIMARY KEY AUTOINCREMENT；
      vote_ballots 用 (room_code, voter_token) 复合主键。
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def initialize(self, campuses, venues, dishes, reviews=()):
        raise NotImplementedError

    def list_campuses(self):
        raise NotImplementedError

    def get_campus(self, campus_id):
        raise NotImplementedError

    def list_venues(self, *, campus_id=None):
        raise NotImplementedError

    def get_venue(self, venue_id):
        raise NotImplementedError

    def save_venue(self, venue):
        raise NotImplementedError

    def list_dishes(self, *, venue_id=None):
        raise NotImplementedError

    def get_dish(self, dish_id):
        raise NotImplementedError

    def save_dish(self, dish):
        raise NotImplementedError

    def add_review(self, dish_id, rating, comment, author, created_at):
        raise NotImplementedError

    def list_reviews(self, *, dish_id=None, limit=None):
        raise NotImplementedError

    def get_review(self, review_id):
        raise NotImplementedError

    def delete_review(self, review_id):
        raise NotImplementedError

    def save_decision(self, decision):
        raise NotImplementedError

    def list_decisions(self, *, since_ms=None, limit=None):
        raise NotImplementedError

    def save_vote_room(self, room):
        raise NotImplementedError

    def get_vote_room(self, code):
        raise NotImplementedError

    def list_vote_rooms(self, limit=50):
        raise NotImplementedError

    def save_ballot(self, ballot):
        raise NotImplementedError

    def list_ballots(self, room_code):
        raise NotImplementedError
