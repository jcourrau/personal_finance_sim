from finance_sim.engine.series_builders import (
    get_income_series,
    get_expense_series
)
from finance_sim.core.financial_item import FinancialItem


def test_income_and_expense_series():
    months = ["2026-01", "2026-02", "2026-03"]

    items = [
        FinancialItem(
            item_id="1",
            name="Salary",
            category="Income",
            start_month="2026-01",
            end_month=None,
            amount=1000.0
        ),
        FinancialItem(
            item_id="2",
            name="Rent",
            category="Housing",
            start_month="2026-02",
            end_month=None,
            amount=300.0
        ),
    ]

    income = get_income_series(months, items)
    expense = get_expense_series(months, items)

    assert income["2026-01"] == 1000.0
    assert income["2026-02"] == 1000.0

    assert expense["2026-01"] == 0.0
    assert expense["2026-02"] == 300.0
