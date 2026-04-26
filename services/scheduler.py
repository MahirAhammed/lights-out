from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from utils.logger import get_logger
import os

logger = get_logger("scheduler")

from services.f1_data import (
    get_current_season_schedule,
    get_pre_race_package,
    get_qualifying_results,
    get_sprint_results,
    get_race_results,
)
from services.email_service import (
    send_pre_race_email,
    send_qualifying_results_email,
    send_sprint_results_email,
    send_race_results_email,
)
from utils.cache import cache_invalidate
from config.database import AsyncSessionLocal
from models import Subscriber
from utils.constants import SESSION_RESULT_OFFSET
import shutil, os

scheduler = AsyncIOScheduler(timezone="UTC")

async def _active_subscribers(db):
    result = await db.execute(
        select(Subscriber).where(
            Subscriber.verified == True,
            Subscriber.is_active == True,
        )
    )
    return result.scalars().all()


def _race_week(schedule: list[dict]) -> dict | None:
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    for race in schedule:
        try:
            race_datetime = datetime.fromisoformat(race["race_date"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if week_start <= race_datetime < week_end:
            return race
    return None


def _session_start(race: dict, name: str) -> datetime | None:
    for s in race.get("sessions", []):
        if name.lower() in s["name"].lower():
            try:
                return datetime.fromisoformat(s["date"].replace("Z", "+00:00"))
            except ValueError:
                return None
    return None


def _send_at(session_start: datetime, session_name: str) -> datetime:
    offset = SESSION_RESULT_OFFSET.get(session_name, 3)
    send_datetime = session_start + timedelta(hours=offset)
    now = datetime.now(timezone.utc)
    return send_datetime if send_datetime > now else now + timedelta(minutes=5)


def _schedule_job(job_func, send_datetime: datetime, job_id: str, args: list):
    scheduler.add_job(
        job_func,
        trigger=DateTrigger(run_date=send_datetime, timezone="UTC"),
        args=args,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduled %s at %s", job_id, datetime.now().strftime("%d %b %Y"))


# RESULT SENDERS
async def _send_qualifying(year: int, round_number: int):
    results = get_qualifying_results(year, round_number)
    if not results:
        logger.warning("Qualifying outcome: no results yet for round %d", round_number)
        return
    async with AsyncSessionLocal() as db:
        subs = await _active_subscribers(db)
        if subs:
            await send_qualifying_results_email(
                subs, {"results": results["results"], "race_name": results["race_name"], "round": round_number, "year": year}, db
            )
            logger.info("Qualifying results sent to %d subscribers", len(subs))


async def _send_sprint(year: int, round_number: int):
    results = get_sprint_results(year, round_number)
    if results:
        async with AsyncSessionLocal() as db:
            subs = await _active_subscribers(db)
            if subs:
                await send_sprint_results_email(
                    subs, {"results": results, "round": round_number, "year": year}, db
                )
                logger.info("Sprint results sent to %d subscribers", len(subs))
    else:
        logger.warning("Sprint outcome: no results yet for round %d", round_number)

    for key in ("driver_standings", "constructor_standings"):
        await cache_invalidate(key)
    logger.info("Standings cache invalidated after sprint round %d", round_number)


async def _send_race(year: int, round_number: int):
    results = get_race_results(year, round_number)
    if results:
        async with AsyncSessionLocal() as db:
            subs = await _active_subscribers(db)
            if subs:
                await send_race_results_email(
                    subs, {"results": results, "round": round_number, "year": year}, db
                )
                logger.info("Race results sent to %d subscribers", len(subs))
    else:
        logger.warning("Race outcome: no results yet for round %d", round_number)
    
    for key in ("driver_standings", "constructor_standings", "current_race_weekend"):
        await cache_invalidate(key) # Invalidate current standings in cache

    logger.info("Standings cache invalidated after race round %d", round_number)


# THURSDAY SCHEDULE CHECKER
async def job_thursday_check():
    _clear_fastf1_cache()
    schedule = await get_current_season_schedule()
    race = _race_week(schedule)
    if not race:
        logger.info("Not a race weekend :(")
        return

    year = datetime.now(timezone.utc).year
    round_number = race["round"]
    is_sprint    = race.get("is_sprint", False)
    logger.info("Race weekend: %s - Round %d (sprint=%s)", race["name"], round_number, is_sprint)

    # Send pre-race email
    try:
        data = await get_pre_race_package(year, round_number)
        async with AsyncSessionLocal() as db:
            subs = await _active_subscribers(db)
            if subs:
                await send_pre_race_email(subs, data, db)
                logger.info("Pre-race email sent to %d subscribers", len(subs))
    except Exception as e:
        logger.error("Pre-race email error: %s", e)

    for job, _, send_datetime, job_id in _schedule_weekend_jobs(race, year):
        _schedule_job(job, send_datetime, job_id, [year, round_number])


async def recover_missed_jobs():

    logger.info("Startup recovery check")
    schedule = await get_current_season_schedule()
    race = _race_week(schedule)
    if not race:
        logger.info("No active race weekend, nothing to recover")
        return

    year = datetime.now(timezone.utc).year
    round_number = race["round"]
    now = datetime.now(timezone.utc)
    logger.info("Active race weekend: %s - Round %d", race["name"], round_number)

    for job, _, send_datetime, job_id in _schedule_weekend_jobs(race, year):
        if send_datetime > now:
            _schedule_job(job, send_datetime, job_id, [year, round_number])
            logger.info("Recovered job: %s", job_id)
        else:
            logger.info("Past send window, skipping: %s", job_id)
    

def _schedule_weekend_jobs(race: dict, year: int) -> list[tuple]:
    round_number = race["round"]
    is_sprint = race.get("is_sprint", False)
    jobs = []

    if is_sprint:
        sprint_quali = _session_start(race, "Sprint Shootout") or _session_start(race, "Sprint Qualifying")
        if sprint_quali:
            jobs.append((
                _send_qualifying, 
                "Qualifying",
                _send_at(sprint_quali, "Qualifying"), 
                f"sprint_quali_{round_number}"
            ))

        sprint_race = _session_start(race, "Sprint")
        if sprint_race:
            jobs.append((
                _send_sprint, 
                "Sprint", 
                _send_at(sprint_race, "Sprint"), 
                f"sprint_{round_number}"
            ))

    qualis = _session_start(race, "Qualifying")
    if qualis:
        jobs.append((
            _send_qualifying,
            "Qualifying",
            _send_at(qualis, "Qualifying"), 
            f"quali_{round_number}"
        ))

    race_start = _session_start(race, "Race")
    if race_start:
        jobs.append((_send_race, "Race", _send_at(race_start, "Race"), f"race_{round_number}"))

    return jobs


def _clear_fastf1_cache(path: str = "/tmp/fastf1_cache"):
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)
            logger.info("FastF1 cache cleared at %s", path)
    except Exception as e:
        logger.warning("Failed to clear FastF1 cache: %s", e)


def start_scheduler():
    scheduler.add_job(
        job_thursday_check,
        trigger=CronTrigger(day_of_week="thu", hour=17, minute=0, timezone="UTC"),
        id="thursday_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started -- Thursday check at 17:00 UTC")