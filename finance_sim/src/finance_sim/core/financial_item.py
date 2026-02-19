from dataclasses import dataclass
from typing import Optional


@dataclass
class FinancialItem:
    """
    Represents a recurring financial flow.

    Can be either:
    - Income (if category == "Income")
    - Expense (any other category)

    The item is active between start_month and end_month inclusive.
    If end_month is None, the item continues indefinitely.
    """

    item_id: str
    name: str
    category: str  # "Income" or expense category
    start_month: str
    end_month: Optional[str]
    amount: float
