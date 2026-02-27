from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from finance_sim.core.plans import PaymentPlan
from finance_sim.engine.simulator import run_simulation


@dataclass
class FakeLoan:
    loan_id: str
    first_due_month: str
    minimum_payment: float
    balance: float

    def reset_balance(self) -> None:
        pass

    def is_active(self, month: str) -> bool:
        # Active only once the due month is reached and balance remains
        return month >= self.first_due_month and self.balance > 0

    def min_payment(self, month: str) -> float:
        return self.minimum_payment if self.is_active(month) else 0.0

    def step(self, month: str, payment: float) -> Dict:
        # Pay minimum plus extra, capped by the remaining balance
        cash_out = 0.0
        if self.is_active(month):
            cash_out = min(self.balance, float(payment))
            self.balance -= cash_out

        return {
            "loan_id": self.loan_id,
            "month": month,
            "interest_paid": 0.0,
            "penalty_paid": 0.0,
            "paid_principal": cash_out,
            "balance_end": self.balance,
            "cash_out": cash_out,
        }


class AlwaysPayFirstActiveLoanPlan():
    """
    Sends all available free cash to the first active loan only.
    """
    def allocate_payments(self, month: str, free_cash: float, active_loans: List[FakeLoan]) -> Dict[str, float]:
        if not active_loans or free_cash <= 0:
            return {}
        return {active_loans[0].loan_id: free_cash}


class PlanThatAlsoTriesInactiveId():
    """
    Returns an allocation containing an extra entry for an inactive loan_id.
    This lets us test that the simulator filters out unknown or inactive ids.
    """
    def allocate_payments(self, month: str, free_cash: float, active_loans: List[FakeLoan]) -> Dict[str, float]:
        allocation: Dict[str, float] = {}
        if active_loans:
            allocation[active_loans[0].loan_id] = max(0.0, free_cash)
        allocation["INACTIVE_OR_UNKNOWN_LOAN"] = 999999.0
        return allocation


def _income_expense_series(months: List[str], income: float, expense: float) -> tuple[Dict[str, float], Dict[str, float]]:
    income_series = {m: float(income) for m in months}
    expense_series = {m: float(expense) for m in months}
    return income_series, expense_series


def test_plan_attempts_to_pay_inactive_loan_id_is_ignored():
    """
    Even if a plan returns an allocation for an inactive or unknown loan_id,
    the simulator must ignore it and continue without failing.
    """
    months = ["2026-01", "2026-02"]
    income_series, expense_series = _income_expense_series(months, income=100.0, expense=0.0)

    loans = [
        FakeLoan(loan_id="L1", first_due_month="2026-01", minimum_payment=10.0, balance=10.0)
    ]
    plan = PlanThatAlsoTriesInactiveId()

    result = run_simulation(
        months=months,
        income_series=income_series,
        expense_series=expense_series,
        loans=loans,
        plan=plan,
        stop_when_debts_cleared=False,
    )

    schedule_loan_ids = {row["loan_id"] for row in result.schedule_rows}
    assert "INACTIVE_OR_UNKNOWN_LOAN" not in schedule_loan_ids
    assert schedule_loan_ids == {"L1"}


def test_three_loans_paid_sequentially_two_months_apart_each():
    """
    Three loans become due at least two months apart.
    Each is paid when it becomes active, one after another.
    """
    months = [
        "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"
    ]
    income_series, expense_series = _income_expense_series(months, income=200.0, expense=0.0)

    loans = [
        FakeLoan(loan_id="L1", first_due_month="2026-01", minimum_payment=10.0, balance=10.0),
        FakeLoan(loan_id="L2", first_due_month="2026-03", minimum_payment=10.0, balance=10.0),
        FakeLoan(loan_id="L3", first_due_month="2026-05", minimum_payment=10.0, balance=10.0),
    ]
    plan = AlwaysPayFirstActiveLoanPlan()

    result = run_simulation(
        months=months,
        income_series=income_series,
        expense_series=expense_series,
        loans=loans,
        plan=plan,
        stop_when_debts_cleared=False,
    )

    payoff_months: Dict[str, str] = {}
    for row in result.schedule_rows:
        if row["balance_end"] == 0.0 and row["paid_principal"] > 0:
            payoff_months.setdefault(row["loan_id"], row["month"])

    assert payoff_months["L1"] == "2026-01"
    assert payoff_months["L2"] == "2026-03"
    assert payoff_months["L3"] == "2026-05"


def test_three_loans_simulation_ends_before_paying_remaining_two():
    """
    Simulation period ends early. It should not fail even if loans remain unpaid.
    """
    months = ["2026-01", "2026-02", "2026-03"]
    income_series, expense_series = _income_expense_series(months, income=200.0, expense=0.0)

    loans = [
        FakeLoan(loan_id="L1", first_due_month="2026-01", minimum_payment=10.0, balance=10.0),
        FakeLoan(loan_id="L2", first_due_month="2026-03", minimum_payment=10.0, balance=10.0),
        FakeLoan(loan_id="L3", first_due_month="2026-05", minimum_payment=10.0, balance=10.0),
    ]
    plan = AlwaysPayFirstActiveLoanPlan()

    result = run_simulation(
        months=months,
        income_series=income_series,
        expense_series=expense_series,
        loans=loans,
        plan=plan,
        end_month="2026-03",
        stop_when_debts_cleared=False,
    )

    assert len(result.cashflow_rows) == 3
    balances = {loan.loan_id: loan.balance for loan in loans}
    assert balances["L1"] == 0.0
    assert balances["L2"] == 0.0
    assert balances["L3"] > 0.0


def test_three_loans_no_end_month_auto_stops_when_debts_cleared():
    """
    No explicit end month. We provide a long months list, but the simulation should
    stop automatically once all loans are cleared.
    """
    months = [
        "2026-01", "2026-02", "2026-03", "2026-04", "2026-05",
        "2026-06", "2026-07", "2026-08"
    ]
    income_series, expense_series = _income_expense_series(months, income=200.0, expense=0.0)

    loans = [
        FakeLoan(loan_id="L1", first_due_month="2026-01", minimum_payment=10.0, balance=10.0),
        FakeLoan(loan_id="L2", first_due_month="2026-03", minimum_payment=10.0, balance=10.0),
        FakeLoan(loan_id="L3", first_due_month="2026-05", minimum_payment=10.0, balance=10.0),
    ]
    plan = AlwaysPayFirstActiveLoanPlan()

    result = run_simulation(
        months=months,
        income_series=income_series,
        expense_series=expense_series,
        loans=loans,
        plan=plan,
        stop_when_debts_cleared=True,
    )

    # The last payoff happens in 2026-05, so simulation should not run beyond that
    assert result.cashflow_rows[-1]["month"] == "2026-05"
    assert all(loan.balance == 0.0 for loan in loans)
