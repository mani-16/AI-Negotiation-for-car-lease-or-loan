from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import declarative_base
import ssl as _ssl

# Base is defined here alone — no engine creation on import
# Engine is only created when init_db() is called from main.py
Base = declarative_base()

# These are set by init_db() called from main.py startup
engine = None
AsyncSessionLocal = None

def init_db(database_url: str):
    global engine, AsyncSessionLocal

    connect_args: dict = {}
    # Enable SSL for cloud databases (Neon, Supabase, etc.)
    if "neon.tech" in database_url or "supabase" in database_url:
        connect_args["ssl"] = _ssl.create_default_context()
    elif "localhost" not in database_url and "127.0.0.1" not in database_url:
        # For other remote DBs (e.g. Render-hosted Postgres), use SSL
        connect_args["ssl"] = _ssl.create_default_context()

    connect_args["command_timeout"] = 10
    connect_args["server_settings"] = {"application_name": "contract_ai"}

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=3,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=300,      # recycle every 5min
        pool_pre_ping=True,    # ping before each use
        connect_args=connect_args,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()