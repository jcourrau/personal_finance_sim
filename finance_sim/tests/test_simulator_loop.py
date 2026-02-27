from dataclasses import dataclass
from typing import Dict, List

from finance_sim.engine.simulator import run_simulation
from finance_sim.core.plans import PaymentPlan


@dataclass
class SimpleLoan:
    """
    Minimal deterministic loan for simulation testing.

    - No interest
    - No penalty
    - Balance decreases by min_payment + extra_payment
    """
    loan_id: str
    rate: float
    minimum: float
    balance: float

    def reset_balance(self) -> None:
        pass

    def is_active(self, month: str) -> bool:
        return self.balance > 0

    def min_payment(self, month: str) -> float:
        return self.minimum if self.balance > 0 else 0.0

    def step(self, month: str, payment: float) -> Dict:
        payment = min(self.balance, self.minimum + payment)
        self.balance -= payment

        return {
            "loan_id": self.loan_id,
            "month": month,
            "interest_paid": 0.0,
            "penalty_paid": 0.0,
            "paid_principal": payment,
            "balance_end": self.balance,
            "cash_out": payment,
        }


class AvalanchePlan:
    """
    Always allocates all positive free_cash to the highest rate active loan.
    """

    def allocate_payments(self, month: str, free_cash: float, active_loans: List[SimpleLoan]) -> Dict[str, float]:
        if free_cash <= 0 or not active_loans:
            return {}

        # highest rate first
        target = sorted(active_loans, key=lambda l: l.rate, reverse=True)[0]
        return {target.loan_id: free_cash}


def test_multiloan_six_months_one_gets_paid_first():
    months = [
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
    ]

    income_series = {m: 500.0 for m in months}
    expense_series = {m: 100.0 for m in months}

    loans = [
        SimpleLoan("L1", rate=0.10, minimum=50.0, balance=200.0),  # highest rate
        SimpleLoan("L2", rate=0.05, minimum=50.0, balance=400.0),
        SimpleLoan("L3", rate=0.03, minimum=50.0, balance=600.0),
    ]

    plan = AvalanchePlan()

    result = run_simulation(
        months=months,
        income_series=income_series,
        expense_series=expense_series,
        loans=loans,
        plan=plan,
        stop_when_debts_cleared=False,
    )

    assert len(result.cashflow_rows) == 6
    l1_rows = [r for r in result.schedule_rows if r["loan_id"] == "L1"]
    assert len(l1_rows) < 6
    assert l1_rows[-1]["balance_end"] == 0.0
