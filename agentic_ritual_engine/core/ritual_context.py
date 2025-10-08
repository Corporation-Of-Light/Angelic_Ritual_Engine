"""Context container describing the ritual state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from astral import LocationInfo
from astral.moon import phase
from astral.sun import sun


def compute_context(lat: float, lon: float, dt: datetime | None = None) -> dict[str, Any]:
    """Compute celestial context for the supplied coordinates."""

    dt = dt or datetime.now(timezone.utc)
    location = LocationInfo(latitude=lat, longitude=lon)
    solar = sun(location.observer, date=dt.date(), tzinfo=timezone.utc)
    moon_phase_index = phase(dt)
    phase_name = _phase_name(moon_phase_index)
    weekday = dt.strftime("%A")

    planetary_hour = _estimate_planetary_hour(dt, solar["sunrise"], solar["sunset"])

    return {
        "datetime": dt.isoformat(),
        "location": {"lat": lat, "lon": lon},
        "moon_phase": phase_name,
        "sunrise": solar["sunrise"].isoformat() if solar.get("sunrise") else None,
        "sunset": solar["sunset"].isoformat() if solar.get("sunset") else None,
        "weekday": weekday,
        "planetary_hour_guess": planetary_hour,
    }


def _phase_name(index: float) -> str:
    phases = [
        "new moon",
        "waxing crescent",
        "first quarter",
        "waxing gibbous",
        "full moon",
        "waning gibbous",
        "last quarter",
        "waning crescent",
    ]
    normalized = int(round(index)) % 30
    bucket = int(normalized / 4)
    return phases[bucket]


def _estimate_planetary_hour(now: datetime, sunrise: datetime, sunset: datetime) -> str:
    planets = [
        "Saturn",
        "Jupiter",
        "Mars",
        "Sun",
        "Venus",
        "Mercury",
        "Moon",
    ]

    if sunrise >= sunset:
        sunrise, sunset = sunset, sunrise

    if sunrise <= now <= sunset:
        segment = (sunset - sunrise) / 12
        index = int((now - sunrise) / segment)
        return f"Day hour {index + 1} ({planets[index % 7]})"

    # Night hours
    if now > sunset:
        next_sunrise = sunrise + (sunset - sunrise)
        segment = (next_sunrise - sunset) / 12
        index = int((now - sunset) / segment)
    else:
        prev_sunset = sunset - (sunrise - sunset)
        segment = (sunrise - prev_sunset) / 12
        index = int((now - prev_sunset) / segment)
    return f"Night hour {index + 1} ({planets[index % 7]})"


@dataclass
class RitualContext:
    """Captures metadata about the ongoing ritual session."""

    loaded: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    location: LocationInfo = field(
        default_factory=lambda: LocationInfo("Default", "World", "UTC", 0, 0)
    )

    def load_defaults(self) -> None:
        """Populate baseline celestial metadata."""

        self.loaded = True

    def describe(self) -> str:
        """Return a human friendly description of the context."""

        timestamp = self.created_at.isoformat()
        return f"Ritual context initialised at {timestamp}"
