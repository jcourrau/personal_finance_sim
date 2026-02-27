from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from finance_sim.core.loan import Loan
from finance_sim.core.plans import PaymentPlan
from finance_sim.core.month import Month


@dataclass
class SimulationResult:
    """
    Raw simulation outputs.

    cashflow_rows
      One row per month with aggregated metrics.

    schedule_rows
      One row per active loan per month.
    """
    cashflow_rows: List[Dict]
    schedule_rows: List[Dict]


def _assert_consecutive_months(months: List[str]) -> None:
    """
    Validates that the months_list is strictly consecutive.

    Example valid:
        2026-01, 2026-02, 2026-03

    Raises:
        ValueError if any gap exists.
    """
    if len(months) < 2:
        return

    for index in range(1, len(months)):
        previous_month = Month.parse(months[index - 1])
        current_month = Month.parse(months[index])
        expected = previous_month.add_months(1)

        if current_month != expected:
            raise ValueError(f"Months are not consecutive: {months[index - 1]} -> {months[index]}")


def _initialize_loans(loans: List[Loan]) -> None:
    """
    Resets loan balances before running a simulation.
    """
    for loan in loans:
        loan.reset_balance()

def _next_month(month: str) -> str:
    """
    Returns the next month as YYYY-MM.
    """
    return Month.parse(month).add_months(1).to_string()


def _get_month_inputs(
    month: str,
    income_series: Dict[str, float],
    expense_series: Dict[str, float],
) -> tuple[float, float]:
    """
    Returns income and baseline expenses for the month.

    Missing months default to 0.0.
    """
    income = float(income_series.get(month, 0.0))
    baseline_expenses = float(expense_series.get(month, 0.0))
    return income, baseline_expenses


def _get_active_loans(month: str, loans: List[Loan]) -> List[Loan]:
    """
    Filters loans active for this month.
    """
    return [loan for loan in loans if loan.is_active(month)]


def _sum_minimum_payments(month: str, active_loans: List[Loan]) -> float:
    """
    Sums minimum required payments for active loans in this month.
    """
    total = 0.0
    for loan in active_loans:
        total += float(loan.min_payment(month))
    return total


def _empty_totals():
    totals = {
        "debt_cash_out": 0.0,
        "interest_paid": 0.0,
        "penalty_paid": 0.0,
        "paid_principal": 0.0,
        "debt_balance_end": 0.0,
        "minimum_paid": 0.0,
        "extra_paid": 0.0,
    }
    return totals


def _apply_loan_steps(
    month: str,
    active_loans: List[Loan],
    minimum_paid: Dict[str, float],
    extra_paid: Dict[str, float],
    schedule_rows: List[Dict],
) -> Dict[str, float]:
    """
    Executes Loan.step for each active loan and appends schedule records.

    Returns monthly totals used by the cashflow row.
    """
    totals = _empty_totals()

    for loan in active_loans:
        min_amount = float(minimum_paid.get(loan.loan_id, 0.0))
        extra_amount = float(extra_paid.get(loan.loan_id, 0.0))
        payment = min_amount + extra_amount

        record = loan.step(month=month, payment=payment)
        schedule_rows.append(record)

        totals["minimum_paid"] += min_amount
        totals["extra_paid"] += extra_amount
        totals["debt_cash_out"] += float(record.get("cash_out", 0.0))
        totals["interest_paid"] += float(record.get("interest_paid", 0.0))
        totals["penalty_paid"] += float(record.get("penalty_paid", 0.0))
        totals["paid_principal"] += float(record.get("paid_principal", 0.0))
        totals["debt_balance_end"] += float(record.get("balance_end", 0.0))

    return totals


def _all_loans_cleared(loans: List[Loan]) -> bool:
    """
    Returns True only when all loans are fully paid.

    Rule: If a loan has a numeric balance, it must be <= 0 to be considered cleared.
    """
    for loan in loans:
        if float(loan.balance) > 0:
            return False
    return True


def run_simulation(
    months: List[str],
    income_series: Dict[str, float],
    expense_series: Dict[str, float],
    loans: List[Loan],
    plan: PaymentPlan,
    end_month: Optional[str] = None,
    stop_when_debts_cleared: bool = False,
    carry_deficit: bool = True,
) -> SimulationResult:
    """
    Executes a month-by-month simulation and returns raw rows.

    Inputs:
    - months: consecutive YYYY-MM list
    - income_series, expense_series: month -> amount
    - loans: domain objects with state
    - plan: decides extra allocation

    Outputs:
    - cashflow_rows: one row per month with aggregates
    - schedule_rows: one row per active loan per month

    Notes:
    - No pandas used here for efficiency
    - The plan does not mutate loans, only provides allocation
    """

    # 1. Validations
    if not months:
        raise ValueError("months cannot be empty")
    _assert_consecutive_months(months)

    cashflow_rows: List[Dict] = []
    schedule_rows: List[Dict] = []

    # 2. Initialize Entities
    _initialize_loans(loans)

    # 3. Monthly loop
    for month in months:
        if end_month is not None and month > end_month:
            break

        income, baseline_expenses = _get_month_inputs(month, income_series, expense_series)

        # All loan calculations should exist in one method.
        active_loans = _get_active_loans(month, loans)
        free_cash_before_debt = income - baseline_expenses  # cash before any debt payments

        # Get minimum and extra payment allocation.
        should_allocate = active_loans and free_cash_before_debt > 0
        default_allocation = ({}, {})

        minimum_paid_map, extra_paid_map = (
            plan.allocate_payments(month, free_cash_before_debt, active_loans)
            if should_allocate else default_allocation
        )

        totals = (
            _apply_loan_steps(month, active_loans, minimum_paid_map, extra_paid_map, schedule_rows)
            if active_loans else _empty_totals()
        )

        free_cash_after_debt = free_cash_before_debt - totals["debt_cash_out"]   # includes minimum + extra
        free_cash_after_debt = 0.0 if 0 > free_cash_after_debt > -1e-9 else free_cash_after_debt  # float cleanup
        free_cash_after_minimums = free_cash_before_debt - totals.get("minimum_paid", 0.0)

        #  Append cashflow row
        cashflow_rows.append(
            {
                "month": month,
                "income": income,
                "baseline_expenses": baseline_expenses,
                "cash_before_debt": free_cash_before_debt,
                "cash_after_minimums": free_cash_after_minimums,
                "cash_after_debt": free_cash_after_debt,
                "minimum_paid": totals.get("minimum_paid", 0.0),
                "extra_paid": totals.get("extra_paid", 0.0),
                "debt_cash_paid": totals.get("debt_cash_out", 0.0),
                "interest_paid": totals.get("interest_paid", 0.0),
                "penalty_paid": totals.get("penalty_paid", 0.0),
                "paid_principal": totals.get("paid_principal", 0.0),
                "debt_balance_end": totals.get("debt_balance_end", 0.0),
            }
        )

        # Early stop
        if stop_when_debts_cleared and _all_loans_cleared(loans):
            break

    # 4. Return outputs
    return SimulationResult(cashflow_rows=cashflow_rows, schedule_rows=schedule_rows)
