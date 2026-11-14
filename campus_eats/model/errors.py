"""统一错误。负责人：C（后端 / 数据结构）。

所有模块只抛 CampusError；web 层按 code 转成 HTTP 状态码和 JSON。
"""
from enum import Enum


class ErrorCode(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"    # 参数格式不对（缺字段、类型错误、数量越界……）
    INVALID_FILTER = "INVALID_FILTER"        # 筛选条件不合法（校区不存在、时间范围反了……）
    NOT_FOUND = "NOT_FOUND"                  # 校区 / 食堂 / 菜品 / 投票不存在
    NO_CANDIDATE = "NO_CANDIDATE"            # 筛选后没有任何可抽的菜
    INVALID_STATE = "INVALID_STATE"          # 当前状态不允许该操作（投票已截止、重复结束……）
    RATE_LIMITED = "RATE_LIMITED"            # 同一天对同一道菜重复评价


HTTP_STATUS = {
    ErrorCode.INVALID_ARGUMENT: 400,
    ErrorCode.INVALID_FILTER: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.NO_CANDIDATE: 409,
    ErrorCode.INVALID_STATE: 409,
    ErrorCode.RATE_LIMITED: 429,
}


class CampusError(Exception):
    """业务错误。message 直接给最终用户看，用中文写清楚怎么办。"""

    def __init__(self, code: ErrorCode, message: str, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        body = {"code": self.code.value, "message": self.message}
        if self.details:
            body["details"] = self.details
        return body

    def __repr__(self) -> str:
        return f"CampusError({self.code.value}, {self.message!r})"
