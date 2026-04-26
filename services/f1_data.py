import fastf1
import httpx
import asyncio
import os
from datetime import datetime, timezone
from utils.cache import cache_get, cache_set
from utils.constants import FLAGS, CONSTRUCTOR_COLOURS, CACHE_TTL
from utils.time_utils import format_lap_time

cache_dir = "/tmp/fastf1"
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"

def _parse_event_sessions(event) -> dict:
    sessions = []
    for i in range(1, 6):
        name = event.get(f"Session{i}", "")
        date = event.get(f"Session{i}Date", None)
        if name and str(date) != "NaT" and date is not None:
            sessions.append({"name": name, "date": str(date)})
    is_sprint = any("sprint" in s["name"].lower() for s in sessions)
    return {"sessions": sessions, "is_sprint": is_sprint}


async def get_current_season_schedule() -> list[dict]:
    cached = await cache_get("schedule")
    if cached is not None:
        return cached

    year = datetime.now(timezone.utc).year
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
    await cache_set("schedule", races, CACHE_TTL["schedule"])
    return races


def _get_circuit_history(location: str, current_year: int, max_years: int = 20) -> dict | None:
    try:
        current_event      = fastf1.get_event(current_year, location)
        present_location = current_event["Location"]
        present_country = current_event["Country"]
    except Exception:
        present_location = None
        present_country = None

    previous_results = [] # list of (year, session) 
    for year in range(current_year - 1, current_year - 1 - max_years, -1):
        try:
            event   = fastf1.get_event(year, location)
            is_match = (event["Location"] in present_location or present_location in event["Location"])
           
            if not is_match and event["Country"] != present_country :
                continue

            session = fastf1.get_session(year, event["RoundNumber"], "R")
            session.load(laps= len(previous_results) == 0 , telemetry= False, weather= False, messages= False)
            if not session.results.empty:
                previous_results.append((year, session))
                if len(previous_results) == 5:
                    break
        except Exception:
            continue
 
    if not previous_results:
        return None

    most_recent_year, race_session = previous_results[0]
    
    quali_session = None
    try:
        qs = fastf1.get_session(most_recent_year, race_session.event["RoundNumber"], "Q")
        qs.load(laps=False, telemetry=False, weather=False, messages=False)
        quali_session = qs if not qs.results.empty else None
    except Exception:
        pass
 
    pole = None
    if quali_session:
        try:
            q_results = quali_session.results
            if not q_results.empty:
                pole_row = q_results.iloc[0]
                pole = {
                    "driver": pole_row["FullName"],
                    "abbreviation": pole_row["Abbreviation"],
                    "flag": FLAGS.get(pole_row.get("Nationality", ""), "🏳️"),
                    "time": format_lap_time(pole_row.get("Q3")),
                }
        except Exception:
            pass
    
    results = race_session.results
    winner_row = results.iloc[0]
    recent_winners = []
    for yr, sess in previous_results:
        if sess.results.empty:
            continue
        w = sess.results.iloc[0]
        name = w["FullName"]
        recent_winners.append({
            "year":   yr,
            "driver": name,
            "team":   w["TeamName"],
        })

    corners    = None
    total_laps = None
    try:
        info = race_session.get_circuit_info()
        if info is not None:
            corners = len(info.corners)
    except Exception:
        pass
    if not race_session.laps.empty:
        total_laps = int(race_session.laps["LapNumber"].max())
    
    return {
        "year": most_recent_year,
        "last_winner": {
            "driver": winner_row["FullName"], 
            "team": winner_row["TeamName"], 
            "flag": FLAGS.get(winner_row.get("Nationality", ""), "🏳️")
        },
        "last_pole": pole,
        "corners": corners,
        "total_laps": total_laps,
        "recent_winners": recent_winners,
    }


async def get_track_info(year: int, round_number: int) -> dict:
    event = fastf1.get_event(year, round_number)
    session_info = _parse_event_sessions(event)
    return {
        "name": event["EventName"],
        "official_name": event.get("OfficialEventName", event["EventName"]),
        "country": event["Country"],
        "location": event["Location"],
        "round": int(event["RoundNumber"]),
        "is_sprint": session_info["is_sprint"],
        "sessions": session_info["sessions"],
        "history": _get_circuit_history(event["Location"], year)
    }


async def get_driver_standings(year: int) -> list[dict]:
    cached = await cache_get("driver_standings")
    if cached is not None:
        return cached

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
            last_round = int(r.json()["MRData"]["StandingsTable"]["round"])

        table = []
        for entry in standings:
            nationality = entry["Driver"].get("nationality", "")
            table.append({
                "position": int(entry["position"]),
                "driver": entry['Driver']['familyName'],
                "nationality": nationality,
                "team_colour": CONSTRUCTOR_COLOURS.get(
                               entry["Constructors"][0]["constructorId"] if entry["Constructors"] else "", "#444"
                           ),
                "team": entry["Constructors"][0]["name"] if entry["Constructors"] else "",
                "points": float(entry["points"]),
            })

        result = {
            "standings": table,
            "last_round": last_round
        }
        await cache_set("driver_standings", result, CACHE_TTL["driver_standings"])
        return result
    except Exception:
        return []


async def get_constructor_standings(year: int) -> list[dict]:
    cached = await cache_get("constructor_standings")
    if cached is not None:
        return cached
    
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
        table = []
        for entry in standings:
            table.append({
                "position": int(entry["position"]),
                "team": entry["Constructor"]["name"],
                "points": float(entry["points"]),
                "colour": CONSTRUCTOR_COLOURS.get(entry["Constructor"]["constructorId"], "#444"),
            })

        await cache_set("constructor_standings", table, CACHE_TTL["constructor_standings"])
        return table
    except Exception:
        return []


def get_race_results(year: int, round_number: int) -> list[dict]:
    try:
        session = fastf1.get_session(year, round_number, "Race")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results
        race_results = []
        for _, row in results.iterrows():
            gridPos = int(row["GridPosition"]) if row.get("GridPosition") else 0
            finalPos = int(row["Position"])
            race_results.append({
                "position": finalPos,
                "driver": row["BroadcastName"],
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "teamColor": row.get("TeamColor", ""),
                "image": row.get("HeadshotUrl", ""),
                "time": format_lap_time(row["Time"]),
                "race_time":     format_lap_time(row["Time"]) if int(row["Position"]) == 1 else None,
                "status": row["Status"],
                "lapped": row["Status"],
                "points": float(row["Points"]) if row["Points"] else 0,
                "grid_position": gridPos,
                "pos_delta": gridPos - finalPos
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
            gridPos = int(row["GridPosition"]) if row.get("GridPosition") else 0
            finalPos = int(row["Position"])
            sprint_results.append({
                "position": finalPos,
                "driver": row["FullName"],
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "teamColor": row.get("TeamColor", ""),
                "image": row.get("HeadshotUrl", ""),
                "time": format_lap_time(row["Time"]),
                "race_time":     format_lap_time(row["Time"]) if int(row["Position"]) == 1 else None,
                "status": row["Status"],
                "lapped": row["Status"],
                "points": float(row["Points"]) if row["Points"] else 0,
                "grid_position": gridPos,
                "pos_delta": gridPos - finalPos
            })
        return sprint_results
    except Exception:
        return []


def get_qualifying_results(year: int, round_number: int) -> list[dict]:
    try:
        session = fastf1.get_session(year, round_number, "Qualifying")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results.to_dict('records')
        pole_time = results[0].get("Q3")
        quali_results = []

        for row in results:
            gap_to_pole = ""
            if row.get("Position") > 1 and row.get("Q3") and pole_time:
                gap = row["Q3"] - pole_time
                gap_to_pole = f"{gap.total_seconds():.3f}"

            quali_results.append({
                "position": int(row["Position"]),
                "driver": row["FullName"],
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "teamColor": row["TeamColor"],
                "image": row["HeadshotUrl"],
                "q1": format_lap_time(row["Q1"]),
                "q2": format_lap_time(row["Q2"]),
                "q3": format_lap_time(row["Q3"]),
                "gap_to_pole": gap_to_pole
            })
        return {
            "results": quali_results, 
            "race_name": session.event['EventName']
        }
    except Exception:
        return []


async def get_pre_race_package(year: int, round_number: int) -> dict:
    track, driver_standings, constructor_standings = await asyncio.gather(
        get_track_info(year, round_number),
        get_driver_standings(year),
        get_constructor_standings(year),
    )
    gap = None
    driver_standings = driver_standings["standings"]
    if len(driver_standings) >= 2:
        gap = {
            "leader":      driver_standings[0]["driver"],
            "second":      driver_standings[1]["driver"],
            "points_gap":  int(driver_standings[0]["points"] - driver_standings[1]["points"]),
            "rounds_left": 24 - track["round"],
        }

    return {
        "track": track,
        "driver_standings": driver_standings,
        "constructor_standings": constructor_standings,
        "championship_gap": gap
    }