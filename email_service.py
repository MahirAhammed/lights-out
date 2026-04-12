import resend
from jinja2 import Environment, FileSystemLoader
from config import settings
from models import EmailLog
from sqlalchemy.ext.asyncio import AsyncSession

resend.api_key = settings.resend_api_key

jinja_env = Environment(loader = FileSystemLoader("templates/"), autoescape = True)

async def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict,
    db: AsyncSession,
    email_type: str,
    race_name: str | None = None
):
    template = jinja_env.get_template(template_name)
    html = template.render(**context)
    
    try:
        response = resend.Emails.send({
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        resend_id = response.get("id")
        log = EmailLog(
            subscriber_email=to,
            email_type=email_type,
            race_name=race_name,
            resend_id=resend_id,
            status="sent"
        )
    except Exception as e:
        log = EmailLog(
            subscriber_email=to,
            email_type=email_type,
            race_name=race_name,
            status="failed",
            error_message=str(e)
        )
        raise
    finally:
        db.add(log)
        await db.commit()

async def send_verification_email(to: str, name: str, token: str, db: AsyncSession):
    verification_url = f"{settings.api_base_url}/subscribers/verify?token={token}"
    await send_email(
        to=to,
        subject="Confirm your F1 updates subscription",
        template_name="verify.html",
        context={"name": name, "verify_url": verification_url},
        db=db,
        email_type="verify"
    )

async def send_welcome_email(to: str, name: str, unsubscribe_token: str, db: AsyncSession):
    unsubscribe_url = f"{settings.api_base_url}/subscribers/unsubscribe?token={unsubscribe_token}"
    await send_email(
        to=to, subject="Welcome to F1 Updates",
        template_name="welcome.html",
        context={"name": name, "unsubscribe_url": unsubscribe_url},
        db=db, email_type="welcome"
    )

async def send_pre_race_email(subscribers: list, data: dict, db: AsyncSession):
    race_name = data["track"].get("official_name", "Next Race")
    for sub in subscribers:
        if not _should_receive(sub, "pre_race"):
            continue
        unsubscribe_url = f"{settings.api_base_url}/subscribers/unsubscribe?token={sub.unsubscribe_token}"
        await send_email(
            to=sub.email,
            subject=f"Race Weekend Preview: {race_name}",
            template_name="pre_race.html",
            context={**data, "subscriber_name": sub.name, "unsubscribe_url": unsubscribe_url},
            db=db, email_type="pre_race", race_name=race_name
        )

async def send_qualifying_results(subscribers: list, data: dict, db: AsyncSession):
    race_name = data.get("race_name", "Qualifying")
    for sub in subscribers:
        if not _should_receive(sub, "qualifying"):
            continue
        unsubscribe_url = f"{settings.api_base_url}/subscribers/unsubscribe?token={sub.unsubscribe_token}"
        await send_email(
            to=sub.email,
            subject=f"Qualifying Results: {race_name}",
            template_name="qualifying.html",
            context={**data, "subscriber_name": sub.name, "unsubscribe_url": unsubscribe_url},
            db=db, email_type="qualifying", race_name=race_name
        )

async def send_race_results(subscribers: list, data: dict, db: AsyncSession):
    race_name = data.get("race_name", "Race")
    for sub in subscribers:
        if not _should_receive(sub, "race"):
            continue
        unsubscribe_url = f"{settings.api_base_url}/subscribers/unsubscribe?token={sub.unsubscribe_token}"
        await send_email(
            to=sub.email,
            subject=f"Race Results: {race_name}",
            template_name="results.html",
            context={**data, "subscriber_name": sub.name, "unsubscribe_url": unsubscribe_url},
            db=db, email_type="race", race_name=race_name
        )

async def send_custom_email(to_list: list[str], subject: str, html_body: str, db: AsyncSession):
    for to in to_list:
        try:
            response = resend.Emails.send({
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html_body,
            })
            db.add(EmailLog(subscriber_email=to, email_type="custom", resend_id=response.get("id"), status="sent"))
        except Exception as e:
            db.add(EmailLog(subscriber_email=to, email_type="custom", status="failed", error_message=str(e)))
    await db.commit()

async def send_one_time_email(to: str, email_type: str, db: AsyncSession):
    from f1_data import (get_driver_standings, get_constructor_standings, get_current_season_schedule)
    from datetime import datetime, timezone
    from constants import NATIONAL_FLAGS

    year = datetime.now().year

    if email_type == "standings":
        driver_standings = await get_driver_standings(year)
        constructor_standings = await get_constructor_standings(year)
        last_round = driver_standings[0].get("round", "?") if driver_standings else "?"
        await send_email(
            to=to, subject=f"F1 {year} Championship Standings",
            template_name="standings.html",
            context={
                "driver_standings": driver_standings,
                "constructor_standings": constructor_standings,
                "year": year,
                "total_rounds": 24,
                "last_round": last_round
            },
            db=db, email_type="one_time_standings"
        )

    elif email_type == "schedule":
        raw = get_current_season_schedule()
        now = datetime.now(timezone.utc)
        next_set = False
        races = []
        for r in raw:
            # Parse race datetime
            try:
                race_dt = datetime.fromisoformat(r["race_date"].replace("Z", "+00:00"))
            except ValueError:
                race_dt = None

            is_past = race_dt < now if race_dt else False
            is_next = (not is_past) and (not next_set)
            if is_next:
                next_set = True

            country_flag = NATIONAL_FLAGS.get(r["country"], "🏁")
            races.append({
                **r,
                "is_past": is_past,
                "is_next": is_next,
                "flag": country_flag,
                "race_date_fmt": race_dt.strftime("%-d %b") if race_dt else "TBC",
                "race_time_fmt": race_dt.strftime("%H:%M UTC") if race_dt else "",
            })

        await send_email(
            to=to, subject=f"F1 {year} Full Season Schedule",
            template_name="schedule.html",
            context={"schedule": races, "year": year},
            db=db, email_type="one_time_schedule"
        )

def _should_receive(subscriber, email_type: str) -> bool:
    prefs = {
        "pre_race":   subscriber.pref_pre_race,
        "qualifying": subscriber.pref_qualifying,
        "race":       subscriber.pref_race,
        "sprint":     subscriber.pref_sprint,
    }
    return prefs.get(email_type, True)