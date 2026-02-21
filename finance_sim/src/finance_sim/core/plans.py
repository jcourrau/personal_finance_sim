from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from finance_sim.core.loan import Loan
from finance_sim.core import distributions


DistributionFn = Callable[[float, List[Loan], Optional[List[str]]], Dict[str, float]]

_DISTRIBUTION_MAP: Dict[str, DistributionFn] = {
    "even_distribution": distributions.even_distribution,
    "highest_rate_first": distributions.highest_rate_first,
    "lowest_balance_first": distributions.lowest_balance_first,
    "proportional_to_balance": distributions.proportional_to_balance,
    "manual_priority_list": distributions.manual_priority_list,
}

@dataclass(frozen=True)
class PaymentPlan:
    """
    Simple plan defined by:
    - allocation_percent: fraction of free_cash used as extra debt payment
    - distribution_mode: how extra_budget is split across active loans
    - buffer: amount of free_cash kept aside before applying allocation_percent
    - manual_priority_list: only used for manual_priority_list mode
    """
    distribution_mode: str
    allocation_percent: float = 1.0
    buffer: float = 0.0
    manual_priority_list: Optional[List[str]] = None

    def allocate(
            self,
            month: str,
            free_cash: float,
            active_loans: List[Loan]
    ) -> Dict[str, float]:
        if not (0.0 <= float(self.allocation_percent) <= 1.0):
            raise ValueError("allocation_percent must be between 0 and 1")
        if float(self.buffer) < 0:
            raise ValueError("buffer cannot be negative")

        extra_budget = max(0.0, float(free_cash) - float(self.buffer)) * float(self.allocation_percent)
        if extra_budget <= 0 or not active_loans:
            return {}

        distributor = _DISTRIBUTION_MAP.get(self.distribution_mode)
        if distributor is None:
            raise ValueError(f"Unknown distribution_mode: {self.distribution_mode}")

        return distributor(extra_budget, active_loans, self.manual_priority_list)

    def __str__(self) -> str:
        pct = int(round(self.allocation_percent * 100))
        base = f"percent={pct}%, mode={self.distribution_mode}, buffer={self.buffer}"
        if self.distribution_mode == "manual_priority_list":
            return f"PaymentPlan({base}, priority={self.manual_priority_list})"
        return f"PaymentPlan({base})"