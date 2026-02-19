from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True, order=True)
class Month:
    year: int
    month: int  # 1 to 12

    def __post_init__(self) -> None:
        if not (1 <= self.month <= 12):
            raise ValueError("month must be between 1 and 12")

    @staticmethod
    def parse(value: str) -> "Month":
        """
        Parses YYYY-MM into Month.
        """
        parts = value.split("-")
        if len(parts) != 2:
            raise ValueError("Month must be formatted as YYYY-MM")

        year_str, month_str = parts
        year = int(year_str)
        month = int(month_str)
        return Month(year=year, month=month)

    @staticmethod
    def from_date(value: date) -> "Month":
        return Month(year=value.year, month=value.month)

    def to_string(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def add_months(self, months: int) -> "Month":
        """
        Returns a new Month shifted by N months.
        """
        total = (self.year * 12 + (self.month - 1)) + months
        new_year = total // 12
        new_month = (total % 12) + 1
        return Month(year=new_year, month=new_month)
