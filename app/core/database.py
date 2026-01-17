from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import Settings
from functools import lru_cache

Base = declarative_base()


@lru_cache
def get_engine():
    settings = Settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return engine


def get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
