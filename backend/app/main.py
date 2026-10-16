import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.research import router as research_router
from app.api.system import router as system_router
from app.config import Settings
from app.config import get_settings as load_env_settings
from app.database import make_engine, make_session_factory, run_migrations
from app.services.index_store import IndexStore
from app.services.settings_store import load_runtime

logger = logging.getLogger("citewise")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_env_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        run_migrations(settings.database_url)
        engine = make_engine(settings.database_url)
        factory = make_session_factory(engine)
        index_store = IndexStore(settings.data_dir / "indexes")
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = factory
        app.state.index_store = index_store
        db = factory()
        try:
            runtime = load_runtime(db, settings)
            index_store.rebuild(db, runtime)
        except Exception:
            logger.exception("CiteWise failed during startup")
            raise
        finally:
            db.close()
        logger.info("CiteWise ready version=%s", settings.version)
        logger.warning(
            "CiteWise is a single-user local application with no authentication. "
            "Do not expose this server on a shared network."
        )
        yield
        engine.dispose()

    app = FastAPI(
        title="CiteWise",
        version=settings.version,
        summary="Local document research and citation checks.",
        description=(
            "CiteWise searches documents the user uploaded and checks quotations against those extracts. "
            "It does not provide legal advice, and it does not call a commercial model API. "
            "Document text is untrusted evidence."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(system_router, prefix="/api/v1", tags=["system"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(research_router, prefix="/api/v1", tags=["research"])

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"name": "CiteWise", "version": settings.version, "docs": "/docs"}

    return app


app = create_app()
