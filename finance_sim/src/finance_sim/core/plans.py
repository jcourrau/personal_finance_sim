from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List
from .loan import Loan


class PaymentPlan(ABC):

    @abstractmethod
    def allocate(
        self,
        month: str,
        free_cash: float,
        active_loans: List[Loan]
    ) -> Dict[str, float]:
        """
        Returns mapping:
        {loan_id: extra_payment}
        """
        pass

# Plans can't allocate free cash to inactive_loan_ids