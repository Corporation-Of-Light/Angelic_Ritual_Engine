# Jiminy Cricket Tools

Lightweight conscience helpers for Python projects. Provides the `JiminyCricket` guardian with configurable checks, reminders, and context managers.

## Installation

```bash
pip install jiminy-cricket-tools
```

## Usage

```python
from jiminy_cricket_tools import (
    create_jiminy,
    check_license_file,
    check_manual_review,
)

jiminy = create_jiminy(
    checks=[check_license_file(), check_manual_review()],
)

with jiminy.conscience("catalog update"):
    if not jiminy.run_checks():
        raise SystemExit("Preflight failed")
    # perform work
```

## Optional Checks

- `check_pending_migrations()` to ensure Alembic migrations exist.
- Extend with your own callables returning `True/False`.

Refer to the main repository docs for integration tips.
