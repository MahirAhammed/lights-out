import resend
from jinja2 import Environment, FileSystemLoader
from config import settings
from database import AsyncSessionLocal
from models import EmailLog, Subscriber
from sqlalchemy.ext.asyncio import AsyncSession

resend.api_key = settings.resend_api_key
jinja = Environment(loader = FileSystemLoader("templates/"), autoescape = True)

async def _send_email(
    to: str,
    subject: str,
    template: str,
    context: dict,
    db: AsyncSession,
    email_type: str,
    race_name: str | None = None
):
    html = jinja.get_template(template).render(**context)
    resend_id = None
    status = "sent"
    error = None

    try:
        response = resend.Emails.send({
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        resend_id = response.get("id")

    except Exception as e:
        status = "failed"
        error = str(e)
    finally:
        db.add(EmailLog(
            subscriber_email = to,
            email_type = email_type,
            race_name = race_name,
            status = status,
            error_message = error
        ))
        await db.commit()

def _unsub_url(token: str) -> str:
    return f"{settings.api_base_url}/subscribers/unsubscribe?token={token}"

# EMAILS
async def send_verification_email(to: str, name: str, token: str):
    verification_url = f"{settings.api_base_url}/subscribers/verify?token={token}"
    async with AsyncSessionLocal() as db:
        await _send_email(
            to = to, subject="Confirm your LightsOut subscription",
            template= "verify.html",
            context = {"name": name, "verify_url": verification_url},
            db = db, email_type = "verify"
        )

async def send_welcome_email(to: str, name: str, unsubscribe_token: str, db: AsyncSession):
    await _send_email(
        to=to, subject="Welcome to LightsOut",
        template="welcome.html",
        context={"name": name, "unsubscribe_url": _unsub_url(unsubscribe_token)},
        db=db, email_type="welcome"
    )

async def send_pre_race_email(subscribers: list[Subscriber], data: dict, db: AsyncSession):
    race_name = data["track"].get("official_name", "Next Race")
    for sub in subscribers:
        if sub.pref_pre_race:
            await _send_email(
                to=sub.email,
                subject=f"Race Weekend Preview: {race_name}",
                template="pre_race.html",
                context={**data, "subscriber_name": sub.name, "unsubscribe_url": _unsub_url(sub.unsubscribe_token)},
                db=db, email_type="pre_race", race_name=race_name
            )

async def send_qualifying_results_email(subscribers: list[Subscriber], data: dict, db: AsyncSession):
    race_name = data.get("race_name", f"Round {data.get('round', '')}")
    for sub in subscribers:
        if sub.pref_qualifying:
            await _send_email(
                to=sub.email,
                subject=f"Qualifying Results: {race_name}",
                template="qualifying.html",
                context={**data, "subscriber_name": sub.name, "unsubscribe_url": _unsub_url(sub.unsubscribe_token)},
                db=db, email_type="qualifying", race_name=race_name
            )

async def send_race_results_email(subscribers: list[Subscriber], data: dict, db: AsyncSession):
    race_name = data.get("race_name", f"Round {data.get('round', '')}")
    for sub in subscribers:
        if sub.pref_race:
            await _send_email(
                to=sub.email,
                subject=f"Race Results: {race_name}",
                template="race_results.html",
                context={**data, "subscriber_name": sub.name, "unsubscribe_url": _unsub_url(sub.unsubscribe_token)},
                db=db, email_type="race", race_name=race_name
            )

async def send_sprint_quali_results_email(subscribers: list[Subscriber], data, db):
    race_name = data.get("race_name", f"Round {data.get('round', '')}")
    for sub in subscribers:
        if sub.pref_sprint:
            await _send_email(
                sub.email,
                f"Sprint Shootout: {race_name}",
                "qualifying.html",
                {**data, "is_sprint": True, "subscriber_name": sub.name, "unsubscribe_url": _unsub_url(sub.unsubscribe_token)},
                db, "sprint_quali",
            )

async def send_sprint_results_email(subscribers: list[Subscriber], data: dict, db: AsyncSession):
    race_name = data.get("race_name", f"Round {data.get('round', '')}")
    for sub in subscribers:
        if sub.pref_sprint:
            await _send_email(
                sub.email,
                f"Sprint Results: {race_name}",
                "race_results.html",
                {**data, "is_sprint": True, "subscriber_name": sub.name, "unsubscribe_url": _unsub_url(sub.unsubscribe_token)},
                db, "sprint", race_name,
            )

# ONE TIME EMAILS
async def send_one_time_email(to: str, email_type: str, db: AsyncSession):
    from f1_data import (get_driver_standings, get_constructor_standings, get_current_season_schedule)
    from datetime import datetime, timezone
    from constants import NATIONAL_FLAGS

    year = datetime.now(timezone.utc).year

    if email_type == "standings":
        driver_standings = await get_driver_standings(year)
        constructor_standings = await get_constructor_standings(year)
        await _send_email(
            to=to, subject=f"F1 {year} Championship Standings",
            template="standings.html",
            context={
                "driver_standings": driver_standings,
                "constructor_standings": constructor_standings,
                "year": year,
                "total_rounds": 24,
                "last_round": driver_standings[0].get("round", "?") if driver_standings else "?"
            },
            db=db, email_type="one_time_standings"
        )

    elif email_type == "schedule":
        schedule = get_current_season_schedule()
        now = datetime.now(timezone.utc)
        next_set = False
        races = []
        for s in schedule:
            # Parse race datetime
            try:
                race_date = datetime.fromisoformat(s["race_date"].replace("Z", "+00:00"))
            except ValueError:
                race_date = None

            is_past = race_date < now if race_date else False
            is_next = (not is_past) and (not next_set)
            if is_next:
                next_set = True

            country_flag = NATIONAL_FLAGS.get(s["country"], "🏁")
            races.append({
                **s,
                "is_past": is_past,
                "is_next": is_next,
                "flag": country_flag,
                "race_date_fmt": race_date.strftime("%-d %b") if race_date else "TBC",
                "race_time_fmt": race_date.strftime("%H:%M UTC") if race_date else "",
            })

        await _send_email(
            to=to, subject=f"F1 {year} Full Season Schedule",
            template="schedule.html",
            context={"schedule": races, "year": year},
            db=db, email_type="one_time_schedule"
        )


# ADMIN
async def send_custom_email(to_list: list[str], subject: str, html_body: str, db: AsyncSession):
    for to in to_list:
        resend_id = None
        status    = "sent"
        error     = None
        try:
            response = resend.Emails.send({
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html_body,
            })
            resend_id = response.get("id")
        except Exception as e:
            status = "failed"
            error = str(e)
        finally:
            db.add(EmailLog(subscriber_email=to, email_type="custom", resend_id=resend_id, status=status, error_message=error))
    
    await db.commit()