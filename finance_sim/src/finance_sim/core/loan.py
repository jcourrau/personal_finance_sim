from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

from finance_sim.core.month import Month

@dataclass
class Loan:
    loan_id: str
    loan_type: str  # usually "loan"
    start_month: str
    first_due_month: str

    principal: float
    annual_rate: float
    term_months: int
    payment_amount: float

    penalty_rate: float = 0.0
    fees_upfront: float = 0.0
    description: str = ""

    balance: float = 0.0

    def __post_init__(self) -> None:
        self.reset_balance()

    def reset_balance(self) -> None:
        """
        Resets the simulation state to its initial condition.
        Call this before each simulation run.
        """
        if self.principal < 0:
            raise ValueError("principal cannot be negative")
        self.balance = float(self.principal)

    def is_active(self, month: str) -> bool:
        """
        A loan is active when:
        - month >= start_month
        - balance > 0
        """
        if self.balance <= 0:
            return False
        return Month.parse(month) >= Month.parse(self.start_month)

    def min_payment(self, month: str) -> float:
        """
        Minimum payment due only from the first_due_month onward, and only if active.
        """
        if not self.is_active(month):
            return 0.0
        if Month.parse(month) < Month.parse(self.first_due_month):
            return 0.0
        return float(self.payment_amount)

    def step(self, month: str, extra_payment: float) -> Dict:
        """
        Advances the loan one month.
        Assumes balance is already initialized via reset_balance.
        """
        if extra_payment < 0:
            raise ValueError("extra_payment cannot be negative")

        if not self.is_active(month):
            return {
                "loan_id": self.loan_id,
                "month": month,
                "interest_paid": 0.0,
                "penalty_paid": 0.0,
                "paid_principal": 0.0,
                "balance_end": float(self.balance),
                "cash_out": 0.0,
            }

        starting_balance = float(self.balance)
        monthly_rate = float(self.annual_rate) / 12.0
        interest = starting_balance * monthly_rate

        min_pay = self.min_payment(month)
        requested_payment = float(min_pay) + float(extra_payment)

        total_due = starting_balance + interest
        cash_out = min(total_due, requested_payment)

        new_balance = total_due - cash_out
        interest_paid = min(interest, cash_out)
        paid_principal = max(0.0, cash_out - interest_paid)

        self.balance = new_balance

        return {
            "loan_id": self.loan_id,
            "month": month,
            "interest_paid": interest_paid,
            "penalty_paid": 0.0,
            "paid_principal": paid_principal,
            "balance_end": new_balance,
            "cash_out": cash_out,
        }
