from __future__ import annotations
from typing import Callable, Dict, List
from finance_sim.core.financial_item import FinancialItem
from finance_sim.core.month import Month


def _is_active(month: str, item: FinancialItem) -> bool:
    """
    Returns True if the financial item is active during the given month.
    """
    current = Month.parse(month)
    start = Month.parse(item.start_month)

    if current < start:
        return False

    if item.end_month is None:
        return True

    end = Month.parse(item.end_month)
    return current <= end


def _is_income(item: FinancialItem) -> bool:
    return item.category == "Income"


def _is_expense(item: FinancialItem) -> bool:
    return item.category != "Income"


def get_financial_series(
    months: List[str],
    items: List[FinancialItem],
    include_item: Callable[[FinancialItem], bool],
) -> Dict[str, float]:
    """
    Builds a dictionary mapping month -> total amount for items that match include_item.

    Include_item decides if an item is part of this series.
    Example:
    - income: lambda item: item.category == "Income"
    - expenses: lambda item: item.category != "Income"
    """
    series: Dict[str, float] = {m: 0.0 for m in months}

    for month in months:
        total = 0.0
        for item in items:
            if include_item(item) and _is_active(month, item):
                total += item.amount
        series[month] = total

    return series


def get_income_series(months: List[str], items: List[FinancialItem]) -> Dict[str, float]:
    """
    Wrapper for income.
    """
    return get_financial_series(months, items, _is_income)


def get_expense_series(months: List[str], items: List[FinancialItem]) -> Dict[str, float]:
    """
    Wrapper for baseline expenses.
    """
    return get_financial_series(months, items, _is_expense)