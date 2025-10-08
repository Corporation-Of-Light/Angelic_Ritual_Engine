"""Streamlit frontend for visualising ritual pulses."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from core.flipbook_builder import FlipbookBuilder
from core.ritual_context import compute_context
from core.symbolic_kb import GlyphImage, Symbol, SymbolicKnowledgeBase
from sqlalchemy.orm import selectinload


def main() -> None:
    """Render an interactive dashboard over indexed symbols."""

    st.set_page_config(page_title="Pulse Map", layout="wide")
    st.title("Agentic Ritual Pulse Map")

    kb = SymbolicKnowledgeBase()

    with st.sidebar:
        st.header("Filters")
        search_text = st.text_input("Search", placeholder="Name, deity, tradition...")
        tradition = st.text_input("Tradition")
        evokes = st.selectbox("Evokes/Invokes", options=["", "evoke", "invoke", "both"])
        planet = st.text_input("Planet")
        element = st.text_input("Element")
        deity = st.text_input("Deity / Spirit")

        st.subheader("Context")
        today = datetime.utcnow().date()
        now_time = datetime.utcnow().time().replace(second=0, microsecond=0)
        date_input = st.date_input("Date", value=today)
        time_input = st.time_input("Time", value=now_time)
        latitude = st.number_input("Latitude", value=0.0, min_value=-90.0, max_value=90.0)
        longitude = st.number_input("Longitude", value=0.0, min_value=-180.0, max_value=180.0)

        context_dt = datetime.combine(date_input, time_input).replace(tzinfo=timezone.utc)
        context_data = compute_context(lat=latitude, lon=longitude, dt=context_dt)

    st.subheader("Current Context")
    cols = st.columns(3)
    cols[0].metric("Moon Phase", context_data.get("moon_phase", "?"))
    cols[1].metric("Weekday", context_data.get("weekday", "?"))
    cols[2].metric("Planetary Hour", context_data.get("planetary_hour_guess", "?"))

    st.caption(
        f"Sunrise: {context_data.get('sunrise')} — Sunset: {context_data.get('sunset')} — Lat/Lon: {context_data['location']['lat']}, {context_data['location']['lon']}"
    )

    filters: Dict[str, Any] = {}
    if tradition:
        filters["tradition"] = tradition
    if evokes:
        filters["evokes_or_invokes"] = evokes
    if planet:
        filters["planet"] = planet
    if element:
        filters["element"] = element
    if deity:
        filters["deity_or_spirit"] = deity

    with kb.get_session() as session:
        query = (
            session.query(Symbol)
            .join(GlyphImage)
            .options(selectinload(Symbol.images), selectinload(Symbol.source))
            .filter(GlyphImage.transparent_bg.is_(True))
        )
        if search_text:
            pattern = f"%{search_text.lower()}%"
            query = query.filter(
                (Symbol.name.ilike(pattern))
                | (Symbol.slug.ilike(pattern))
                | (Symbol.deity_or_spirit.ilike(pattern))
                | (Symbol.tradition.ilike(pattern))
            )
        for key, value in filters.items():
            column = getattr(Symbol, key, None)
            if column is None or not value:
                continue
            query = query.filter(column.ilike(f"%{value}%"))

        symbols = query.distinct().all()
        session.expunge_all()

    hot_symbols = sorted(symbols, key=lambda s: s.created_at, reverse=True)[:5]

    st.subheader("Hot Symbols")
    if hot_symbols:
        for symbol in hot_symbols:
            st.write(f"- {symbol.name} ({symbol.tradition or 'Unknown'}) — {symbol.deity_or_spirit or '—'}")
    else:
        st.info("No symbols match the current filters.")

    st.subheader("Gallery")
    gallery_columns = st.columns(4)
    for index, symbol in enumerate(symbols):
        images = [img for img in symbol.images if img.transparent_bg]
        if not images:
            continue
        image = images[0]
        column = gallery_columns[index % len(gallery_columns)]
        thumb_path = Path(image.thumb_path)
        raster_path = Path(image.raster_path)
        column.image(str(thumb_path), caption=symbol.name, use_column_width=True)
        column.markdown(
            f"<a href='{raster_path}' target='_blank'>Open</a>", unsafe_allow_html=True
        )

    st.subheader("Actions")
    if st.button("Build Flipbook"):
        builder = FlipbookBuilder()
        count = builder.build_html_flipbook(query=search_text, filters=filters)
        st.success(f"Flipbook generated with {count} symbols. Check flipbook.html.")


if __name__ == "__main__":
    main()
