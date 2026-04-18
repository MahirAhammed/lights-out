from datetime import datetime, timedelta, timezone
import pytz

def format_lap_time(td) -> str:
    if td is None or str(td) in ("NaT", "nan", "None"):
        return "-"
    try:
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        total_seconds =total_seconds % 3600
        minutes  = int(total_seconds // 60)
        seconds  = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:06.3f}"
    except Exception:
        return str(td)


def format_schedule_time(dt_str: str, timezone: str = "UTC") -> str:
    if not dt_str or dt_str in ("NaT", "None", "nan"):
        return "TBC"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        tz = pytz.timezone(timezone)
        local_dt = dt.astimezone(tz)
        return local_dt.strftime("%-d %b | %H:%M")
    except Exception:
        return dt_str


def timezone_label(timezone: str) -> str:
    try:
        now = datetime.now(pytz.timezone(timezone))
        abbr   = now.strftime("%Z")        # SAST, CET, GMT etc.
        offset = now.strftime("%z")        # +0200
        sign   = offset[0]
        hours  = int(offset[1:3])
        mins   = int(offset[3:5])
        utc    = f"UTC {sign}{hours}" if mins == 0 else f"UTC {sign}{hours}:{mins:02d}"
        return f"{abbr} [{utc}]"
    except Exception:
        return timezone