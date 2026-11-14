"""实体 <-> JSON。负责人：C（后端 / 数据结构）。

to_jsonable：任何实体 → 可以 json.dumps 的 dict/list。
*_from_dict：前端 / 管理后台发来的 JSON → 实体（只校验格式，业务规则由各服务校验）。
"""
from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any

from .entities import (DecisionFilters, Dish, RatingSummary, VoteOption,
                       VoteResult)
from .enums import DishCategory, DishSource, MealPeriod, VenueKind
from .errors import CampusError, ErrorCode


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, RatingSummary):
        return {"dish_id": obj.dish_id, "count": obj.count, "average": obj.average,
                "histogram": {str(k): v for k, v in obj.histogram.items()}}
    if isinstance(obj, VoteResult):
        return {"room": to_jsonable(obj.room), "tallies": to_jsonable(obj.tallies),
                "total_votes": obj.total_votes, "winners": list(obj.winners),
                "tie": obj.tie}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(to_jsonable(k)): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    return obj


def _enum(cls, value, field_name):
    try:
        return cls(value)
    except (ValueError, TypeError):
        allowed = ", ".join(m.value for m in cls)
        raise CampusError(ErrorCode.INVALID_ARGUMENT,
                          f"{field_name} 只能是 {allowed}") from None


def _str(value, field_name: str, *, required: bool = True, limit: int = 200) -> str:
    if value is None:
        if required:
            raise CampusError(ErrorCode.INVALID_ARGUMENT, f"缺少 {field_name}")
        return ""
    if not isinstance(value, str):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 必须是字符串")
    value = value.strip()
    if required and not value:
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 不能为空")
    if len(value) > limit:
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 不能超过 {limit} 个字符")
    return value


def _int(value, field_name: str, *, minimum: int | None = None,
         maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 必须是整数")
    if minimum is not None and value < minimum:
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 不能小于 {minimum}")
    if maximum is not None and value > maximum:
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 不能大于 {maximum}")
    return value


def _str_tuple(value: Any, field_name: str, limit: int = 200) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, f"{field_name} 必须是字符串数组")
    return tuple(_str(x, field_name, required=False, limit=limit) for x in value)


def filters_from_dict(data: Any) -> DecisionFilters:
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, "filters 必须是对象")
    max_price = data.get("max_price_fen")
    if max_price is not None:
        max_price = _int(max_price, "max_price_fen", minimum=0, maximum=100_000)
    recent_days = _int(data.get("recent_days", 7), "recent_days", minimum=0, maximum=60)
    return DecisionFilters(
        campus_id=data.get("campus_id") or None,
        venue_ids=_str_tuple(data.get("venue_ids"), "venue_ids"),
        kinds=tuple(_enum(VenueKind, x, "kinds") for x in (data.get("kinds") or [])),
        meal_period=(_enum(MealPeriod, data["meal_period"], "meal_period")
                     if data.get("meal_period") else None),
        max_price_fen=max_price,
        categories=tuple(_enum(DishCategory, x, "categories")
                         for x in (data.get("categories") or [])),
        include_tags=_str_tuple(data.get("include_tags"), "include_tags", 20),
        exclude_tags=_str_tuple(data.get("exclude_tags"), "exclude_tags", 20),
        exclude_dish_ids=_str_tuple(data.get("exclude_dish_ids"), "exclude_dish_ids", 64),
        exclude_recent=bool(data.get("exclude_recent", True)),
        recent_days=recent_days,
    )


def dish_from_dict(data: Any) -> Dish:
    """管理后台提交的菜品。缺省值按“新菜”处理；业务校验在 CatalogService。"""
    if not isinstance(data, dict):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, "菜品必须是 JSON 对象")
    return Dish(
        id=_str(data.get("id"), "id", limit=64),
        venue_id=_str(data.get("venue_id"), "venue_id", limit=64),
        name=_str(data.get("name"), "name", limit=40),
        category=_enum(DishCategory, data.get("category", DishCategory.OTHER.value), "category"),
        price_fen=_int(data.get("price_fen"), "price_fen", minimum=0, maximum=100_000),
        tags=_str_tuple(data.get("tags"), "tags", 20),
        description=_str(data.get("description", ""), "description", required=False, limit=120),
        available=bool(data.get("available", True)),
        source=_enum(DishSource, data.get("source", DishSource.DEMO.value), "source"),
    )


def venue_from_dict(data: Any) -> dict:
    """管理后台提交的就餐点。返回 dict 供 CatalogService 使用（避免接口里塞太多参数）。"""
    if not isinstance(data, dict):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, "就餐点必须是 JSON 对象")
    periods = tuple(_enum(MealPeriod, x, "open_periods")
                    for x in (data.get("open_periods") or [MealPeriod.LUNCH.value,
                                                           MealPeriod.DINNER.value]))
    tags = _str_tuple(data.get("tags"), "tags", 20)
    return {
        "id": _str(data.get("id"), "id", limit=64),
        "campus_id": _str(data.get("campus_id"), "campus_id", limit=64),
        "name": _str(data.get("name"), "name", limit=40),
        "kind": _enum(VenueKind, data.get("kind", VenueKind.CANTEEN.value), "kind"),
        "location": _str(data.get("location", ""), "location", required=False, limit=60),
        "open_periods": periods,
        "tags": tags,
        "available": bool(data.get("available", True)),
    }


def vote_options_from_list(data: Any) -> tuple[VoteOption, ...]:
    if not isinstance(data, list):
        raise CampusError(ErrorCode.INVALID_ARGUMENT, "options 必须是数组")
    options = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise CampusError(ErrorCode.INVALID_ARGUMENT, f"options[{i}] 必须是对象")
        options.append(VoteOption(
            option_id=_str(item.get("option_id"), f"options[{i}].option_id", limit=64),
            label=_str(item.get("label"), f"options[{i}].label", limit=30),
        ))
    return tuple(options)
