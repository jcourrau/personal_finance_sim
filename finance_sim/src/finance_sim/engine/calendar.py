from __future__ import annotations
from typing import List, Optional
from datetime import date
from finance_sim.core.month import Month

def build_months(
    start_month: str,
    end_month: Optional[str],
    max_months: int = 240
) -> List[str]:
    start = Month.parse(start_month)

    if end_month is not None:
        end = Month.parse(end_month)
        if end < start:
            raise ValueError("end_month must be >= start_month")

        months: List[str] = []
        current = start
        while current <= end:
            months.append(current.to_string())
            current = current.add_months(1)

        if len(months) > max_months:
            raise ValueError("Exceeded max_months")

        return months

    months = []
    current = start
    for _ in range(max_months):
        months.append(current.to_string())
        current = current.add_months(1)

    return months


def months_from_date_range(start_date: date, end_date: date) -> List[str]:
    if end_date < start_date:
        raise ValueError("end_date must be >= start_date")

    start = Month.from_date(start_date)
    end = Month.from_date(end_date)

    months: List[str] = []
    current = start
    while current <= end:
        months.append(current.to_string())
        current = current.add_months(1)

    return months
