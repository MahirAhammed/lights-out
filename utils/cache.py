from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from models import Cache
from config.database import AsyncSessionLocal

async def cache_get(key: str) -> dict | list | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Cache).where(Cache.key == key))
        entry  = result.scalar_one_or_none()

        if entry is None: return None
        if entry.force_refresh: return None
        if entry.expires_at < datetime.now(timezone.utc): return None

        return entry.value

async def cache_set(key: str, value: dict | list, ttl_seconds: int):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Cache).where(Cache.key == key))
        entry  = result.scalar_one_or_none()

        if entry:
            entry.value         = value
            entry.expires_at    = expires_at
            entry.force_refresh = False
            entry.updated_at    = datetime.now(timezone.utc)
        else:
            db.add(Cache(key=key, value=value, expires_at=expires_at))

        await db.commit()


async def cache_invalidate(key: str):
    """Mark for refresh on next read without deleting the stale value."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Cache).where(Cache.key == key))
        entry  = result.scalar_one_or_none()
        if entry:
            entry.force_refresh = True
            await db.commit()


async def cache_delete(key: str):
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Cache).where(Cache.key == key))
        await db.commit()