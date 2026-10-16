import argparse

import uvicorn

from app.config import get_settings
from app.database import make_engine, make_session_factory, run_migrations
from app.demo import seed_demo
from app.services.index_store import IndexStore
from app.services.settings_store import load_runtime


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="citewise")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Start the API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    sub.add_parser("seed-demo", help="Load clearly labelled synthetic PDFs")
    sub.add_parser("rebuild-index", help="Rebuild keyword and vector indexes from the database")
    args = parser.parse_args(argv)
    if args.command == "serve":
        uvicorn.run("app.main:app", host=args.host, port=args.port)
        return
    settings = get_settings()
    run_migrations(settings.database_url)
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    index_store = IndexStore(settings.data_dir / "indexes")
    db = factory()
    try:
        runtime = load_runtime(db, settings)
        if args.command == "seed-demo":
            documents, created, present = seed_demo(db, settings, index_store)
            print(f"created={created} already_present={present} documents={len(documents)}")
        elif args.command == "rebuild-index":
            index_store.rebuild(db, runtime)
            print(
                f"chunks={len(index_store.chunks)} embedder={index_store.embedder.name if index_store.embedder else ''}"
            )
            if index_store.embedding_notice:
                print(index_store.embedding_notice)
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
