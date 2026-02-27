from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import inspect

from finance_sim.core.loan import Loan
from finance_sim.core import distributions


DistributionFn = Callable[[float, List[Loan], Optional[List[str]]], Dict[str, float]]

_DISTRIBUTION_MAP: Dict[str, DistributionFn] = {
    name: fn
    for name, fn in inspect.getmembers(distributions, inspect.isfunction)
    if not name.startswith("_")
}


def _normalize_payments(loan_payments: Dict[str, float]):
    return {loan_id: max(0.0, float(amount)) for loan_id, amount in loan_payments.items()}


@dataclass()
class PaymentPlan:
    """
    Computes an extra budget from free cash and distributes it across active loans.

    If use_full_budget is False:
        Performs a single distribution pass.

    If use_full_budget is True:
        Runs multiple distribution rounds until:
        - remaining budget is effectively zero, or
        - no eligible loans remain (No remaining payoff capacity)
    """
    distribution_mode: str
    allocation_percent: float = 1.0
    buffer: float = 0.0
    manual_priority_list: Optional[List[str]] = None
    use_full_budget: bool = False

    def __post_init__(self):
        self.allocation_percent = float(self.allocation_percent)
        self.buffer = float(self.buffer)
        self._initial_validations()

    def _initial_validations(self):
        if self.allocation_percent < 0 or self.allocation_percent > 1:
            raise ValueError("allocation_percent must be between 0 and 1")
        if self.buffer < 0:
            raise ValueError("buffer cannot be negative")


    def _allocate_use_full_budget(
            self,
            month: str,
            initial_budget: float,
            active_loans: List[Loan],
            distributor,
    ) -> Dict[str, float]:
        """
        Repeats distribution rounds to use as much budget as possible,
        respecting each loan monthly payoff cap.
        """

        def _get_eligible_loans_and_caps(
                loans: List[Loan],
                _assigned_cash: Dict[str, float],
        ) -> tuple[List[Loan], Dict[str, float]]:

            _payoff_caps: Dict[str, float] = {
                loan.loan_id: loan.payoff_amount_for_month(month)
                for loan in loans
            }

            _eligible_loans = [
                loan
                for loan in loans
                if _payoff_caps[loan.loan_id] - _assigned_cash.get(loan.loan_id, 0.0) > epsilon
            ]

            return _eligible_loans, _payoff_caps

        epsilon = 1e-6
        remaining_budget = initial_budget
        assigned_cash: Dict[str, float] = {}  # Tracks total assigned per loan
        loans_by_id = {loan.loan_id: loan for loan in active_loans} # Quick lookup

        # Loans that still have capacity this month
        eligible_loans, payoff_caps = _get_eligible_loans_and_caps(active_loans, assigned_cash)

        # Loops over budget until is fully allocated
        while remaining_budget > epsilon and eligible_loans:

            # Ask the distributor how it would split the remaining budget
            proposed_allocation = distributor(
                remaining_budget,
                eligible_loans,
                self.manual_priority_list,
            )
            spent_this_round = 0.0  # Tracks how much we actually managed to assign

            # Allocation per Loan loop
            for loan_id, proposed_amount in proposed_allocation.items():

                # Ignore unknown ids and negative proposals
                if loan_id not in loans_by_id or proposed_amount <= 0:
                    continue

                # Define how much we can pay on this Loan.
                total_cap = payoff_caps.get(loan_id, 0.0)           # Max cash the loan can consume
                already_assigned = assigned_cash.get(loan_id, 0.0)  # Assigned in prior rounds
                cap_left = total_cap - already_assigned             # Remaining capacity
                if cap_left <= epsilon:                             # No room left for this loan
                    continue

                actual_payment  = min(proposed_amount, cap_left, remaining_budget)   # Enforce caps on payments
                if actual_payment <= epsilon:                                        # Ignore negligible payments
                    continue

                # Applies the payment
                assigned_cash[loan_id] = already_assigned + actual_payment   # Update the loan total
                remaining_budget -= actual_payment                           # Reduce remaining global cash
                spent_this_round += actual_payment                           # Track round usage
                if remaining_budget <= epsilon:                              # No more budget to allocate
                    break

            if spent_this_round <= epsilon:
                break   # Nothing was assigned this round, avoids infinite-loop

            # Still has remaining capacity
            eligible_loans, payoff_caps = _get_eligible_loans_and_caps(active_loans, assigned_cash)

        return assigned_cash  # Final allocation after all rounds

    # Main Method
    def allocate_payments(
            self,
            month: str,
            cash_available: float,
            active_loans: List[Loan]
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """
        Returns:
            minimum_paid_by_loan, extra_paid_by_loan

        Rules:
        - If cash_available <= 0: returns ({}, {})
        - Minimums are funded first (partially if needed)
        - Extra is allocated only if all minimums are fully covered
        """
        # Get the actual usable budget
        if not active_loans or cash_available <= 0:
            return {}, {} # Avoids unnecessary calculations

        # Get the distribution function
        distributor = _DISTRIBUTION_MAP.get(self.distribution_mode)
        if distributor is None:
            raise ValueError(f"Unknown distribution_mode: {self.distribution_mode}")

        required_min = {loan.loan_id: float(loan.min_payment(month)) for loan in active_loans}
        total_min_required = sum(required_min.values())

        # Not enough for minimums: distribute available cash as partial minimum payments
        if total_min_required > 0 and cash_available < total_min_required:
            minimum_paid = distributor(cash_available, active_loans, self.manual_priority_list)
            minimum_paid = _normalize_payments(minimum_paid)
            return minimum_paid, {}

        # Enough only for minimums: Doesn't return extra allocation.
        minimum_paid = required_min
        remaining = cash_available - total_min_required
        if remaining <= 0:
            return minimum_paid, {}

        # Extra budget comes from remaining cash
        extra_budget = max(0.0, remaining - self.buffer) * self.allocation_percent
        if extra_budget <= 0:
            return minimum_paid, {}

        # Send the raw allocation.
        if not self.use_full_budget:
            extra_paid = distributor(extra_budget, active_loans, self.manual_priority_list)
            extra_paid = _normalize_payments(extra_paid)
            return minimum_paid, extra_paid

        # Send the distributed allocation.
        extra_paid = self._allocate_use_full_budget(
             month=month,
             initial_budget=extra_budget,
             active_loans=active_loans,
            distributor=distributor,
        )
        return minimum_paid, extra_paid

    def __str__(self) -> str:
        pct = int(round(self.allocation_percent * 100))
        base = f"percent={pct}%, mode={self.distribution_mode}, buffer={self.buffer}"
        if self.distribution_mode == "manual_priority_list":
            return f"PaymentPlan({base}, priority={self.manual_priority_list})"
        return f"PaymentPlan({base})"