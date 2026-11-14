"""测试里常用的小工具。"""
from __future__ import annotations

from campus_eats.model import DecisionFilters, VoteOption


def filters(**kwargs) -> DecisionFilters:
    return DecisionFilters(**kwargs)


def options(*ids_and_labels) -> tuple[VoteOption, ...]:
    return tuple(VoteOption(oid, label) for oid, label in ids_and_labels)
