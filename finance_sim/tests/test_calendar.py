from datetime import date
from finance_sim.engine.calendar import months_from_date_range


def test_months_from_date_range():
    months = months_from_date_range(
        date(2026, 2, 15),
        date(2026, 4, 1)
    )
    assert months == ["2026-02", "2026-03", "2026-04"]
