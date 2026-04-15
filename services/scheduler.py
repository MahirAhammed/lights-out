from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

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
    now        = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end   = week_start + timedelta(days=7)

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
    offset  = SESSION_RESULT_OFFSET.get(session_name, 3)
    send_datetime = session_start + timedelta(hours=offset)
    now     = datetime.now(timezone.utc)
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
    print(f"  Scheduled {job_id} => {send_datetime.strftime('%a %d %b %H:%M UTC')}")


# RESULT SENDERS
async def _send_qualifying(year: int, round_number: int):
    results = get_qualifying_results(year, round_number)
    if not results:
        print(f"Qualifying job: no results yet for round {round_number}")
        return
    async with AsyncSessionLocal() as db:
        subs = await _active_subscribers(db)
        if subs:
            await send_qualifying_results_email(
                subs, {"results": results, "round": round_number, "year": year}, db
            )
            print(f"Qualifying results sent to {len(subs)} subscribers")


async def _send_sprint(year: int, round_number: int):
    results = get_sprint_results(year, round_number)
    if not results:
        print(f"Sprint job: no results yet for round {round_number}")
        return
    async with AsyncSessionLocal() as db:
        subs = await _active_subscribers(db)
        if subs:
            await send_sprint_results_email(
                subs, {"results": results, "round": round_number, "year": year}, db
            )
            print(f"Sprint results sent to {len(subs)} subscribers")
        
    for key in ("driver_standings", "constructor_standings", "current_race_weekend"):
        await cache_invalidate(key) # Invalidate current standings in cache


async def _send_race(year: int, round_number: int):
    results = get_race_results(year, round_number)
    if not results:
        print(f"Race job: no results yet for round {round_number}")
        return
    async with AsyncSessionLocal() as db:
        subs = await _active_subscribers(db)
        if subs:
            await send_race_results_email(
                subs, {"results": results, "round": round_number, "year": year}, db
            )
            print(f"Race results sent to {len(subs)} subscribers")
    
    for key in ("driver_standings", "constructor_standings", "current_race_weekend"):
        await cache_invalidate(key) # Invalidate current standings in cache


# THURSDAY SCHEDULE CHECKER
async def job_thursday_check():
    print(f"Thursday check => {datetime.now(timezone.utc).strftime('%d %b %Y')}")
    schedule = await get_current_season_schedule()
    race = _race_week(schedule)

    if not race:
        print("Not a race weekend")
        return

    year = datetime.now(timezone.utc).year
    round_number = race["round"]
    is_sprint = race.get("is_sprint", False)
    print(f"  Race weekend: {race['name']} => Round {round_number} (sprint={is_sprint})")

    # Send pre-race email
    try:
        data = await get_pre_race_package(year, round_number)
        async with AsyncSessionLocal() as db:
            subs = await _active_subscribers(db)
            if subs:
                await send_pre_race_email(subs, data, db)
                print(f"  Pre-race email sent to {len(subs)} subscribers")
    except Exception as e:
        print(f"  Pre-race email error: {e}")

    # Schedule result emails for the weekend
    if is_sprint:
        sprint_start = _session_start(race, "Sprint")
        if sprint_start:
            _schedule_job(_send_sprint, _send_at(sprint_start, "Sprint"),
                          f"sprint_{round_number}", [year, round_number])

        sprint_quali_start = _session_start(race, "Sprint Shootout") \
                          or _session_start(race, "Sprint Qualifying")
        if sprint_quali_start:
            _schedule_job(_send_qualifying, _send_at(sprint_quali_start, "Qualifying"),
                          f"sprint_quali_{round_number}", [year, round_number])

    quali_start = _session_start(race, "Qualifying")
    if quali_start:
        _schedule_job(_send_qualifying, _send_at(quali_start, "Qualifying"),
                      f"quali_{round_number}", [year, round_number])

    race_start = _session_start(race, "Race")
    if race_start:
        _schedule_job(_send_race, _send_at(race_start, "Race"),
                      f"race_{round_number}", [year, round_number])


def start_scheduler():
    scheduler.add_job(
        job_thursday_check,
        trigger=CronTrigger(day_of_week="thu", hour=17, minute=0, timezone="UTC"),
        id="thursday_check",
        replace_existing=True,
    )
    scheduler.start()