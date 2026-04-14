from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.config import settings

engine = create_async_engine(
    settings.database_url, 
    connect_args ={"ssl": "require", "statement_cache_size": 0},
    echo=False, 
    pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session