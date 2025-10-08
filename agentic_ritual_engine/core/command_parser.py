"""Utility functions for parsing textual ritual commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from slugify import slugify
from unidecode import unidecode

from .flipbook_builder import FlipbookBuilder


@dataclass
class ParsedCommand:
    """Represents a normalized operator and optional payload."""

    action: str
    payload: str | None = None


class CommandParser:
    """Convert free-form text into structured commands."""

    def __init__(self) -> None:
        self.triggers: Dict[str, Callable[..., Any]] = {
            "kronketa": self._assemble_boardroom,
            "gavel": self._legal_sim,
            "hellfire recon": self._red_team,
            "bayesian sophiarch": self._forecasting_stub,
            "sigil flipbook": self._sigil_flipbook,
            "chrono_walker": self._timeline_stub,
            "nephilim vox": self._metalcore_stub,
        }

    def parse(self, raw: str) -> ParsedCommand:
        """Normalize text and split into action and payload."""

        clean = unidecode(raw).strip()
        if not clean:
            raise ValueError("Command cannot be empty")

        parts = clean.split(maxsplit=1)
        action = slugify(parts[0])
        payload = parts[1] if len(parts) > 1 else None
        return ParsedCommand(action=action, payload=payload)

    def parse_and_execute(self, text: str, **kwargs: Any) -> dict[str, Any]:
        """Detect command triggers and execute associated handlers."""

        normalized = unidecode(text).strip().lower()
        for trigger, handler in self.triggers.items():
            if trigger in normalized:
                result = handler(text=normalized, **kwargs)
                return {
                    "trigger": trigger,
                    "status": "ok",
                    "result": result,
                }
        return {"trigger": None, "status": "ignored", "result": None}

    # ------------------------------------------------------------------
    # Handler stubs

    def _assemble_boardroom(self, **_: Any) -> str:
        return "Meta-agent boardroom assembly initiated."

    def _legal_sim(self, **_: Any) -> str:
        return "Legal simulation module pending implementation."

    def _red_team(self, **_: Any) -> str:
        return "Red-team reconnaissance ritual standby."

    def _forecasting_stub(self, **_: Any) -> str:
        return "Bayesian sophia forecasting stub ready."

    def _sigil_flipbook(self, **kwargs: Any) -> dict[str, Any]:
        builder = FlipbookBuilder()
        filters = kwargs.get("filters")
        query = kwargs.get("query")
        count = builder.build_html_flipbook(filters=filters, query=query)
        return {"flipbook": "flipbook.html", "symbols": count}

    def _timeline_stub(self, **_: Any) -> str:
        return "Chrono walker timeline simulation stub active."

    def _metalcore_stub(self, **_: Any) -> str:
        return "Nephilim Vox metalcore generator pending riffs."
