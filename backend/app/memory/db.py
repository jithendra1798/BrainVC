import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.memory.tables import Base

_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        url = os.environ.get("BRAINVC_DB")
        if not url:
            data_dir = Path(__file__).resolve().parents[2] / "data"
            data_dir.mkdir(exist_ok=True)
            url = f"sqlite:///{data_dir / 'brainvc.db'}"
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory():
    get_engine()
    return _session_factory
