from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import Settings
from functools import lru_cache

Base = declarative_base()


@lru_cache
def get_engine():
    settings = Settings()
    db_url = settings.database_url
    # SQLAlchemy 1.4+ removed the 'postgres' dialect alias; normalize to 'postgresql'
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(db_url, pool_pre_ping=True)
    return engine


def get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
