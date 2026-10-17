"""Loading and validating the JSON data files in data/.

These JSON files are the whole "database". They are edited by hand, which
means typos are inevitable -- so everything here exists to catch a mistake at
startup and tell you exactly where it is, rather than letting a bad value
reach the map and produce a blank page or a pin in the ocean.

Validation collects *every* problem and reports them together, so you can fix
a batch of typos in one pass instead of rerunning once per mistake.

Docs:
  json          https://docs.python.org/3/library/json.html
  pathlib.Path  https://docs.python.org/3/library/pathlib.html
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Resolve data/ relative to THIS file, not the current working directory.
# Vercel's docs note that a deployed function's working directory is the
# project root, which would also work -- but __file__ is correct either way.
DATA_DIR = Path(__file__).parent / "data"

# The four access states from the spec. Anything else is a typo.
ACCESS_STATES = ("open", "cal_id", "card_key", "closed")

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# ids end up in URLs (Phase 4), so keep them to URL-safe characters.
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Rough bounding box around Berkeley. A coordinate outside this is almost
# always a swapped lat/lng, which is the single most common mistake here.
BERKELEY_BOX = {"lat": (37.84, 37.90), "lng": (-122.30, -122.22)}


class DataError(Exception):
    """One or more data files are malformed.

    The message lists every problem found, one per line.
    """


def _fail(filename: str, problems: list[str]) -> None:
    """Raise a DataError listing all problems in a readable block."""
    lines = "\n".join(f"  - {p}" for p in problems)
    raise DataError(
        f"\n\n{len(problems)} problem(s) found in data/{filename}:\n{lines}\n"
    )


def expand_day_key(key: str) -> tuple[str, ...]:
    """Turn an access_schedule key into the weekdays it covers.

    Accepts a single day ("fri") or an inclusive range ("mon-fri"), so you can
    write one entry for a stretch of identical days and a separate entry for a
    day that differs. Ranges may wrap around the end of the week ("sat-mon").

        >>> expand_day_key("fri")
        ('fri',)
        >>> expand_day_key("mon-wed")
        ('mon', 'tue', 'wed')

    Raises ValueError on an unrecognised key.
    """
    key = key.strip().lower()

    if key in WEEKDAYS:
        return (key,)

    if "-" in key:
        start, _, end = key.partition("-")
        if start in WEEKDAYS and end in WEEKDAYS:
            i, j = WEEKDAYS.index(start), WEEKDAYS.index(end)
            if i <= j:
                return WEEKDAYS[i : j + 1]
            # Wraps past Sunday, e.g. "sat-mon".
            return WEEKDAYS[i:] + WEEKDAYS[: j + 1]

    raise ValueError(
        f"{key!r} is not a day or day range. "
        f"Use one of {', '.join(WEEKDAYS)}, or a range like 'mon-fri'."
    )


def _check_access_schedule(where: str, schedule: object, problems: list[str]) -> None:
    """Validate the shape of one building's access_schedule.

    Phase 2 only checks that it is well formed; Phase 6 is what actually reads
    it to work out whether a building is open right now.
    """
    if not isinstance(schedule, dict):
        problems.append(f"{where}.access_schedule must be an object, got {type(schedule).__name__}")
        return

    for key, periods in schedule.items():
        try:
            expand_day_key(key)
        except ValueError as exc:
            problems.append(f"{where}.access_schedule key {exc}")
            # Keep checking the periods under this key anyway, so one run
            # reports every problem instead of one layer at a time.

        if not isinstance(periods, list):
            problems.append(f"{where}.access_schedule['{key}'] must be a list of periods")
            continue

        for i, period in enumerate(periods):
            at = f"{where}.access_schedule['{key}'][{i}]"

            if not isinstance(period, dict):
                problems.append(f"{at} must be an object with start, end and access")
                continue

            for field in ("start", "end"):
                value = period.get(field)
                if not isinstance(value, str):
                    problems.append(f"{at}.{field} is missing")
                # "24:00" is allowed as an end time, meaning midnight.
                elif not TIME_PATTERN.match(value) and not (field == "end" and value == "24:00"):
                    problems.append(f"{at}.{field} = {value!r} is not a 24-hour HH:MM time")

            access = period.get("access")
            if access not in ACCESS_STATES:
                problems.append(
                    f"{at}.access = {access!r} is not one of {', '.join(ACCESS_STATES)}"
                )


def _check_building(i: int, building: object, seen_ids: set[str], problems: list[str]) -> None:
    """Validate one entry from buildings.json."""
    where = f"buildings[{i}]"

    if not isinstance(building, dict):
        problems.append(f"{where} must be an object, got {type(building).__name__}")
        return

    # Prefer naming the building in later messages, so errors are findable.
    name = building.get("name")
    if isinstance(name, str) and name:
        where = f"buildings[{i}] ({name})"
    else:
        problems.append(f"{where}.name is missing or empty")

    building_id = building.get("id")
    if not isinstance(building_id, str) or not building_id:
        problems.append(f"{where}.id is missing or empty")
    elif not ID_PATTERN.match(building_id):
        problems.append(
            f"{where}.id = {building_id!r} must be lowercase letters, digits, "
            f"hyphens or underscores (it becomes part of a URL)"
        )
    elif building_id in seen_ids:
        problems.append(f"{where}.id = {building_id!r} is used by more than one building")
    else:
        seen_ids.add(building_id)

    for field, (low, high) in (("lat", BERKELEY_BOX["lat"]), ("lng", BERKELEY_BOX["lng"])):
        value = building.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            problems.append(f"{where}.{field} is missing or not a number")
        elif not low <= value <= high:
            problems.append(
                f"{where}.{field} = {value} is outside Berkeley ({low} to {high}). "
                f"Are lat and lng swapped?"
            )

    if "access_schedule" not in building:
        problems.append(f"{where}.access_schedule is missing")
    else:
        _check_access_schedule(where, building["access_schedule"], problems)


def load_buildings() -> list[dict]:
    """Read and validate data/buildings.json.

    Returns the list of buildings. Raises DataError with a readable summary if
    the file is missing, is not valid JSON, or has bad values.
    """
    path = DATA_DIR / "buildings.json"

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise DataError(f"\n\nMissing data file: {path}\n") from None

    try:
        buildings = json.loads(raw)
    except json.JSONDecodeError as exc:
        # JSONDecodeError knows the line and column, which is the most useful
        # thing to show for a stray comma or a missing quote.
        raise DataError(
            f"\n\ndata/buildings.json is not valid JSON:\n"
            f"  - {exc.msg} at line {exc.lineno}, column {exc.colno}\n"
        ) from None

    problems: list[str] = []

    if not isinstance(buildings, list):
        _fail("buildings.json", [f"the file must contain a list of buildings, got {type(buildings).__name__}"])

    seen_ids: set[str] = set()
    for i, building in enumerate(buildings):
        _check_building(i, building, seen_ids, problems)

    if problems:
        _fail("buildings.json", problems)

    return buildings
