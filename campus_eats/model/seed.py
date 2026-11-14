"""初始数据与业务常量。负责人：C（后端 / 数据结构）；调研数据由全组提供。

注意：下面的食堂、窗口、外卖都是**演示数据**（source=DEMO），
真实数据按 docs/07-调研与数据采集.md 线下调研后用 `tools/import_survey.py` 导入。
所有测试都依赖这里的数字，改动时同步修改测试里的期望值。
"""
from .entities import Campus, Dish, Review, Venue
from .enums import DishCategory, DishSource, MealPeriod, VenueKind

TZ_OFFSET_HOURS = 8                 # 统计 / 评价限流使用的时区（北京时间）
DEFAULT_RECENT_DAYS = 7             # “最近吃过”默认跳过 7 天
RATING_MIN = 1
RATING_MAX = 5
REVIEW_MAX_COMMENT = 200
REVIEW_MAX_AUTHOR = 20
VOTE_CODE_LENGTH = 6
VOTE_MIN_OPTIONS = 2
VOTE_MAX_OPTIONS = 8
VOTE_MIN_DURATION_MS = 60_000                # 1 分钟
VOTE_MAX_DURATION_MS = 7 * 24 * 60 * 60_000  # 7 天

# ------------------------------------------------------------------ 校区

CAMPUSES: tuple[Campus, ...] = (
    Campus("ms", "马房山校区", ("马区", "东院", "西院", "鉴湖")),
    Campus("nh", "南湖校区", ("南湖", "南湖东门")),
)

# ------------------------------------------------------------------ 食堂 / 窗口 / 外卖
# 名称与窗口为演示样例，调研后替换。open_periods 决定“当前时段”筛选。

_ALL_DAY = (MealPeriod.BREAKFAST, MealPeriod.LUNCH, MealPeriod.DINNER)
_MAIN_MEALS = (MealPeriod.LUNCH, MealPeriod.DINNER)

VENUES: tuple[Venue, ...] = (
    Venue("ms_east", "ms", "东院食堂", VenueKind.CANTEEN, "东院·一楼",
          _ALL_DAY, ("大众菜", "经济")),
    Venue("ms_west", "ms", "西院食堂", VenueKind.CANTEEN, "西院·二楼",
          _MAIN_MEALS, ("小炒", "面食")),
    Venue("nh_main", "nh", "南湖食堂", VenueKind.CANTEEN, "南湖·一楼",
          _ALL_DAY, ("窗口多", "人气高")),
    Venue("nh_takeout", "nh", "外卖·轻食沙拉（示例）", VenueKind.TAKEOUT, "南湖校区周边",
          (MealPeriod.LUNCH, MealPeriod.DINNER, MealPeriod.LATE_NIGHT),
          ("外卖", "轻食", "夜宵")),
)

# ------------------------------------------------------------------ 菜品

_MEAT = ("肉",)
_SIGNATURE = ("招牌",)

DISHES: tuple[Dish, ...] = (
    # 马房山 · 东院
    Dish("ms_east_tomato_egg", "ms_east", "番茄炒蛋盖饭", DishCategory.RICE, 1200,
         ("素", "清淡", "便宜"), "酸甜下饭，常年窗口第一名", source=DishSource.DEMO),
    Dish("ms_east_braised_chicken", "ms_east", "黄焖鸡米饭", DishCategory.RICE, 1500,
         ("招牌", "微辣", "肉"), "土豆软糯，汤汁拌饭", source=DishSource.DEMO),
    Dish("ms_east_soy_milk", "ms_east", "现磨豆浆", DishCategory.DRINK, 200,
         ("早餐", "素", "便宜"), "早餐窗口，甜度可选", source=DishSource.DEMO),
    # 马房山 · 西院
    Dish("ms_west_beef_noodle", "ms_west", "红烧牛肉面", DishCategory.NOODLE, 1300,
         ("招牌", "微辣", "肉"), "牛肉块给得实在，汤头偏咸", source=DishSource.DEMO),
    Dish("ms_west_malatang", "ms_west", "自选麻辣烫", DishCategory.SET, 1600,
         ("辣", "自选", "热乎"), "按重量计价，排队高峰较久", source=DishSource.DEMO),
    Dish("ms_west_xiaolongbao", "ms_west", "小笼包（8 只）", DishCategory.SNACK, 800,
         ("早餐", "肉", "便宜"), "现蒸，配醋和姜丝", source=DishSource.DEMO),
    # 南湖
    Dish("nh_main_pepper_steak", "nh_main", "黑椒牛柳饭", DishCategory.RICE, 1500,
         ("肉", "招牌"), "黑椒味重，铁板现炒", source=DishSource.DEMO),
    Dish("nh_main_veggie_set", "nh_main", "两荤一素套餐", DishCategory.SET, 1200,
         ("套餐", "实惠"), "每天换菜，适合管饱", source=DishSource.DEMO),
    Dish("nh_main_sour_noodle", "nh_main", "酸辣粉", DishCategory.NOODLE, 1000,
         ("辣", "酸辣", "便宜"), "红薯粉，酸辣够劲", source=DishSource.DEMO),
    # 外卖样例（手工录入，不接真实平台）
    Dish("nh_takeout_salad", "nh_takeout", "鸡胸肉轻食沙拉", DishCategory.SET, 1800,
         ("轻食", "高蛋白", "外卖"), "外卖样例数据；配送约 30 分钟", source=DishSource.TAKEOUT),
    Dish("nh_takeout_burger", "nh_takeout", "香辣鸡腿堡套餐", DishCategory.SET, 1500,
         ("快餐", "辣", "外卖"), "外卖样例数据；含薯条和可乐", source=DishSource.TAKEOUT),
    Dish("nh_takeout_milk_tea", "nh_takeout", "珍珠奶茶", DishCategory.DRINK, 1200,
         ("饮品", "甜", "外卖"), "外卖样例数据；三分糖推荐", source=DishSource.TAKEOUT),
)

# ------------------------------------------------------------------ 演示评价
# 用匿名昵称，避免把真实同学写进仓库。

REVIEWS: tuple[Review, ...] = (
    Review(1, "ms_east_tomato_egg", 5, "家常味道，便宜大碗，番茄给得足。", "匿名同学1",
           1_762_000_100_000),
    Review(2, "ms_east_braised_chicken", 4, "汤汁拌饭很好吃，就是饭有点硬。", "匿名同学2",
           1_762_000_200_000),
    Review(3, "ms_west_beef_noodle", 5, "牛肉块真的多，汤偏咸但很香。", "匿名同学3",
           1_762_000_300_000),
    Review(4, "ms_west_malatang", 4, "好吃，但中午排队要十分钟。", "匿名同学4",
           1_762_000_400_000),
    Review(5, "nh_takeout_salad", 3, "味道不错，就是配送费有点贵。", "匿名同学1",
           1_762_000_500_000),
)
