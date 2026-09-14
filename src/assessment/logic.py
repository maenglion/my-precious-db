"""3-valued logic (TRUE / FALSE / UNKNOWN).

v0.2 9장 규칙:
    AND: FALSE 있으면 FALSE, 아니고 UNKNOWN 있으면 UNKNOWN, 전부 TRUE면 TRUE
    OR:  TRUE  있으면 TRUE,  아니고 UNKNOWN 있으면 UNKNOWN, 전부 FALSE면 FALSE
    NOT: TRUE->FALSE, FALSE->TRUE, UNKNOWN->UNKNOWN
"""

from __future__ import annotations

from enum import Enum


class TruthValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


def t_and(*values: TruthValue) -> TruthValue:
    """AND with three-valued logic."""
    if not values:
        raise ValueError("t_and() requires at least one value")
    if any(v is TruthValue.FALSE for v in values):
        return TruthValue.FALSE
    if any(v is TruthValue.UNKNOWN for v in values):
        return TruthValue.UNKNOWN
    return TruthValue.TRUE


def t_or(*values: TruthValue) -> TruthValue:
    """OR with three-valued logic."""
    if not values:
        raise ValueError("t_or() requires at least one value")
    if any(v is TruthValue.TRUE for v in values):
        return TruthValue.TRUE
    if any(v is TruthValue.UNKNOWN for v in values):
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def t_not(value: TruthValue) -> TruthValue:
    """NOT with three-valued logic."""
    if value is TruthValue.TRUE:
        return TruthValue.FALSE
    if value is TruthValue.FALSE:
        return TruthValue.TRUE
    return TruthValue.UNKNOWN