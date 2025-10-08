"""Generate static flipbooks from cleaned symbol assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .symbolic_kb import GlyphImage, Symbol, SymbolicKnowledgeBase

cli = typer.Typer(help="Compile static flipbooks of cleaned symbols.")


class FlipbookBuilder:
    """Combine catalogued symbols into browsable flipbooks."""

    def __init__(self, engine_url: str | None = None) -> None:
        self.kb = SymbolicKnowledgeBase(engine_url=engine_url)
        base_dir = Path(__file__).resolve().parent
        self.template_env = Environment(
            loader=FileSystemLoader(str(base_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def build_html_flipbook(
        self,
        output_path: str | Path = "flipbook.html",
        query: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Render a static HTML gallery of symbol glyphs."""

        filters = dict(filters or {})
        with self.kb.get_session() as session:
            stmt = (
                select(Symbol)
                .join(GlyphImage)
                .options(
                    selectinload(Symbol.images),
                    selectinload(Symbol.source),
                    selectinload(Symbol.rites),
                )
                .where(GlyphImage.transparent_bg.is_(True))
            )

            if query:
                pattern = f"%{query.lower()}%"
                stmt = stmt.where(
                    (Symbol.name.ilike(pattern))
                    | (Symbol.slug.ilike(pattern))
                    | (Symbol.tradition.ilike(pattern))
                    | (Symbol.deity_or_spirit.ilike(pattern))
                )

            for key, value in filters.items():
                column = getattr(Symbol, key, None)
                if column is None or value is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    stmt = stmt.where(column.in_(value))
                else:
                    stmt = stmt.where(column == value)

            symbols = session.execute(stmt.distinct()).scalars().all()
            session.expunge_all()

        rendered = self._render_template(symbols)
        output_path = Path(output_path)
        output_path.write_text(rendered, encoding="utf-8")
        return len(symbols)

    def _render_template(self, symbols: list[Symbol]) -> str:
        template = self.template_env.from_string(self._template_source())
        cards = [self._symbol_to_card(symbol) for symbol in symbols]
        return template.render(cards=cards)

    def _symbol_to_card(self, symbol: Symbol) -> dict[str, Any]:
        images = [img for img in symbol.images if img.transparent_bg]
        primary = images[0] if images else None
        source_title = symbol.source.title if symbol.source else "Unknown"
        page_hint = symbol.page_hint or "?"
        return {
            "name": symbol.name,
            "slug": symbol.slug,
            "tradition": symbol.tradition,
            "function": symbol.function,
            "evokes_or_invokes": symbol.evokes_or_invokes,
            "deity_or_spirit": symbol.deity_or_spirit,
            "source_title": source_title,
            "page_hint": page_hint,
            "tags": symbol.tags or [],
            "thumb_url": primary.thumb_path if primary else None,
            "image_url": primary.raster_path if primary else None,
        }

    def _template_source(self) -> str:
        return """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Agentic Ritual Flipbook</title>
    <style>
      body { font-family: "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 1.5rem; background: #0f1014; color: #f7f7f7; }
      header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
      h1 { margin: 0; font-size: 1.75rem; }
      input[type="search"] { padding: 0.5rem 1rem; border-radius: 999px; border: none; width: 320px; background: #1e1f26; color: #f7f7f7; }
      .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1.25rem; }
      .card { background: rgba(30, 31, 38, 0.85); border-radius: 16px; padding: 1rem; box-shadow: 0 8px 24px rgba(0,0,0,0.35); transition: transform 0.2s ease, box-shadow 0.2s ease; position: relative; }
      .card:hover { transform: translateY(-4px); box-shadow: 0 12px 28px rgba(0,0,0,0.45); }
      .thumb { width: 100%; aspect-ratio: 1 / 1; background: rgba(255,255,255,0.08); border-radius: 12px; display: flex; justify-content: center; align-items: center; overflow: hidden; margin-bottom: 1rem; }
      .thumb img { max-width: 100%; max-height: 100%; object-fit: contain; }
      .meta { font-size: 0.85rem; line-height: 1.4; }
      .meta strong { display: inline-block; width: 100px; color: #9aa0ff; font-weight: 600; }
      .tags { margin: 0.75rem 0 0; display: flex; flex-wrap: wrap; gap: 0.35rem; }
      .tag { background: rgba(154, 160, 255, 0.15); color: #d1d4ff; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; }
      a.full { color: #9aa0ff; text-decoration: none; font-weight: 600; }
      .hidden { display: none !important; }
    </style>
  </head>
  <body>
    <header>
      <h1>Agentic Ritual Flipbook</h1>
      <input id="search" type="search" placeholder="Search symbols..." aria-label="Search symbols" />
    </header>
    <section class="grid" id="gallery">
      {% for card in cards %}
      <article class="card" data-filter="{{ (card.name or '') | lower }} {{ (card.tradition or '') | lower }} {{ (card.deity_or_spirit or '') | lower }} {{ (card.function or '') | lower }} {{ card.tags | join(' ') | lower }}">
        <div class="thumb">
          {% if card.thumb_url %}
          <a class="full" href="{{ card.image_url }}" target="_blank" rel="noopener">
            <img src="{{ card.thumb_url }}" alt="{{ card.name }} thumbnail" />
          </a>
          {% else %}
          <span>No preview</span>
          {% endif %}
        </div>
        <h2>{{ card.name }}</h2>
        <div class="meta">
          <div><strong>Tradition</strong>{{ card.tradition or '—' }}</div>
          <div><strong>Function</strong>{{ card.function or '—' }}</div>
          <div><strong>Evokes</strong>{{ card.evokes_or_invokes or '—' }}</div>
          <div><strong>Spirit</strong>{{ card.deity_or_spirit or '—' }}</div>
          <div><strong>Source</strong>{{ card.source_title }} (p. {{ card.page_hint }})</div>
        </div>
        {% if card.tags %}
        <div class="tags">
          {% for tag in card.tags %}
          <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
        {% endif %}
      </article>
      {% endfor %}
    </section>
    <script>
      const searchInput = document.getElementById('search');
      const cards = document.querySelectorAll('#gallery .card');
      searchInput.addEventListener('input', (event) => {
        const query = event.target.value.trim().toLowerCase();
        cards.forEach((card) => {
          const text = card.getAttribute('data-filter');
          if (!query || (text && text.includes(query))) {
            card.classList.remove('hidden');
          } else {
            card.classList.add('hidden');
          }
        });
      });
    </script>
  </body>
</html>
"""


@cli.command("make-flipbook")
def cli_make_flipbook(
    output: Path = typer.Option(Path("flipbook.html"), "--output", help="HTML output path."),
    filter_expr: str | None = typer.Option(
        None,
        "--filter",
        help="Simple key=value pairs to filter symbols (comma separated).",
    ),
    query: str | None = typer.Option(None, "--query", help="Text query against names, slugs, tradition."),
) -> None:
    builder = FlipbookBuilder()
    filters = _parse_filter_expr(filter_expr)
    count = builder.build_html_flipbook(output_path=output, query=query, filters=filters)
    typer.echo(f"[info] wrote {output} with {count} symbols")


def _parse_filter_expr(filter_expr: str | None) -> dict[str, Any]:
    if not filter_expr:
        return {}
    filters: dict[str, Any] = {}
    pairs = [item.strip() for item in filter_expr.split(",") if item.strip()]
    for pair in pairs:
        if "=" not in pair:
            continue
        key, value = [part.strip() for part in pair.split("=", 1)]
        if not key:
            continue
        if value.startswith("["):
            try:
                filters[key] = json.loads(value)
            except json.JSONDecodeError:
                filters[key] = value
        else:
            filters[key] = value
    return filters


if __name__ == "__main__":
    cli()
