from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
_factory: sessionmaker | None = None


def configure(url: str) -> None:
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    _engine = create_engine(url, **kwargs)
    _factory = sessionmaker(_engine, expire_on_commit=False)


def new_session() -> Session:
    assert _factory is not None, "db.configure(url) must be called first"
    return _factory()


def get_session():
    with new_session() as s:
        yield s
