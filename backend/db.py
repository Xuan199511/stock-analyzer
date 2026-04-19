"""SQLAlchemy engine + session factory.

SQLite file lives next to the backend folder so it survives restarts
but is trivial to delete. For Render/Railway deployments the container
filesystem is ephemeral — cache will naturally cold-start on deploy.
"""
import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DB_PATH = os.getenv("ANALYSIS_DB_PATH", os.path.join(os.path.dirname(__file__), "analysis_cache.db"))
_DB_URL  = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    _DB_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from models import analysis_report  # noqa: F401  (registers mapper)
    Base.metadata.create_all(bind=engine)


@contextmanager
def db_session() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
