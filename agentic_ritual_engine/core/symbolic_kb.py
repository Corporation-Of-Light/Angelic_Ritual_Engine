"""SQLAlchemy models and data-access helpers for the ritual symbol store."""

from __future__ import annotations
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    create_engine,
    func,
    or_,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import (
    Session,
    declarative_base,
    relationship,
    selectinload,
    sessionmaker,
)

Base = declarative_base()


symbol_rite_association = Table(
    "symbol_rites",
    Base.metadata,
    Column("symbol_id", ForeignKey("symbols.id"), primary_key=True),
    Column("rite_id", ForeignKey("rites.id"), primary_key=True),
)


class TextSource(Base):
    """Describes a textual source for symbols and rites."""

    __tablename__ = "text_sources"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    tradition = Column(String(128), nullable=True)
    url = Column(String(512), nullable=True, unique=False)
    local_path = Column(String(512), nullable=True, unique=False)
    license = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    symbols = relationship("Symbol", back_populates="source")
    rites = relationship("Rite", back_populates="source")


class Symbol(Base):
    """Represents a magical or ritual symbol."""

    __tablename__ = "symbols"
    __table_args__ = (
        Index("ix_symbol_slug", "slug", unique=True),
        Index("ix_symbol_tradition", "tradition"),
        Index("ix_symbol_deity_or_spirit", "deity_or_spirit"),
        Index("ix_symbol_evokes_or_invokes", "evokes_or_invokes"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    tradition = Column(String(128), nullable=True)
    class_ = Column("class", String(128), nullable=True)
    function = Column(String(255), nullable=True)
    evokes_or_invokes = Column(String(128), nullable=True)
    deity_or_spirit = Column(String(255), nullable=True)
    planet = Column(String(64), nullable=True)
    element = Column(String(64), nullable=True)
    correspondence = Column(Text, nullable=True)
    source_id = Column(ForeignKey("text_sources.id"), nullable=True)
    page_hint = Column(String(64), nullable=True)
    tags = Column(JSON, default=list, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source = relationship("TextSource", back_populates="symbols")
    images = relationship("GlyphImage", back_populates="symbol", cascade="all, delete-orphan")
    rites = relationship("Rite", secondary=symbol_rite_association, back_populates="symbols")


class GlyphImage(Base):
    """Stores raster or vector representations of symbols."""

    __tablename__ = "glyph_images"

    id = Column(Integer, primary_key=True)
    symbol_id = Column(ForeignKey("symbols.id"), nullable=False)
    kind = Column(String(64), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    dpi = Column(Integer, nullable=True)
    vector_path = Column(String(512), nullable=True)
    raster_path = Column(String(512), nullable=True)
    thumb_path = Column(String(512), nullable=True)
    transparent_bg = Column(Boolean, default=True, nullable=False)
    bbox = Column(JSON, nullable=True)
    hash_sha256 = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    symbol = relationship("Symbol", back_populates="images")


class Rite(Base):
    """Captures ritual instructions that reference symbols."""

    __tablename__ = "rites"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    tradition = Column(String(128), nullable=True)
    purpose = Column(String(255), nullable=True)
    steps = Column(JSON, default=list, nullable=True)
    source_id = Column(ForeignKey("text_sources.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source = relationship("TextSource", back_populates="rites")
    symbols = relationship("Symbol", secondary=symbol_rite_association, back_populates="rites")


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_db(engine_url: str = "sqlite:///data/ritual.db") -> None:
    """Initialise the database engine and create tables if needed."""

    global _engine, _SessionLocal

    url = make_url(engine_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(engine_url, future=True)
    _SessionLocal = sessionmaker(
        bind=_engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    Base.metadata.create_all(_engine)


def _require_session() -> Session:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None  # for type checkers
    return _SessionLocal()


def upsert_source(**kwargs: Any) -> TextSource:
    """Create or update a textual source based on URL, path or title."""

    session = _require_session()
    try:
        allowed_fields = {
            "title",
            "author",
            "year",
            "tradition",
            "url",
            "local_path",
            "license",
            "notes",
        }
        payload = {key: kwargs.get(key) for key in allowed_fields if key in kwargs}
        if not payload.get("title"):
            raise ValueError("A source title is required")

        candidates = []
        if payload.get("url"):
            candidates.append(TextSource.url == payload["url"])
        if payload.get("local_path"):
            candidates.append(TextSource.local_path == payload["local_path"])
        stmt = select(TextSource)
        if candidates:
            stmt = stmt.where(or_(*candidates))
        else:
            stmt = stmt.where(TextSource.title == payload["title"])

        existing = session.execute(stmt).scalar_one_or_none()

        if existing:
            for key, value in payload.items():
                if value is not None:
                    setattr(existing, key, value)
            entity = existing
        else:
            entity = TextSource(**payload)
            session.add(entity)

        session.commit()
        session.refresh(entity)
        session.expunge(entity)
        return entity
    finally:
        session.close()


def upsert_symbol(**kwargs: Any) -> Symbol:
    """Create or update a symbol using its slug as the unique key."""

    session = _require_session()
    try:
        allowed_fields = {
            "name",
            "slug",
            "tradition",
            "class_",
            "function",
            "evokes_or_invokes",
            "deity_or_spirit",
            "planet",
            "element",
            "correspondence",
            "source_id",
            "page_hint",
            "tags",
        }
        payload = {key: kwargs.get(key) for key in allowed_fields if key in kwargs}
        slug = payload.get("slug")
        name = payload.get("name")
        if not slug:
            raise ValueError("Symbol slug is required for upsert")
        if not name:
            raise ValueError("Symbol name is required for upsert")

        stmt = select(Symbol).where(Symbol.slug == slug)
        existing = session.execute(stmt).scalar_one_or_none()

        tags_value = payload.get("tags")
        if tags_value is not None and not isinstance(tags_value, list):
            if isinstance(tags_value, (set, tuple)):
                payload["tags"] = list(tags_value)
            else:
                payload["tags"] = [tags_value]

        if existing:
            for key, value in payload.items():
                if value is not None:
                    setattr(existing, key, value)
            entity = existing
        else:
            entity = Symbol(**payload)
            session.add(entity)

        session.commit()
        session.refresh(entity)
        session.expunge(entity)
        return entity
    finally:
        session.close()


def attach_glyph(symbol_id: int, **kwargs: Any) -> GlyphImage:
    """Attach a glyph image record to a symbol."""

    session = _require_session()
    try:
        symbol = session.get(Symbol, symbol_id)
        if symbol is None:
            raise ValueError(f"Symbol {symbol_id} not found")

        allowed_fields = {
            "kind",
            "width",
            "height",
            "dpi",
            "vector_path",
            "raster_path",
            "thumb_path",
            "transparent_bg",
            "bbox",
            "hash_sha256",
        }
        payload = {key: kwargs.get(key) for key in allowed_fields if key in kwargs}
        if not payload.get("kind"):
            raise ValueError("Glyph kind is required")

        glyph = GlyphImage(symbol_id=symbol_id, **payload)
        session.add(glyph)
        session.commit()
        session.refresh(glyph)
        session.expunge(glyph)
        return glyph
    finally:
        session.close()


def find_symbols(query: str = "", filters: dict[str, Any] | None = None) -> list[Symbol]:
    """Search symbols by text query and optional filters."""

    filters = dict(filters or {})
    session = _require_session()
    try:
        stmt = select(Symbol).order_by(Symbol.name)
        if query:
            pattern = f"%{query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Symbol.name).like(pattern),
                    func.lower(Symbol.slug).like(pattern),
                    func.lower(Symbol.deity_or_spirit).like(pattern),
                    func.lower(Symbol.tradition).like(pattern),
                )
            )

        tag_filter = filters.pop("tags", None)
        for key, value in filters.items():
            if value is None:
                continue
            column = getattr(Symbol, key, None)
            if column is None:
                continue
            if isinstance(value, (list, tuple, set)):
                stmt = stmt.where(column.in_(value))
            else:
                stmt = stmt.where(column == value)

        results = session.execute(stmt).scalars().all()

        if tag_filter:
            if not isinstance(tag_filter, (list, tuple, set)):
                tag_filter = [tag_filter]
            tag_set = set(tag_filter)
            results = [sym for sym in results if sym.tags and tag_set.issubset(set(sym.tags))]

        session.expunge_all()
        return results
    finally:
        session.close()


def get_symbol_with_images(slug: str) -> Symbol | None:
    """Return a symbol and eagerly load its associated glyph images and rites."""

    session = _require_session()
    try:
        stmt = (
            select(Symbol)
            .where(Symbol.slug == slug)
            .options(
                selectinload(Symbol.images),
                selectinload(Symbol.source),
                selectinload(Symbol.rites),
            )
        )
        symbol = session.execute(stmt).scalar_one_or_none()
        if symbol is not None:
            session.expunge_all()
        return symbol
    finally:
        session.close()


class SymbolicKnowledgeBase:
    """Backwards-compatible wrapper exposing session helpers."""

    def __init__(self, engine_url: str | None = None) -> None:
        self.engine_url = engine_url or "sqlite:///data/ritual.db"
        init_db(self.engine_url)
        self.is_initialized = True

    def initialize_schema(self) -> None:
        init_db(self.engine_url)
        self.is_initialized = True

    def get_session(self) -> Session:
        return _require_session()

    # Convenience passthroughs for legacy callers
    def upsert_source(self, **kwargs: Any) -> TextSource:
        return upsert_source(**kwargs)

    def upsert_symbol(self, **kwargs: Any) -> Symbol:
        return upsert_symbol(**kwargs)

    def attach_glyph(self, symbol_id: int, **kwargs: Any) -> GlyphImage:
        return attach_glyph(symbol_id, **kwargs)
