# Data format

Every field in the JSON files under `data/`, its type, and an example.

All of this is validated at startup by `data.py`. If something is wrong the
server refuses to start and prints every problem it found, naming the building
and the field. You never get a half-broken map.

---

## `data/buildings.json`

A **list** of building objects. One entry per building, one pin per building on
the map.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique. Lowercase letters, digits, `-`, `_`. Must start with a letter or digit. Becomes part of a URL, so no spaces or capitals. |
| `name` | string | yes | Shown on the map pin and popup. Write it how a student would say it. |
| `lat` | number | yes | Latitude, decimal degrees. Must be between 37.84 and 37.90 (Berkeley). |
| `lng` | number | yes | Longitude, decimal degrees. **Negative** here. Must be between -122.30 and -122.22. |
| `access_schedule` | object | yes | Weekly opening schedule. See below. |
| `hours_source` | string | **yes** | Where the hours came from: a URL, `"Google Maps"`, or `"Google Maps — no hours listed"`. |

`hours_source` matters because this site publishes hours to other people. When
one turns out to be wrong, the first question is where it came from. It is
**required**, including for buildings with no hours — there the useful fact is
that someone checked, and where. That stops the same building being researched
twice, and stops an unsourced time being published.

Where a source is weaker than an official campus page, say so in the string —
e.g. a third-party aggregator, or a reservations page whose hours may differ
from building access.

The `lat`/`lng` bounds exist to catch the most common mistake: swapping the two
values. If you do, you get a clear error instead of a pin in the Indian Ocean.

### Example

```json
{
  "id": "doe-library",
  "name": "Doe Memorial Library",
  "lat": 37.8721871,
  "lng": -122.2595133,
  "access_schedule": {
    "mon-thu": [{ "start": "08:00", "end": "22:00", "access": "open" }],
    "fri": [{ "start": "08:00", "end": "17:00", "access": "open" }],
    "sat-sun": [{ "start": "13:00", "end": "17:00", "access": "open" }]
  }
}
```

---

## `access_schedule`

An object mapping **day keys** to a **list of time periods**.

### Day keys

A key is either a single day or an inclusive range:

- Single day: `"mon"`, `"tue"`, `"wed"`, `"thu"`, `"fri"`, `"sat"`, `"sun"`
- Range: `"mon-fri"`, `"sat-sun"`, `"mon-thu"`, `"tue-thu"` …

Ranges may wrap past Sunday, so `"sat-mon"` means Saturday, Sunday **and**
Monday. Use whichever grouping matches reality — a library with different
Friday and Saturday hours gets three keys, not two.

### Time periods

Each period is an object:

| Field | Type | Notes |
|---|---|---|
| `start` | string | 24-hour `"HH:MM"`, zero-padded. `"08:00"`, not `"8:00"`. |
| `end` | string | Same format. `"24:00"` is allowed, meaning midnight. |
| `access` | string | One of `open`, `cal_id`, `card_key`, `closed`. |

### Access states

| Value | Meaning | Dot color on the popup |
|---|---|---|
| `open` | Anyone can walk in | Green |
| `cal_id` | Need a Cal ID card | Yellow |
| `card_key` | Need a department card key | Yellow |
| `closed` | Locked | Red |

`cal_id` and `card_key` are both yellow because from a visitor's point of view
the question is just "can I get in with a card?" — but they are stored
separately because *which* card matters to you.

### Anything not listed is Closed

You do not write `closed` periods. A time not covered by any period counts as
closed automatically. Dwinelle Hall has no `sat` or `sun` key at all, which is
how you say "shut all weekend":

```json
"access_schedule": {
  "mon-fri": [
    { "start": "07:00", "end": "18:00", "access": "open" },
    { "start": "18:00", "end": "22:00", "access": "card_key" }
  ]
}
```

Use an explicit `closed` period only when you want to punch a hole in a day
that is otherwise open.

### An empty schedule means "not researched yet"

`"access_schedule": {}` is valid and is what every imported building starts
with. It currently evaluates the same as closed, because nothing is covered.

This is a placeholder, not a fact — it does **not** mean the building is
actually shut. [HOURS_CHECKLIST.md](HOURS_CHECKLIST.md) tracks which buildings
still need real hours. Worth keeping in mind for Phase 6: showing a confident
red "Closed" dot for a building nobody has looked up yet would be telling
visitors something untrue, so unresearched buildings probably need their own
state (grey "hours unknown") rather than being lumped in with Closed.

### Current time

Access is evaluated against the current time in **America/Los_Angeles**, not
the visitor's own timezone. Someone checking this page from New York sees
whether the bathroom is open *in Berkeley*. (Implemented in Phase 6.)

---

## `data/bathrooms.json`

A **list** of bathroom objects. Optional — if the file is missing, the map
simply has no bathrooms on it.

| Field | Type | Notes |
|---|---|---|
| `id` | string | Unique. Same rules as a building `id`. Becomes the link `/#<id>`. |
| `building_id` | string | **Must match an `id` in `buildings.json`.** |
| `floor` | string | Free text: `"1"`, `"4"`, `"Basement"`, `"Mezzanine"`. |
| `directions` | string | How to find it once you are inside. |
| `single_restroom` | boolean | The whole room is yours, with a door that locks — not one stall among several. A yes/no attribute, **not** a rating. |
| `hero_photo` | string | Bare filename in `public/static/photos/`. Not a path. |
| `extra_photos` | list of strings | May be `[]`. Entrance and hallway shots that help you find it. |
| `ratings` | object | All nine categories, each a whole number 1–10. |
| `review` | string | The roast. |
| `date_rated` | string | ISO `YYYY-MM-DD`. |

### Ratings

Nine categories, all required. **10 is always best** — 10 echo means silent,
10 busyness means empty:

`peace`, `cleanliness`, `privacy`, `echo`, `stall_gaps`, `toilet_paper`,
`smell`, `temperature`, `busyness`

`single_restroom` is deliberately not here: it is an attribute, not a judgement.

### Example

```json
{
  "id": "wheeler-hall-150-4th-floor",
  "building_id": "wheeler-hall",
  "floor": "4",
  "directions": "North stairwell to the top, then left at the end of the hall.",
  "single_restroom": true,
  "hero_photo": "wheeler_floor4.jpg",
  "extra_photos": [],
  "ratings": {
    "peace": 9, "cleanliness": 8, "privacy": 10, "echo": 7, "stall_gaps": 10,
    "toilet_paper": 6, "smell": 8, "temperature": 7, "busyness": 9
  },
  "review": "Marble walls and nobody around. Worth the four flights.",
  "date_rated": "2026-10-17"
}
```

### What is checked at startup

Beyond types, validation catches the mistakes that would otherwise fail
silently:

- **`building_id` must match a real building.** A typo here would attach the
  bathroom to nothing, so it would vanish from the map with no error at all.
- **Every photo file must exist** in `public/static/photos/`. A misspelled
  filename becomes a named error instead of a broken image in the browser.
- **Every rating category present, each 1–10.** A misspelled category is
  reported by name, with the valid list.
- **`date_rated` must parse** as `YYYY-MM-DD`.

### Photos

Store a bare filename, not a path — everything lives in
`public/static/photos/`. Two rules:

1. **No people in any photo.** Not in the background, not reflected in a
   mirror, not feet under a stall door.
2. **Strip metadata before committing.** Phone photos embed GPS coordinates,
   timestamps and device info, and this repo is public. This is done by hand —
   there is no script for it.
