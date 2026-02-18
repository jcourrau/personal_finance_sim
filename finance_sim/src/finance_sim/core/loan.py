from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass
class Loan:
    loan_id: str
    principal: float
    annual_rate: float
    start_month: str
    term_months: int
    payment_amount: float

    def is_active(self, month: str) -> bool:
        raise NotImplementedError

    def min_payment(self, month: str) -> float:
        raise NotImplementedError

    def step(self, month: str, extra_payment: float) -> Dict:
        """
        Executes one simulation step for this loan.

        Returns a record dict with:
        - interest_paid
        - penalty_paid
        - paid_principal
        - balance_end
        - cash_out
        """
        raise NotImplementedError
