"""全组共用的枚举。负责人：C（后端 / 数据结构）。

枚举的 value 就是 JSON 和数据库里存的字符串，改名前必须全组同意。
"""
from enum import Enum


class VenueKind(str, Enum):
    CANTEEN = "CANTEEN"      # 食堂（整层 / 整栋）
    WINDOW = "WINDOW"        # 食堂里的独立窗口、风味档口
    TAKEOUT = "TAKEOUT"      # 外卖商家（演示期用手工录入的样例数据）


class MealPeriod(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    LATE_NIGHT = "LATE_NIGHT"


class DishCategory(str, Enum):
    RICE = "RICE"            # 盖饭 / 炒饭
    NOODLE = "NOODLE"        # 面 / 粉
    SNACK = "SNACK"          # 小吃 / 包子 / 饺子
    SET = "SET"              # 套餐 / 快餐
    DRINK = "DRINK"          # 饮品 / 汤
    OTHER = "OTHER"


class DecisionMode(str, Enum):
    WHEEL = "WHEEL"          # 转盘
    LOTTERY = "LOTTERY"      # 抽签


class DishSource(str, Enum):
    DEMO = "DEMO"            # 演示数据，界面上要标注
    SURVEY = "SURVEY"        # 线下调研录入（07 号文档）
    TAKEOUT = "TAKEOUT"      # 外卖样例（手工录入）


class VoteStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
