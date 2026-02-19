from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional


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

    balance: Optional[float] = None  # set to principal on first use if None

    def is_active(self, month: str) -> bool:
        # inactive When paid (balance - 0 )
        raise NotImplementedError

    def min_payment(self, month: str) -> float:
        raise NotImplementedError

    def step(self, month: str, extra_payment: float) -> Dict:
        """
        Executes one simulation step for this loan.

        Returns a record dict with:
        - loan_id
        - month
        - interest_paid
        - penalty_paid
        - paid_principal
        - balance_end
        - cash_out
        """
        raise NotImplementedError
