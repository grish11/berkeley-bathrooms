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

### Current time

Access is evaluated against the current time in **America/Los_Angeles**, not
the visitor's own timezone. Someone checking this page from New York sees
whether the bathroom is open *in Berkeley*. (Implemented in Phase 6.)

---

## `data/bathrooms.json`

**Not yet created — Phase 3.** The planned shape, from the project spec:

| Field | Type | Notes |
|---|---|---|
| `id` | string | Unique, URL-safe, same rules as a building `id` |
| `building_id` | string | Must match an `id` in `buildings.json` |
| `floor` | ? | To be decided |
| `directions` | string | How to actually find it |
| `single_stall` | boolean | A yes/no attribute, **not** a rating |
| `hero_photo` | string | Filename in `public/static/photos/` |
| `extra_photos` | list of strings | Entrance, hallway — shots that help you find it |
| `ratings` | object | Nine categories, each 1–10 |
| `review` | string | The roast |
| `date_rated` | string | Date format to be decided |

The nine rating categories, where **10 is always best**: Peace, Cleanliness,
Privacy, Echo (10 = silent), Stall Gaps, Toilet Paper, Smell, Temperature,
Busyness (10 = empty).

This table gets filled in properly when the file is created.
