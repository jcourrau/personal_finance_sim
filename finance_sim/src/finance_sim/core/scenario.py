from __future__ import annotations
from typing import List
from .loan import Loan
from .plans import PaymentPlan


class Scenario:

    def __init__(
        self,
        scenario_id: str,
        start_month: str,
        end_month: str | None,
        loans: List[Loan],
        plan: PaymentPlan
    ):
        self.scenario_id = scenario_id
        self.start_month = start_month
        self.end_month = end_month
        self.loans = loans
        self.plan = plan

        self._cashflow_df = None
        self._credit_schedule_df = None

    def simulate(self):
        raise NotImplementedError

    def consolidated_report(self):
        raise NotImplementedError

    def summary_report(self):
        raise NotImplementedError

    def choose_best_plan(self, plans: List[PaymentPlan], objective: str):
        raise NotImplementedError

    def change_plan(self, plan: PaymentPlan):
        self.plan = plan
