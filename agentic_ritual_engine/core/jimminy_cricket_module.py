"""Jiminy Cricket module: a lightweight conscience plugin for runtime checks."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

DEFAULT_REMINDERS = [
    "Document manual verification steps.",
    "Respect data licensing and usage policies.",
    "Double-check transformations before publishing.",
]

import logging


@dataclass
class ConscienceConfig:
    """Configuration for the Jiminy Cricket conscience layer."""

    enabled: bool = True
    checks: list[Callable[[], bool]] = field(default_factory=list)
    reminders: list[str] = field(default_factory=lambda: list(DEFAULT_REMINDERS))
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("jiminy_cricket"))


class JiminyCricket:
    """Drop-in guardian for program behaviour and ethical reminders."""

    def __init__(self, config: Optional[ConscienceConfig] = None) -> None:
        self.config = config or ConscienceConfig()
        if not self.config.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[jiminy] %(levelname)s %(message)s")
            handler.setFormatter(formatter)
            self.config.logger.addHandler(handler)
        self.config.logger.setLevel(logging.INFO)

    def affirm(self, message: str) -> None:
        """Log a simple affirmation to keep teams aligned."""

        if self.config.enabled:
            self.config.logger.info(message)

    def run_checks(self) -> bool:
        """Execute all registered checks, returning True only if all pass."""

        if not self.config.enabled:
            return True

        failed = []
        for check in self.config.checks:
            try:
                result = check()
            except Exception as exc:  # pragma: no cover - guard clause
                self.config.logger.error("Check %s crashed: %s", check.__name__, exc)
                result = False
            if not result:
                failed.append(check.__name__)

        if failed:
            self.config.logger.warning("Checks failed: %s", ", ".join(failed))
            return False

        self.config.logger.info("All Jiminy checks passed.")
        return True

    def remind(self) -> None:
        """Emit standard reminders to keep best practices in view."""

        if not self.config.enabled:
            return

        for note in self.config.reminders:
            self.config.logger.info("Reminder: %s", note)

    @contextmanager
    def conscience(self, task_name: str) -> Iterator[None]:
        """Context manager wrapping critical sections with checks and reminders."""

        start = datetime.utcnow()
        self.config.logger.info("Beginning %s with Jiminy Cricket oversight", task_name)
        try:
            yield
        finally:
            duration = (datetime.utcnow() - start).total_seconds()
            self.config.logger.info("Completed %s in %.2fs", task_name, duration)
            self.remind()


def create_jiminy(
    enabled: bool = True,
    checks: Optional[Iterable[Callable[[], bool]]] = None,
    reminders: Optional[Iterable[str]] = None,
) -> JiminyCricket:
    """Helper to quickly instantiate a Jiminy Cricket guardian."""

    config = ConscienceConfig(
        enabled=enabled,
        checks=list(checks or []),
        reminders=list(reminders or []),
    )
    return JiminyCricket(config=config)


# ---------------------------------------------------------------------------
# Standard check factories


def check_license_file(path: Path = Path("LICENSE")) -> Callable[[], bool]:
    """Ensure a LICENSE file exists (basic license compliance guard)."""

    def _inner() -> bool:
        exists = path.exists()
        if not exists:
            logging.getLogger("jiminy_cricket").warning("License file missing at %s", path)
        return exists

    _inner.__name__ = f"check_license_file_{path.name}"
    return _inner


def check_manual_review(path: Path = Path("docs/manual_review.md")) -> Callable[[], bool]:
    """Verify manual review log exists to track catalog decisions."""

    def _inner() -> bool:
        exists = path.exists()
        if not exists:
            logging.getLogger("jiminy_cricket").warning("Manual review log missing at %s", path)
        return exists

    _inner.__name__ = f"check_manual_review_{path.stem}"
    return _inner


def check_pending_migrations(directory: Path = Path("alembic/versions")) -> Callable[[], bool]:
    """Warn if migration directory is absent or empty."""

    def _inner() -> bool:
        logger = logging.getLogger("jiminy_cricket")
        if not directory.exists():
            logger.warning("Migration directory missing: %s", directory)
            return False
        has_files = any(directory.iterdir())
        if not has_files:
            logger.warning("No migration files found in %s", directory)
        return has_files

    _inner.__name__ = f"check_pending_migrations_{directory.name}"
    return _inner
