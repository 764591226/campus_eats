"""参考实现：全部接口的内存版本。

用途：
1. 证明契约测试本身是对的（参考实现必须 100% 通过）；
2. 队友的模块还没写完时，用参考实现顶上，让整个程序先跑起来（python run.py 默认就用它）；
3. 遇到“这个接口到底该怎么表现”的疑问时，可以读这里的代码。

正式实现不要 import 这个文件。区别：数据要存进 SQLite（经由 Repository），重启不丢。
"""
from __future__ import annotations

import dataclasses
import random
import secrets
import threading
from collections import Counter
from datetime import datetime, timedelta, timezone

from campus_eats.catalog.interfaces import CatalogService, StatsService
from campus_eats.decision.interfaces import DecisionService, VoteService
from campus_eats.model import (Campus, CampusError, Decision, DecisionFilters,
                               DecisionMode, DecisionResult, Dish, DishCategory,
                               DishDetail, DishOption, DishSource, ErrorCode,
                               HistoryEntry, MealPeriod, RatingSummary, Review,
                               StatsSummary, TopDish, Venue, VenueKind,
                               VoteBallot, VoteOption, VoteResult, VoteRoom,
                               VoteStatus, VoteTally)
from campus_eats.model import seed
from campus_eats.model.repository import Repository
from campus_eats.review.interfaces import ReviewService

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # 去掉容易混淆的 I O 0 1


# ====================================================================== 数据结构（C）

class MemoryRepository(Repository):

    def __init__(self):
        self._lock = threading.RLock()
        self._campuses: dict[str, Campus] = {}
        self._venues: dict[str, Venue] = {}
        self._dishes: dict[str, Dish] = {}
        self._reviews: dict[int, Review] = {}
        self._decisions: dict[str, Decision] = {}
        self._rooms: dict[str, VoteRoom] = {}
        self._ballots: dict[str, dict[str, VoteBallot]] = {}
        self._next_review_id = 1
        self._initialized = False

    def initialize(self, campuses, venues, dishes, reviews=()):
        with self._lock:
            if self._initialized:
                return
            self._campuses = {c.id: c for c in campuses}
            self._venues = {v.id: v for v in venues}
            self._dishes = {d.id: d for d in dishes}
            for review in reviews:
                self._reviews[review.review_id] = review
                self._next_review_id = max(self._next_review_id, review.review_id + 1)
            self._initialized = True

    def list_campuses(self):
        return list(self._campuses.values())

    def get_campus(self, campus_id):
        return self._campuses.get(campus_id)

    def list_venues(self, *, campus_id=None):
        with self._lock:
            return [v for v in self._venues.values()
                    if campus_id is None or v.campus_id == campus_id]

    def get_venue(self, venue_id):
        return self._venues.get(venue_id)

    def save_venue(self, venue):
        with self._lock:
            self._venues[venue.id] = venue

    def list_dishes(self, *, venue_id=None):
        with self._lock:
            return [d for d in self._dishes.values()
                    if venue_id is None or d.venue_id == venue_id]

    def get_dish(self, dish_id):
        return self._dishes.get(dish_id)

    def save_dish(self, dish):
        with self._lock:
            self._dishes[dish.id] = dish

    def add_review(self, dish_id, rating, comment, author, created_at):
        with self._lock:
            review = Review(self._next_review_id, dish_id, rating, comment, author,
                            created_at)
            self._next_review_id += 1
            self._reviews[review.review_id] = review
            return review

    def list_reviews(self, *, dish_id=None, limit=None):
        with self._lock:
            result = [r for r in self._reviews.values()
                      if dish_id is None or r.dish_id == dish_id]
        result.sort(key=lambda r: (r.created_at, r.review_id), reverse=True)
        return result[:limit] if limit is not None else result

    def get_review(self, review_id):
        return self._reviews.get(review_id)

    def delete_review(self, review_id):
        with self._lock:
            self._reviews.pop(review_id, None)

    def save_decision(self, decision):
        with self._lock:
            self._decisions[decision.decision_id] = decision

    def list_decisions(self, *, since_ms=None, limit=None):
        with self._lock:
            result = [d for d in self._decisions.values()
                      if since_ms is None or d.created_at >= since_ms]
        result.sort(key=lambda d: d.created_at, reverse=True)
        return result[:limit] if limit is not None else result

    def save_vote_room(self, room):
        with self._lock:
            self._rooms[room.code] = room

    def get_vote_room(self, code):
        return self._rooms.get(code)

    def list_vote_rooms(self, limit=50):
        with self._lock:
            result = sorted(self._rooms.values(), key=lambda r: r.created_at,
                            reverse=True)
        return result[:limit]

    def save_ballot(self, ballot):
        with self._lock:
            self._ballots.setdefault(ballot.room_code, {})[ballot.voter_token] = ballot

    def list_ballots(self, room_code):
        with self._lock:
            ballots = list(self._ballots.get(room_code, {}).values())
        return sorted(ballots, key=lambda b: b.created_at)


# ====================================================================== 评价（E）

class RefReviewService(ReviewService):

    def __init__(self, repo, clock):
        self.repo = repo
        self.clock = clock

    def _date(self, ms: int):
        tz = timezone(timedelta(hours=seed.TZ_OFFSET_HOURS))
        return datetime.fromtimestamp(ms / 1000, tz).date()

    def _need_dish(self, dish_id: str) -> Dish:
        dish = self.repo.get_dish(dish_id)
        if dish is None:
            raise CampusError(ErrorCode.NOT_FOUND, f"没有这道菜：{dish_id}")
        return dish

    def add_review(self, dish_id, rating, comment, author):
        self._need_dish(dish_id)
        if isinstance(rating, bool) or not isinstance(rating, int) \
                or not seed.RATING_MIN <= rating <= seed.RATING_MAX:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "评分必须是 1–5 的整数")
        if not isinstance(author, str):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "昵称必须是字符串")
        author = author.strip()
        if not 1 <= len(author) <= seed.REVIEW_MAX_AUTHOR:
            raise CampusError(ErrorCode.INVALID_ARGUMENT,
                              f"昵称需要 1–{seed.REVIEW_MAX_AUTHOR} 个字")
        if comment is None:
            comment = ""
        if not isinstance(comment, str):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "评论必须是字符串")
        comment = comment.strip()
        if len(comment) > seed.REVIEW_MAX_COMMENT:
            raise CampusError(ErrorCode.INVALID_ARGUMENT,
                              f"评论不能超过 {seed.REVIEW_MAX_COMMENT} 个字")

        now = self.clock.now_ms()
        today = self._date(now)
        for old in self.repo.list_reviews(dish_id=dish_id):
            if old.author == author and self._date(old.created_at) == today:
                raise CampusError(ErrorCode.RATE_LIMITED,
                                  "今天已经评价过这道菜了，明天再来吧",
                                  dish_id=dish_id)
        return self.repo.add_review(dish_id, rating, comment, author, now)

    def list_reviews(self, dish_id, limit=20):
        self._need_dish(dish_id)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "limit 需要是 1–100 的整数")
        return self.repo.list_reviews(dish_id=dish_id, limit=limit)

    def list_recent(self, limit=20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "limit 需要是 1–100 的整数")
        return self.repo.list_reviews(limit=limit)

    def summary(self, dish_id):
        self._need_dish(dish_id)
        reviews = self.repo.list_reviews(dish_id=dish_id)
        histogram = {n: 0 for n in range(seed.RATING_MIN, seed.RATING_MAX + 1)}
        for review in reviews:
            histogram[review.rating] += 1
        average = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0.0
        return RatingSummary(dish_id, len(reviews), average, histogram)

    def delete_review(self, review_id, operator):
        if isinstance(review_id, bool) or not isinstance(review_id, int):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "review_id 必须是整数")
        if not isinstance(operator, str) or not operator.strip():
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "请填写操作人")
        review = self.repo.get_review(review_id)
        if review is None:
            raise CampusError(ErrorCode.NOT_FOUND, f"没有这条评价：{review_id}")
        self.repo.delete_review(review_id)
        return review


# ====================================================================== 数据管理（C）

class RefCatalogService(CatalogService):

    def __init__(self, repo, reviews, clock):
        self.repo = repo
        self.reviews = reviews
        self.clock = clock

    def _campus(self, campus_id: str) -> Campus:
        campus = self.repo.get_campus(campus_id)
        if campus is None:
            raise CampusError(ErrorCode.INVALID_FILTER, f"没有这个校区：{campus_id}")
        return campus

    def _venue(self, venue_id: str) -> Venue:
        venue = self.repo.get_venue(venue_id)
        if venue is None:
            raise CampusError(ErrorCode.NOT_FOUND, f"没有这个就餐点：{venue_id}")
        return venue

    def _dish(self, dish_id: str) -> Dish:
        dish = self.repo.get_dish(dish_id)
        if dish is None:
            raise CampusError(ErrorCode.NOT_FOUND, f"没有这道菜：{dish_id}")
        return dish

    def list_campuses(self):
        return self.repo.list_campuses()

    def list_venues(self, campus_id=None, kinds=None, meal_period=None):
        if campus_id is not None:
            self._campus(campus_id)
        if meal_period is not None and not isinstance(meal_period, MealPeriod):
            raise CampusError(ErrorCode.INVALID_FILTER, "meal_period 取值不正确")
        kinds = tuple(kinds or ())
        result = []
        for venue in self.repo.list_venues(campus_id=campus_id):
            if not venue.available:
                continue
            if kinds and venue.kind not in kinds:
                continue
            if meal_period is not None and meal_period not in venue.open_periods:
                continue
            result.append(venue)
        return result

    def get_venue(self, venue_id):
        return self._venue(venue_id)

    def list_dishes(self, venue_id=None, category=None, keyword=None,
                    include_unavailable=False):
        if venue_id is not None:
            venue = self.repo.get_venue(venue_id)
            if venue is None:
                raise CampusError(ErrorCode.INVALID_FILTER, f"没有这个就餐点：{venue_id}")
        if category is not None and not isinstance(category, DishCategory):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "category 取值不正确")
        needle = keyword.strip().lower() if isinstance(keyword, str) else ""
        result = []
        for dish in self.repo.list_dishes(venue_id=venue_id):
            if not include_unavailable and not dish.available:
                continue
            if category is not None and dish.category != category:
                continue
            if needle:
                haystack = " ".join((dish.name, dish.description) + dish.tags).lower()
                if needle not in haystack:
                    continue
            result.append(dish)
        return result

    def get_dish(self, dish_id):
        return self._dish(dish_id)

    def dish_detail(self, dish_id):
        dish = self._dish(dish_id)
        venue = self._venue(dish.venue_id)
        campus = self.repo.get_campus(venue.campus_id)
        if campus is None:
            raise CampusError(ErrorCode.NOT_FOUND, "这道菜所在的校区不存在")
        return DishDetail(dish, venue, campus, self.reviews.summary(dish_id),
                          tuple(self.reviews.list_reviews(dish_id, limit=10)))

    def upsert_venue(self, data):
        required = ("id", "campus_id", "name", "kind")
        missing = [k for k in required if not data.get(k)]
        if missing:
            raise CampusError(ErrorCode.INVALID_ARGUMENT,
                              "缺少字段：" + "、".join(missing))
        campus_id = data["campus_id"]
        if self.repo.get_campus(campus_id) is None:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, f"没有这个校区：{campus_id}")
        periods = tuple(data.get("open_periods") or ())
        if not periods:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "至少选择一个营业时段")
        kind = data["kind"]
        if not isinstance(kind, VenueKind):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "kind 取值不正确")
        venue = Venue(
            id=str(data["id"]).strip(),
            campus_id=campus_id,
            name=str(data["name"]).strip(),
            kind=kind,
            location=str(data.get("location") or "").strip(),
            open_periods=periods,
            tags=tuple(data.get("tags") or ()),
            available=bool(data.get("available", True)),
        )
        if not venue.id or not venue.name:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "id 和 name 不能为空")
        self.repo.save_venue(venue)
        return venue

    def upsert_dish(self, dish):
        if not isinstance(dish, Dish):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "dish 类型不正确")
        if not dish.id or not dish.name:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "id 和菜名不能为空")
        if self.repo.get_venue(dish.venue_id) is None:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, f"没有这个就餐点：{dish.venue_id}")
        if not isinstance(dish.category, DishCategory):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "category 取值不正确")
        if not 0 <= dish.price_fen <= 100_000:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "价格需要在 0–1000 元之间")
        if not isinstance(dish.available, bool):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "available 必须是布尔值")
        dish = dataclasses.replace(dish, updated_at=self.clock.now_ms())
        self.repo.save_dish(dish)
        return dish

    def set_dish_availability(self, dish_id, available, operator):
        if not isinstance(operator, str) or not operator.strip():
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "请填写操作人")
        if not isinstance(available, bool):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "available 必须是布尔值")
        dish = self._dish(dish_id)
        dish = dataclasses.replace(dish, available=available,
                                   updated_at=self.clock.now_ms())
        self.repo.save_dish(dish)
        return dish


# ====================================================================== 决策（B）

class RefDecisionService(DecisionService):

    def __init__(self, repo, catalog, clock, rng=None):
        self.repo = repo
        self.catalog = catalog
        self.clock = clock
        self.rng = rng or random.Random()

    def _recent_ids(self, days: int) -> set[str]:
        if days <= 0:
            return set()
        since = self.clock.now_ms() - days * 24 * 60 * 60 * 1000
        return {d.dish_id for d in self.repo.list_decisions(since_ms=since)}

    def candidates(self, filters):
        if not isinstance(filters, DecisionFilters):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "filters 类型不正确")
        if not 0 <= filters.recent_days <= 60:
            raise CampusError(ErrorCode.INVALID_FILTER, "recent_days 需要在 0–60 之间")
        if filters.max_price_fen is not None and filters.max_price_fen < 0:
            raise CampusError(ErrorCode.INVALID_FILTER, "预算不能是负数")

        venues = self.catalog.list_venues(filters.campus_id, filters.kinds or None,
                                          filters.meal_period)
        if filters.venue_ids:
            allowed = set(filters.venue_ids)
            venues = [v for v in venues if v.id in allowed]
        recent_ids = self._recent_ids(filters.recent_days)

        options: list[DishOption] = []
        for venue in venues:
            campus = self.repo.get_campus(venue.campus_id)
            if campus is None:
                continue
            for dish in self.catalog.list_dishes(venue_id=venue.id):
                if dish.id in filters.exclude_dish_ids:
                    continue
                if filters.max_price_fen is not None and dish.price_fen > filters.max_price_fen:
                    continue
                if filters.categories and dish.category not in filters.categories:
                    continue
                tags = set(dish.tags)
                if filters.include_tags and not set(filters.include_tags) <= tags:
                    continue
                if filters.exclude_tags and tags & set(filters.exclude_tags):
                    continue
                rating = self.catalog.dish_detail(dish.id).rating
                options.append(DishOption(dish, venue, campus, rating,
                                          recent=dish.id in recent_ids))
        options.sort(key=lambda o: o.dish.id)

        if not options:
            raise CampusError(ErrorCode.NO_CANDIDATE,
                              "没有符合条件的菜，放宽一个筛选条件试试")
        if filters.exclude_recent:
            fresh = [o for o in options if not o.recent]
            if fresh:
                return fresh
            return options          # 全部最近吃过：交给 decide() 兜底
        return options

    def _popularity(self) -> Counter:
        since = self.clock.now_ms() - 30 * 24 * 60 * 60 * 1000
        return Counter(d.dish_id for d in self.repo.list_decisions(since_ms=since))

    @staticmethod
    def _weight(option: DishOption, popularity: Counter) -> int:
        return 20 + round(option.rating.average * 10) + min(popularity[option.dish.id], 30)

    def decide(self, filters, mode=DecisionMode.WHEEL):
        if not isinstance(mode, DecisionMode):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "mode 取值不正确")
        options = self.candidates(filters)
        fallback = filters.exclude_recent and bool(options) and all(o.recent for o in options)
        popularity = self._popularity()
        weights = [self._weight(o, popularity) for o in options]

        winner_index = self.rng.choices(range(len(options)), weights=weights, k=1)[0]
        winner = options[winner_index]

        rest = [(i, o) for i, o in enumerate(options) if i != winner_index]
        alternatives: list[DishOption] = []
        pool = list(rest)
        for _ in range(min(2, len(pool))):
            alt_weights = [self._weight(o, popularity) for _, o in pool]
            pick = self.rng.choices(range(len(pool)), weights=alt_weights, k=1)[0]
            alternatives.append(pool.pop(pick)[1])

        now = self.clock.now_ms()
        decision = Decision(f"D{now}-{secrets.token_hex(2).upper()}", winner.dish.id,
                            winner.venue.id, mode, now)
        self.repo.save_decision(decision)

        parts = []
        if fallback:
            parts.append("最近都吃过了，这次从全部候选里抽")
        rating = winner.rating
        parts.append(f"评分 {rating.average:.1f}（{rating.count} 条评价）"
                     if rating.count else "暂无评分")
        count = popularity[winner.dish.id]
        parts.append(f"近 30 天被抽中 {count} 次" if count else "还没有被抽中过")
        return DecisionResult(decision, winner, tuple(alternatives), " · ".join(parts))

    def history(self, limit=20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "limit 需要是 1–100 的整数")
        result = []
        for decision in self.repo.list_decisions(limit=limit * 3):
            dish = self.repo.get_dish(decision.dish_id)
            venue = self.repo.get_venue(decision.venue_id)
            campus = self.repo.get_campus(venue.campus_id) if venue else None
            if dish is None or venue is None or campus is None:
                continue
            result.append(HistoryEntry(decision, dish, venue, campus))
            if len(result) == limit:
                break
        return result


# ====================================================================== 投票（B）

class RefVoteService(VoteService):

    def __init__(self, repo, clock, rng=None):
        self.repo = repo
        self.clock = clock
        self.rng = rng or random.Random()

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(_CODE_ALPHABET)
                           for _ in range(seed.VOTE_CODE_LENGTH))
            if self.repo.get_vote_room(code) is None:
                return code

    def _load(self, code: str) -> VoteRoom:
        room = self.repo.get_vote_room(code)
        if room is None:
            raise CampusError(ErrorCode.NOT_FOUND, f"没有这个投票：{code}")
        return room

    def _auto_close(self, room: VoteRoom) -> VoteRoom:
        if room.status == VoteStatus.OPEN and self.clock.now_ms() >= room.closes_at:
            room = dataclasses.replace(room, status=VoteStatus.CLOSED)
            self.repo.save_vote_room(room)
        return room

    def _result(self, room: VoteRoom) -> VoteResult:
        ballots = self.repo.list_ballots(room.code)
        counts = Counter(b.option_id for b in ballots)
        tallies = tuple(VoteTally(o.option_id, o.label, counts[o.option_id])
                        for o in room.options)
        top = max((t.count for t in tallies), default=0)
        winners = tuple(t.option_id for t in tallies if top > 0 and t.count == top)
        return VoteResult(room, tallies, len(ballots), winners, len(winners) > 1)

    def create_room(self, title, options, closes_in_ms, creator):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 40:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "投票标题需要 1–40 个字")
        if not isinstance(creator, str) or not 1 <= len(creator.strip()) <= 20:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "发起人昵称需要 1–20 个字")
        if not isinstance(options, tuple) or not \
                seed.VOTE_MIN_OPTIONS <= len(options) <= seed.VOTE_MAX_OPTIONS:
            raise CampusError(ErrorCode.INVALID_ARGUMENT,
                              f"选项需要 {seed.VOTE_MIN_OPTIONS}–{seed.VOTE_MAX_OPTIONS} 个")
        seen = set()
        for option in options:
            if not isinstance(option, VoteOption):
                raise CampusError(ErrorCode.INVALID_ARGUMENT, "选项类型不正确")
            if option.option_id in seen:
                raise CampusError(ErrorCode.INVALID_ARGUMENT, "选项 id 不能重复")
            if not option.label:
                raise CampusError(ErrorCode.INVALID_ARGUMENT, "选项名称不能为空")
            seen.add(option.option_id)
        if isinstance(closes_in_ms, bool) or not isinstance(closes_in_ms, int) \
                or not seed.VOTE_MIN_DURATION_MS <= closes_in_ms <= seed.VOTE_MAX_DURATION_MS:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "投票时长需要在 1 分钟到 7 天之间")
        now = self.clock.now_ms()
        room = VoteRoom(self._new_code(), title.strip(), options, creator.strip(),
                        now, now + closes_in_ms)
        self.repo.save_vote_room(room)
        return room

    def get_room(self, code):
        room = self._auto_close(self._load(code))
        return self._result(room)

    def cast_vote(self, code, voter_token, option_id):
        if not isinstance(voter_token, str) or not 8 <= len(voter_token) <= 64:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "投票凭证格式不正确")
        room = self._auto_close(self._load(code))
        if room.status != VoteStatus.OPEN:
            raise CampusError(ErrorCode.INVALID_STATE, "投票已经结束了")
        if option_id not in {o.option_id for o in room.options}:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "没有这个选项")
        self.repo.save_ballot(VoteBallot(code, voter_token, option_id,
                                         self.clock.now_ms()))
        return self._result(room)

    def close_room(self, code, operator):
        if not isinstance(operator, str) or not operator.strip():
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "请填写操作人")
        room = self._auto_close(self._load(code))
        if room.status != VoteStatus.OPEN:
            raise CampusError(ErrorCode.INVALID_STATE, "投票已经结束了")
        room = dataclasses.replace(room, status=VoteStatus.CLOSED)
        self.repo.save_vote_room(room)
        return self._result(room)

    def list_rooms(self, limit=20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "limit 需要是 1–100 的整数")
        return self.repo.list_vote_rooms(limit=limit)


# ====================================================================== 统计（C）

class RefStatsService(StatsService):

    def __init__(self, repo, catalog, clock):
        self.repo = repo
        self.catalog = catalog
        self.clock = clock

    def _check_campus(self, campus_id):
        if campus_id is not None and self.repo.get_campus(campus_id) is None:
            raise CampusError(ErrorCode.INVALID_FILTER, f"没有这个校区：{campus_id}")

    def _in_range(self, ms: int, since: int, until: int) -> bool:
        return since <= ms < until

    def popular_dishes(self, limit=10, campus_id=None):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, "limit 需要是 1–50 的整数")
        self._check_campus(campus_id)
        counter = Counter()
        labels = {}
        for decision in self.repo.list_decisions():
            dish = self.repo.get_dish(decision.dish_id)
            venue = self.repo.get_venue(decision.venue_id)
            if dish is None or venue is None:
                continue
            if campus_id is not None and venue.campus_id != campus_id:
                continue
            counter[dish.id] += 1
            labels[dish.id] = f"{dish.name} · {venue.name}"
        rows = [TopDish(dish_id, labels[dish_id], n) for dish_id, n in counter.items()]
        rows.sort(key=lambda row: (-row.count, row.label))
        return rows[:limit]

    def summary(self, campus_id=None, since_ms=None, until_ms=None):
        self._check_campus(campus_id)
        since = 0 if since_ms is None else since_ms
        # until 是开区间。不传时用 now + 1，保证“刚刚发生的决策 / 投票”也算进看板。
        until = self.clock.now_ms() + 1 if until_ms is None else until_ms
        if since > until:
            raise CampusError(ErrorCode.INVALID_FILTER, "开始时间不能晚于结束时间")

        decisions = [d for d in self.repo.list_decisions()
                     if self._in_range(d.created_at, since, until)]
        by_campus = Counter()
        by_category = Counter()
        dish_counter = Counter()
        dish_labels = {}
        for decision in decisions:
            dish = self.repo.get_dish(decision.dish_id)
            venue = self.repo.get_venue(decision.venue_id)
            if dish is None or venue is None:
                continue
            if campus_id is not None and venue.campus_id != campus_id:
                continue
            by_campus[venue.campus_id] += 1
            by_category[dish.category.value] += 1
            dish_counter[dish.id] += 1
            dish_labels[dish.id] = f"{dish.name} · {venue.name}"

        top = [TopDish(dish_id, dish_labels[dish_id], n)
               for dish_id, n in dish_counter.items()]
        top.sort(key=lambda row: (-row.count, row.label))

        reviews = [r for r in self.repo.list_reviews()
                   if self._in_range(r.created_at, since, until)]
        if campus_id is not None:
            kept = []
            for review in reviews:
                dish = self.repo.get_dish(review.dish_id)
                venue = self.repo.get_venue(dish.venue_id) if dish else None
                if venue is not None and venue.campus_id == campus_id:
                    kept.append(review)
            reviews = kept

        rooms = [r for r in self.repo.list_vote_rooms(limit=100_000)
                 if self._in_range(r.created_at, since, until)]
        ballots = sum(1 for room in rooms for ballot in self.repo.list_ballots(room.code)
                      if self._in_range(ballot.created_at, since, until))

        avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0.0
        return StatsSummary(
            campus_id=campus_id,
            since_ms=since,
            until_ms=until,
            decision_count=sum(by_campus.values()),
            vote_room_count=len(rooms),
            ballot_count=ballots,
            top_dishes=tuple(top[:5]),
            by_campus=dict(sorted(by_campus.items())),
            by_category=dict(sorted(by_category.items())),
            avg_rating=avg,
            review_count=len(reviews),
        )
