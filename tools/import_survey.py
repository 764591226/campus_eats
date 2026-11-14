"""线下调研数据导入工具。负责人：E（测试 / 运维，兼评价模块开发）。

用法：
    python tools/import_survey.py surveys/南湖校区.csv --dry-run
    python tools/import_survey.py surveys/南湖校区.csv

CSV 一行对应一道菜；同一窗口的多道菜重复填写窗口字段即可（按 venue_id 去重）。
模板见 surveys/survey-template.csv。导入前请把 seed 里的演示数据理解为“占位”，
答辩前用这个工具把真实调研结果导入 SQLite。

依赖：C 完成 SqliteRepository 后可用。导入过程只调用 Repository，不经过业务服务，
避免把“上架 / 售罄”等后台状态误改。
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from campus_eats.model import (CampusError, Dish, DishCategory, DishSource,  # noqa: E402
                               MealPeriod, Venue, VenueKind)
from campus_eats.model.serialize import _enum, _int, _str  # noqa: E402

REQUIRED = ["venue_id", "campus_id", "venue_name", "venue_kind", "location",
            "open_periods", "venue_tags", "dish_id", "dish_name", "category",
            "price_fen", "dish_tags", "description", "source", "available"]


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [name for name in REQUIRED if name not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"CSV 缺少列：{', '.join(missing)}")
        return [row for row in reader if any((v or "").strip() for v in row.values())]


def parse_bool(raw: str) -> bool:
    return (raw or "").strip().lower() in ("1", "true", "yes", "y", "是", "在售")


def split(raw: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in (raw or "").replace("；", ";").replace("、", ",")
                 .replace(";", ",").split(",") if x.strip())


def build_entities(rows: list[dict]) -> tuple[list[Venue], list[Dish]]:
    venues: dict[str, Venue] = {}
    dishes: list[Dish] = []
    for line_no, row in enumerate(rows, start=2):
        try:
            venue_id = _str(row["venue_id"], "venue_id", limit=64)
            if venue_id not in venues:
                venues[venue_id] = Venue(
                    id=venue_id,
                    campus_id=_str(row["campus_id"], "campus_id", limit=64),
                    name=_str(row["venue_name"], "venue_name", limit=40),
                    kind=_enum(VenueKind, row["venue_kind"], "venue_kind"),
                    location=_str(row["location"], "location", required=False, limit=60),
                    open_periods=tuple(_enum(MealPeriod, x, "open_periods")
                                       for x in split(row["open_periods"])),
                    tags=split(row["venue_tags"]),
                    available=True,
                )
            dishes.append(Dish(
                id=_str(row["dish_id"], "dish_id", limit=64),
                venue_id=venue_id,
                name=_str(row["dish_name"], "dish_name", limit=40),
                category=_enum(DishCategory, row["category"], "category"),
                price_fen=_int(int(row["price_fen"] or 0), "price_fen",
                               minimum=0, maximum=100_000),
                tags=split(row["dish_tags"]),
                description=_str(row["description"], "description", required=False, limit=120),
                available=parse_bool(row["available"]),
                source=_enum(DishSource, row["source"] or DishSource.SURVEY.value, "source"),
            ))
        except (KeyError, ValueError, CampusError) as exc:
            raise SystemExit(f"第 {line_no} 行有问题：{exc}") from None
    return list(venues.values()), dishes


def main() -> None:
    parser = argparse.ArgumentParser(description="导入线下调研 CSV")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--db", default="data/campus_eats.db")
    parser.add_argument("--dry-run", action="store_true", help="只校验并打印统计，不写数据库")
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise SystemExit(f"找不到文件：{args.csv_path}")
    rows = read_rows(args.csv_path)
    venues, dishes = build_entities(rows)
    print(f"读取 {len(rows)} 行：{len(venues)} 个就餐点，{len(dishes)} 道菜")
    if args.dry_run:
        for venue in venues:
            print(f"  {venue.campus_id} · {venue.name}（{venue.kind.value}）"
                  f" 营业时段 {', '.join(p.value for p in venue.open_periods)}")
        return

    from campus_eats.wiring import build
    system = build({"repository"}, db_path=args.db)
    for venue in venues:
        system.repo.save_venue(venue)
    for dish in dishes:
        system.repo.save_dish(dish)
    print(f"已写入 {args.db}。启动后可在管理后台看到；新增校区的菜品请先确认 campus 存在。")


if __name__ == "__main__":
    main()
