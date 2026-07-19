from app.memory.db import get_session_factory


def get_session():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
