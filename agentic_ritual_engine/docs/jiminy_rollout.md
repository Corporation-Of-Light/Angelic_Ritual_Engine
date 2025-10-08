# Jiminy Cricket Rollout Plan

This document captures the standard approach for reusing the `jimminy_cricket_module` across repositories.

## Distribution Options

1. **Shared folder** – copy `core/jimminy_cricket_module.py` into consuming repo under `utils/` and import directly.
2. **Git submodule** – add the `core/` folder as a submodule so updates propagate automatically.
3. **Internal package** – package as `jiminy-cricket-tools` in a private index for installation via `pip`.

For immediate rollout, option (1) is fastest; plan to migrate to (3) once API stabilises.

## Standard Checks & Reminders

The module now ships helper factories:

```python
from core.jimminy_cricket_module import (
    create_jiminy,
    check_license_file,
    check_manual_review,
    check_pending_migrations,
    DEFAULT_REMINDERS,
)

jiminy = create_jiminy(
    checks=[
        check_license_file(),
        check_manual_review(Path("docs/manual_review.md")),
        check_pending_migrations(Path("alembic/versions")),
    ],
    reminders=DEFAULT_REMINDERS + ["Log data provenance before release."],
)
```

Add project-specific checks (e.g., ensure `.env.example` exists) by writing new callables and passing them into `create_jiminy`.

## Recommended Usage Pattern

1. Instantiate once near program entry.
2. Wrap critical workflows:
   ```python
   with jiminy.conscience("catalog-update"):
       if not jiminy.run_checks():
           raise SystemExit("Safety checks failed")
       perform_catalog_tasks()
       jiminy.affirm("Catalog pipeline complete")
   ```
3. For CLI tools, expose a `--no-jiminy` flag to disable when necessary.

## Integration Targets

- **Agentic Ritual Engine** – already integrated (see `core/`).
- **Data ingestion repos** – drop module into utilities, add reminder about licensing and review logs.
- **Visualization dashboards** – run checks before publishing static artifacts (ensures data provenance).

## Future Enhancements

- Optional notifier hook (Slack/email) on failed checks.
- Structured logging integration (JSON logs for centralised monitoring).
- Expand factory helpers (e.g., git status clean check, dataset checksum verification).
