from __future__ import annotations
from typing import Dict, List, Optional

from finance_sim.core.loan import Loan


"""
Distribution functions for PaymentPlan.allocate.
All functions must accept the same arguments and return a Dict[str, float].
_: -> must be included and ignore by the function.
"""

def even_distribution(
        extra_budget: float,
        active_loans: List[Loan],
        _: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Splits extra_budget evenly across all active loans.

    Example:
        extra_budget=60, 3 loans -> 20 each
    """
    if extra_budget <= 0 or not active_loans:
        return {}
    per_loan = extra_budget / len(active_loans)
    return {loan.loan_id: per_loan for loan in active_loans}


def highest_rate_first(
        extra_budget: float,
        active_loans: List[Loan],
        _: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Allocates all extra_budget to the loan with the highest annual_rate.

    This matches the avalanche strategy.
    """
    if extra_budget <= 0 or not active_loans:
        return {}
    top = max(active_loans, key=lambda l: float(l.annual_rate))
    return {top.loan_id: extra_budget}


def lowest_balance_first(
        extra_budget: float,
        active_loans: List[Loan],
        _: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Allocates all extra_budget to the loan with the lowest current balance.

    Useful to close small debts faster.
    """
    if extra_budget <= 0 or not active_loans:
        return {}
    top = min(active_loans, key=lambda l: float(l.balance))
    return {top.loan_id: extra_budget}


def proportional_to_balance(
        extra_budget: float,
        active_loans: List[Loan],
        _: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Splits extra_budget proportionally to each loan balance.

    If total balance is 1000 and a loan has 200, it receives 20 percent of extra_budget.
    """
    if extra_budget <= 0 or not active_loans:
        return {}

    total_balance = sum(float(l.balance) for l in active_loans)
    if total_balance <= 0:
        return {}

    return {
        loan.loan_id: extra_budget * (float(loan.balance) / total_balance)
        for loan in active_loans
    }


def manual_priority_list(
    extra_budget: float,
    active_loans: List[Loan],
    priority: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Allocates all extra_budget to the first loan id in priority that is currently active.

    If none of the priority ids are active, returns empty allocation.

    Requires:
        priority list of loan ids in desired order.
    """
    if extra_budget <= 0 or not active_loans:
        return {}
    if not priority:
        raise ValueError("manual_priority_list requires a non empty priority list")

    active_ids = {l.loan_id for l in active_loans}
    for loan_id in priority:
        if loan_id in active_ids:
            return {loan_id: extra_budget}

    return {}