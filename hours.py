"""Turning a building's weekly access_schedule into readable text.

The schedule in data/buildings.json is written for editing by hand, not for
reading on a page:

    {"mon-fri": [{"start": "08:00", "end": "21:00", "access": "open"}]}

This module turns that into lines a person can read:

    ["Mon-Fri  8 am - 9 pm"]

It lives in Python rather than JavaScript on purpose. docs/ARCHITECTURE.md
sets the rule that all the rules live server-side, so there is exactly one
place where "what does this schedule mean" is decided.

Phase 6 adds current_access() here -- working out whether a building is open
*right now* belongs with the code that already understands these schedules.
"""

from __future__ import annotations

import data

# Shown after the times when getting in needs more than walking through a door.
ACCESS_LABELS = {
    "open": "",
    "cal_id": " (Cal ID)",
    "card_key": " (card key)",
    "closed": " (closed)",
}

DAY_LABELS = {
    "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
    "fri": "Fri", "sat": "Sat", "sun": "Sun",
}


def _format_time(value: str) -> str:
    """'08:00' -> '8 am'.  '13:15' -> '1:15 pm'.  '24:00' -> 'midnight'.

    12-hour rather than 24-hour because this is read by students in the US,
    and the minutes are dropped when they are :00 so the common case stays
    short ("8 am", not "8:00 am").
    """
    if value in ("24:00", "00:00"):
        return "midnight"

    hour, minute = (int(part) for part in value.split(":"))
    suffix = "am" if hour < 12 else "pm"

    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12  # 12:30 rather than 0:30

    if hour == 12 and minute == 0:
        return "noon"

    if minute == 0:
        return f"{display_hour} {suffix}"
    return f"{display_hour}:{minute:02d} {suffix}"


def _format_period(period: dict) -> str:
    """One {start, end, access} as '8 am - 9 pm', or 'open 24 hours'."""
    start, end = period["start"], period["end"]
    label = ACCESS_LABELS.get(period["access"], "")

    if start == "00:00" and end == "24:00":
        return f"open 24 hours{label}"

    return f"{_format_time(start)} - {_format_time(end)}{label}"


def _periods_by_day(access_schedule: dict) -> dict[str, list[dict]]:
    """Expand the day keys so each weekday lists every period covering it.

    A day can be covered by more than one key. Main Stacks is open 9am-2am
    Mon-Thu, which is written as `mon-thu` 09:00-24:00 plus `tue-fri`
    00:00-02:00 -- so Monday appears under two keys. The periods must be
    collected together (a union), not resolved to whichever key matched first.
    """
    by_day: dict[str, list[dict]] = {day: [] for day in data.WEEKDAYS}

    for key, periods in access_schedule.items():
        for day in data.expand_day_key(key):
            by_day[day].extend(periods)

    for day, periods in by_day.items():
        by_day[day] = sorted(periods, key=lambda p: p["start"])

    return by_day


def format_schedule(access_schedule: dict) -> list[str]:
    """Render a weekly schedule as readable lines.

        >>> format_schedule({"mon-fri": [{"start": "08:00", "end": "21:00",
        ...                               "access": "open"}]})
        ['Mon-Fri  8 am - 9 pm']

    Consecutive days with identical hours are collapsed into one line, so a
    normal weekday schedule reads as a single row rather than five.

    Returns [] for an empty schedule. That means "hours not published", which
    is the case for most campus buildings -- the caller should say so rather
    than render it as closed.
    """
    if not access_schedule:
        return []

    by_day = _periods_by_day(access_schedule)

    lines: list[str] = []
    run_start: str | None = None
    run_text: str | None = None

    def flush(run_end: str) -> None:
        if run_text:  # skip runs of days with no periods at all
            days = DAY_LABELS[run_start]
            if run_start != run_end:
                days += f"-{DAY_LABELS[run_end]}"
            lines.append(f"{days}  {run_text}")

    previous_day = None
    for day in data.WEEKDAYS:
        text = ", ".join(_format_period(p) for p in by_day[day])

        if text != run_text:
            if previous_day is not None:
                flush(previous_day)
            run_start, run_text = day, text
        previous_day = day

    flush(data.WEEKDAYS[-1])
    return lines
