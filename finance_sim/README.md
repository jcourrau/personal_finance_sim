# Finance Simulator (finance-sim)

Modular, library-first engine to simulate personal or business finance cashflows across months. It focuses on:
- A monthly loop that combines income, baseline expenses, minimum debt payments, and plan-driven extra payments.
- Pluggable loan models (abstract base today) and payment allocation plans.
- Producing raw rows suitable for analysis/export (no hard dependency on DataFrames in the core loop).

This repository currently exposes a Python package only (no CLI yet). The main entry point for running a simulation in code is `finance_sim.engine.simulator.run_simulation`.


## Stack
- Language: Python (>= 3.10)
- Packaging/build: `setuptools` (PEP 517) via `pyproject.toml`
- Package manager: `pip`
- Testing: `pytest` (configured in `pyproject.toml`)
- Linting: `ruff`
- Type checking: `mypy`
- Runtime deps:
  - `pandas` (not required by the core loop but available for downstream reporting)
  - `numpy`
  - `sqlalchemy`


## Requirements
- Python 3.10 or newer
- pip (or another PEP 517 compatible installer)
- Recommended: virtual environment (e.g., `venv`)
- OS: Windows, macOS, or Linux


## Installation
Install in editable/development mode with optional dev tools.

From the project root, the Python package is in the `finance_sim/` subdirectory.

```powershell
# 1) Create/activate a virtual environment (recommended)
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 2) Install the package
pip install -e .\finance_sim

# 3) (Optional) Install dev extras: pytest, ruff, mypy
pip install -e .\finance_sim[dev]
```

Notes:
- On macOS/Linux, adapt virtualenv activation accordingly (`source .venv/bin/activate`).
- If you do not want editable mode, you can `pip install .\finance_sim` instead.


## Quick start (library usage)
The simulation loop expects:
- `months`: list of YYYY-MM strings in consecutive order.
- `income_series` and `expense_series`: mappings `{month: amount}`.
- `loans`: list of loan objects implementing the abstract `Loan` interface.
- `plan`: an implementation of `PaymentPlan` that allocates extra cash across active loans.

Because `Loan` and `PaymentPlan` are abstract here, the simplest way to try the engine is to define small test doubles (like in `tests/test_simulator_loop.py`):

```python
from dataclasses import dataclass
from typing import Dict, List
from finance_sim.engine.simulator import run_simulation
from finance_sim.core.plans import PaymentPlan

@dataclass
class FakeLoan:
    loan_id: str
    active_months: List[str]
    minimum: float
    balance: float

    def is_active(self, month: str) -> bool:
        return month in self.active_months

    def min_payment(self, month: str) -> float:
        return self.minimum if self.is_active(month) else 0.0

    def step(self, month: str, extra_payment: float) -> Dict:
        paid_principal = min(self.balance, self.minimum + extra_payment)
        self.balance -= paid_principal
        return {
            "loan_id": self.loan_id,
            "month": month,
            "interest_paid": 0.0,
            "penalty_paid": 0.0,
            "paid_principal": paid_principal,
            "balance_end": self.balance,
            "cash_out": paid_principal,
        }

class FakePlan(PaymentPlan):
    def allocate(self, month: str, free_cash: float, active_loans: List[FakeLoan]) -> Dict[str, float]:
        if not active_loans:
            return {}
        extra = max(0.0, free_cash)
        return {active_loans[0].loan_id: extra}

months = ["2026-01", "2026-02"]
income_series = {"2026-01": 100.0, "2026-02": 100.0}
expense_series = {"2026-01": 10.0, "2026-02": 10.0}
loans = [FakeLoan(loan_id="L1", active_months=["2026-01", "2026-02"], minimum=20.0, balance=50.0)]
plan = FakePlan()

result = run_simulation(
    months=months,
    income_series=income_series,
    expense_series=expense_series,
    loans=loans,
    plan=plan,
    stop_when_debts_cleared=False,
)

print(result.cashflow_rows)
print(result.schedule_rows)
```

For production, you would implement concrete `Loan` models and real `PaymentPlan` strategies.


## API surface (selected)
- `finance_sim.engine.simulator.run_simulation(...) -> SimulationResult`
  - Validates months are consecutive.
  - Loops monthly to compute: income, expenses, minimum loan payments, free cash.
  - Delegates extra payment allocation to `PaymentPlan.allocate(...)`.
  - Steps each active loan via `Loan.step(...)`.
  - Returns two lists of dicts: `cashflow_rows` and `schedule_rows`.

- `finance_sim.core.loan.Loan` (abstract): requires `is_active`, `min_payment`, and `step`.
- `finance_sim.core.plans.PaymentPlan` (abstract): implement `allocate(month, free_cash, active_loans)`.
- Utilities exist in `engine/calendar.py`, `engine/series_builders.py`, and reporting helpers in `reporting/`.


## Project structure
```
finance_sim/
├─ pyproject.toml                 # Packaging, deps, pytest and ruff config
├─ README.md                      # This file
├─ src/
│  └─ finance_sim/
│     ├─ __init__.py
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ financial_item.py
│     │  ├─ loan.py               # Abstract base for loans
│     │  ├─ month.py              # Month parsing/utilities
│     │  └─ plans.py              # Abstract PaymentPlan
│     ├─ data/
│     │  ├─ __init__.py
│     │  ├─ db.py                 # Placeholder for DB access (empty today)
│     │  ├─ loader.py             # Data loading helpers
│     │  └─ orm_models.py         # SQLAlchemy models (if/when used)
│     ├─ engine/
│     │  ├─ __init__.py
│     │  ├─ calendar.py
│     │  ├─ series_builders.py
│     │  └─ simulator.py          # run_simulation entry point
│     └─ reporting/
│        ├─ __init__.py
│        ├─ comparison.py
│        └─ outputs.py
└─ tests/
   ├─ test_calendar.py
   ├─ test_imports.py
   ├─ test_series_builders.py
   ├─ test_simulation_scenarios.py
   └─ test_simulator_loop.py
```


## Running tests
From the `finance_sim/` directory (where `pyproject.toml` lives):

```powershell
# If not already installed
pip install -e .[dev]

# Run test suite
pytest -q
```

Pytest is configured via `tool.pytest.ini_options` in `pyproject.toml` to discover tests under `tests/`.


## Linting and type checks (optional)
```powershell
# Ruff (lint/format as configured)
ruff check .

# Mypy (type checking)
mypy src
```


## Environment variables
No environment variables are currently required for core usage documented above.

- TODO: If/when `data/db.py` is implemented for database access, document required env vars (e.g., `FINANCE_SIM_DB_URL`) here.


## Scripts / CLI
There are currently no console entry points defined in `pyproject.toml`.

- TODO: Add a `project.scripts` console entry if a CLI is desired, e.g., `finance-sim=finance_sim.cli:main`, and document usage here.


## Examples and notebooks
- TODO: Provide richer examples, sample datasets, or notebooks demonstrating typical scenarios and reporting.


## Versioning
Current version: `0.1.0` (see `pyproject.toml`).


## License
A license file is not present in this repository.

- TODO: Add a `LICENSE` file and state the chosen license here (e.g., MIT, Apache-2.0, GPL, or Proprietary). Until then, treat the code as All Rights Reserved.


## Acknowledgments
- Author: Jason Courrau (see `pyproject.toml`).
