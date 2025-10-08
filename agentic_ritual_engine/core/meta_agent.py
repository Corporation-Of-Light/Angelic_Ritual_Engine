"""Meta-agent orchestration for the ritual engine."""

from fastapi import FastAPI

from .ritual_context import RitualContext
from .symbolic_kb import SymbolicKnowledgeBase


class MetaAgent:
    """Coordinates data ingestion, context building, and ritual actions."""

    def __init__(self) -> None:
        self.context = RitualContext()
        self.kb = SymbolicKnowledgeBase()

    def bootstrap(self) -> None:
        """Perform minimal startup wiring for the engine."""

        if not self.context.loaded:
            self.context.load_defaults()
        if not self.kb.is_initialized:
            self.kb.initialize_schema()


def create_app() -> FastAPI:
    """Factory to build the FastAPI application."""

    app = FastAPI(title="Agentic Ritual Engine", version="0.1.0")
    engine = MetaAgent()

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/context")
    async def get_context() -> dict[str, str]:
        summary = engine.context.describe()
        return {"context": summary}

    return app
