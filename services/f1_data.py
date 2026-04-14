import fastf1
import httpx
import asyncio
from datetime import datetime, timezone
from utils.constants import FLAGS, CONSTRUCTOR_COLOURS

# fastf1.Cache.enable_cache("/tmp/fastf1_cache")
ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"

def _parse_event_sessions(event) -> dict:
    sessions = []
    for i in range(1, 6):
        name = event.get(f"Session{i}", "")
        date = event.get(f"Session{i}Date", None)
        if name and str(date) != "NaT" and date is not None:
            sessions.append({
                "name": name,
                "date": str(date),
            })

    is_sprint = any("sprint" in s["name"].lower() for s in sessions)

    return {"sessions": sessions, "is_sprint": is_sprint}


def get_current_season_schedule() -> list[dict]:
    year = datetime.now().year
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = []
    for _, row in schedule.iterrows():
        session_info = _parse_event_sessions(row)
        races.append({
            "round": int(row["RoundNumber"]),
            "name": row["EventName"],
            "country": row["Country"],
            "location": row["Location"],
            "official_name": row.get("OfficialEventName", row["EventName"]),
            "race_date": str(row["Session5Date"]),
            "is_sprint": session_info["is_sprint"],
            "sessions": session_info["sessions"],
        })
    return races


def get_next_race() -> dict | None:
    year = datetime.now().year
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    now = datetime.now(timezone.utc)

    upcoming = schedule[schedule["Session5Date"] > now]
    if upcoming.empty:
        return None

    row = upcoming.iloc[0]
    session_info = _parse_event_sessions(row)

    return {
        "round": int(row["RoundNumber"]),
        "name": row["EventName"],
        "country": row["Country"],
        "location": row["Location"],
        "official_name": row.get("OfficialEventName", row["EventName"]),
        "race_date": str(row["Session5Date"]),
        "is_sprint": session_info["is_sprint"],
        "sessions": session_info["sessions"],
    }


def get_track_info(year: int, round_number: int) -> dict:
    event = fastf1.get_event(year, round_number)
    session_info = _parse_event_sessions(event)

    current_race = fastf1.get_session(year, round_number, 'R')
    current_race.load(laps=True, telemetry=False, weather=False, messages=False)
    # total_laps = current_race.total_laps
    # Get corner count if available
    try:
        circuit_info = current_race.get_circuit_info()
        corner_count = len(circuit_info.corners) if circuit_info else "N/A"
    except Exception:
        corner_count = "N/A"

    last_winner = None
    lookback_years = 10
    for i in range(1, lookback_years + 1):
        try:
            prev_year = year - i
            prev_race = fastf1.get_session(prev_year, round_number, 'R')
            prev_race.load(laps=False, telemetry=False, weather=False, messages=False)
            
            # Check if this is the correct GP
            if prev_race.event['EventName'] == event['EventName']:
                winner_row = prev_race.results.iloc[0]
                last_winner = {
                    "driver": winner_row["FullName"],
                    "team": winner_row["TeamName"],
                    "year": prev_year
                }
                break # Exit loop once we find the most recent winner
        except Exception:
            continue
    return {
        "name": event["EventName"],
        "official_name": event.get("OfficialEventName", event["EventName"]),
        "country": event["Country"],
        "location": event["Location"],
        "round": int(event["RoundNumber"]),
        # "total_laps": total_laps,
        "corners": corner_count,
        "last_winner": last_winner,
        "is_sprint": session_info["is_sprint"],
        "sessions": session_info["sessions"],
    }


async def get_driver_standings(year: int) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{ERGAST_BASE}/{year}/driverStandings.json",
                timeout=10.0
            )
            r.raise_for_status()
            lists = r.json()["MRData"]["StandingsTable"]["StandingsLists"]
            if not lists:
                return []
            standings = lists[0]["DriverStandings"]
        result = []
        for entry in standings:
            nationality = entry["Driver"].get("nationality", "")
            result.append({
                "position": int(entry["position"]),
                "driver": entry['Driver']['familyName'],
                # "last_round": r.json()["MRData"]["StandingsTable"].get("round"),
                "nationality": nationality,
                "flag": FLAGS.get(nationality, "🏳️"),
                "team_colour": CONSTRUCTOR_COLOURS.get(
                               entry["Constructors"][0]["constructorId"] if entry["Constructors"] else "", "#444"
                           ),
                "team": entry["Constructors"][0]["name"] if entry["Constructors"] else "",
                "points": float(entry["points"]),
                "wins": int(entry["wins"]),
            })
        return result[:10]
    except Exception:
        return []


async def get_constructor_standings(year: int) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{ERGAST_BASE}/{year}/constructorstandings.json",
                timeout=10.0
            )
            r.raise_for_status()
            lists = r.json()["MRData"]["StandingsTable"]["StandingsLists"]
            if not lists:
                return []
            standings = lists[0]["ConstructorStandings"]
        result = []
        for entry in standings:
            result.append({
                "position": int(entry["position"]),
                "team": entry["Constructor"]["name"],
                "points": float(entry["points"]),
                "colour": CONSTRUCTOR_COLOURS.get(entry["Constructor"]["constructorId"], "#444"),
            })

        return result[:11]
    except Exception:
        return []


def get_race_results(year: int, round_number: int) -> list[dict]:
    try:
        session = fastf1.get_session(year, round_number, "Race")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results
        race_results = []
        for _, row in results.iterrows():
            race_results.append({
                "position": str(row["Position"]),
                "driver": row["FullName"],
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "time": str(row["Time"]),
                "status": row["Status"],
                "points": float(row["Points"]) if row["Points"] else 0,
            })
        return race_results
    except Exception:
        return []


def get_sprint_results(year: int, round_number: int) -> list[dict]:
    try:
        session = fastf1.get_session(year, round_number, "Sprint")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results
        sprint_results = []
        for _, row in results.iterrows():
            sprint_results.append({
                "position": str(row["Position"]),
                "driver": row["FullName"],
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "time": str(row["Time"]),
                "status": row["Status"],
                "points": float(row["Points"]) if row["Points"] else 0,
            })
        return sprint_results
    except Exception:
        return []


def get_qualifying_results(year: int, round_number: int) -> list[dict]:
    try:
        session = fastf1.get_session(year, round_number, "Qualifying")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results
        quali_results = []
        for _, row in results.iterrows():
            quali_results.append({
                "position": int(row["Position"]),
                "driver": row["FullName"],
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "q1": str(row["Q1"]) if str(row["Q1"]) != "NaT" else "-",
                "q2": str(row["Q2"]) if str(row["Q2"]) != "NaT" else "-",
                "q3": str(row["Q3"]) if str(row["Q3"]) != "NaT" else "-",
            })
        return quali_results
    except Exception:
        return []


async def get_pre_race_package(year: int, round_number: int) -> dict:
    track = get_track_info(year, round_number)
    driver_standings, constructor_standings = await asyncio.gather(
        get_driver_standings(year),
        get_constructor_standings(year),
    )
    return {
        "track": track,
        "driver_standings": driver_standings,
        "constructor_standings": constructor_standings,
    }