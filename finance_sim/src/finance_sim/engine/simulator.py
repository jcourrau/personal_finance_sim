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


def _calculate_free_cash(income: float, baseline_expenses: float, minimum_payments: float) -> float:
    """
    Computes free cash before extra debt payments.

    free_cash = income - baseline_expenses - minimum_payments
    """
    return income - baseline_expenses - minimum_payments


def _get_allocation(
    plan: PaymentPlan,
    month: str,
    free_cash: float,
    active_loans: List[Loan],
) -> Dict[str, float]:
    """
    Requests an allocation from the plan and validates it.

    Validation rules:
    - Negative extra payments are not allowed (raise).
    - Allocations for inactive or unknown loan ids are ignored.
    """
    raw_allocation = plan.allocate(month=month, free_cash=free_cash, active_loans=active_loans)

    active_ids = {loan.loan_id for loan in active_loans}
    allocation: Dict[str, float] = {}

    for loan_id, extra_payment in raw_allocation.items():
        try:
            extra = float(extra_payment)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"extra_payment for loan_id {loan_id} must be numeric") from exc
        if extra < 0:
            raise ValueError("extra_payment cannot be negative")
        if loan_id in active_ids and extra > 0:
            allocation[loan_id] = extra

    return allocation


def _empty_totals():
    totals = {
        "debt_cash_out": 0.0,
        "interest_paid": 0.0,
        "penalty_paid": 0.0,
        "paid_principal": 0.0,
        "debt_balance_end": 0.0,
    }
    return totals


def _apply_loan_steps(
    month: str,
    active_loans: List[Loan],
    allocation: Dict[str, float],
    schedule_rows: List[Dict],
) -> Dict[str, float]:
    """
    Executes Loan.step for each active loan and appends schedule records.

    Returns monthly totals used by the cashflow row.
    """
    totals = _empty_totals()

    for loan in active_loans:
        extra_payment = float(allocation.get(loan.loan_id, 0.0))
        record = loan.step(month=month, extra_payment=extra_payment)
        schedule_rows.append(record)

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

    # 2. Initialize Loans Balance
    _initialize_loans(loans)

    # 3. Monthly loop
    for month in months:
        if end_month is not None and month > end_month:
            break

        income, baseline_expenses = _get_month_inputs(month, income_series, expense_series)
        active_loans = _get_active_loans(month, loans)
        minimum_payments = _sum_minimum_payments(month, active_loans)
        original_free_cash = _calculate_free_cash(income, baseline_expenses, minimum_payments)

        if active_loans:
            allocation = _get_allocation(plan, month, original_free_cash, active_loans)
            totals = _apply_loan_steps(month, active_loans, allocation, schedule_rows)
        else:
            totals = _empty_totals()

        free_cash_after_debt = original_free_cash - totals["debt_cash_out"]
        free_cash_after_debt = 0.0 if 0 > free_cash_after_debt > -1e-9 else free_cash_after_debt

        #  Append cashflow row
        cashflow_rows.append(
            {
                "month": month,
                "income": income,
                "baseline_expenses": baseline_expenses,
                "minimum_payments": minimum_payments,
                "free_cash_after_minimum_payments": original_free_cash,
                "debt_cash_out": totals["debt_cash_out"],
                "free_cash_after_debt": free_cash_after_debt,
                "interest_paid": totals["interest_paid"],
                "penalty_paid": totals["penalty_paid"],
                "paid_principal": totals["paid_principal"],
                "debt_balance_end": totals["debt_balance_end"],
            }
        )

        # Early stop
        if stop_when_debts_cleared and _all_loans_cleared(loans):
            break

    # 4. Return outputs
    return SimulationResult(cashflow_rows=cashflow_rows, schedule_rows=schedule_rows)
