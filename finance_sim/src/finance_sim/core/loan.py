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
    extra_payment_rate: float = 0.0
    fees_upfront: float = 0.0
    description: str = ""

    balance: float = 0.0

    def __post_init__(self) -> None:
        self.principal = float(self.principal)
        self.annual_rate = float(self.annual_rate)
        self.payment_amount = float(self.payment_amount)
        self.penalty_rate = float(self.penalty_rate)
        self.fees_upfront = float(self.fees_upfront)
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

    def step(self, month: str, payment: float) -> Dict:
        """
        Advances the loan one month.
        Assumes balance is already initialized via reset_balance.
        """
        if payment < 0:
            raise ValueError("The payment cannot be negative")

        if not self.is_active(month):
            return {
                "loan_id": self.loan_id,
                "month": month,
                "interest_paid": 0.0,
                "penalty_paid": 0.0,
                "paid_principal": 0.0,
                "balance_end": self.balance,
                "cash_out": 0.0,
            }

        starting_balance = self.balance
        interest = starting_balance * (self.annual_rate / 12.0)

        required_min = self.min_payment(month)
        min_paid = min(required_min, payment)
        extra_paid = max(0.0, payment - min_paid)

        # penalty if underpaid
        penalty_paid = 0.0
        if min_paid + 1e-9 < required_min:
            penalty_paid = starting_balance * self.penalty_rate  # simple

        total_due = starting_balance + interest + penalty_paid
        cash_out = min(total_due, min_paid + extra_paid)

        interest_paid = min(interest, cash_out)
        paid_principal = max(0.0, cash_out - interest_paid)
        new_balance = total_due - cash_out

        self.balance = new_balance

        return {
            "loan_id": self.loan_id,
            "month": month,
            "interest_paid": interest_paid,
            "penalty_paid": penalty_paid,
            "paid_principal": paid_principal,
            "balance_end": new_balance,
            "cash_out": cash_out,
        }


    def payoff_amount_for_month(self, month: str) -> float:
        """
        Returns the maximum cash this loan can consume this month without going below 0,
        assuming interest grows once for the month.

        This does not mutate state.
        """
        if not self.is_active(month):
            return 0.0

        starting_balance = float(self.balance)
        monthly_rate = float(self.annual_rate) / 12.0
        interest = starting_balance * monthly_rate
        return starting_balance + interest
