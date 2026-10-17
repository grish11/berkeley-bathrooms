# Adding buildings and bathrooms

A practical walkthrough. For the field-by-field reference see
[DATA_FORMAT.md](DATA_FORMAT.md).

Right now only **buildings** exist. Bathrooms arrive in Phase 3 and this guide
grows to cover them.

---

## Adding a building

### 1. Get the coordinates

The pin needs latitude and longitude. Two reliable ways:

**OpenStreetMap** (same data the map itself uses, so the pin will line up with
the building outline):

1. Go to <https://www.openstreetmap.org/>
2. Search the building name, e.g. "Dwinelle Hall Berkeley"
3. Right-click the middle of the building → **Show address** — the URL now
   contains `#map=19/37.8707/-122.2606`; those two numbers are lat and lng

**Google Maps:** right-click the building → the first menu item is the
`lat, lng` pair; click it to copy.

Either way, aim for the **middle of the building**, not the street outside.
Five or six decimal places is plenty.

> Watch the signs. In Berkeley latitude is about `+37.87` and longitude is
> about `-122.26`. Longitude is **negative**. If you swap them, startup
> validation will tell you — it checks both are inside a Berkeley-shaped box.

### 2. Pick an id

Lowercase, hyphens, no spaces: `doe-library`, `dwinelle-hall`,
`valley-life-sciences`. It must be unique, and it ends up in a URL later, so
pick something you will not want to rename.

### 3. Work out the access schedule

Find the building's real hours — the campus page for the building, or the
[UC Berkeley Library hours page](https://www.lib.berkeley.edu/visit/hours) for
libraries. Then translate them into day keys and periods:

```json
"access_schedule": {
  "mon-thu": [{ "start": "08:00", "end": "22:00", "access": "open" }],
  "fri":     [{ "start": "08:00", "end": "17:00", "access": "open" }],
  "sat-sun": [{ "start": "13:00", "end": "17:00", "access": "open" }]
}
```

Rules worth remembering:

- Times are 24-hour and zero-padded: `"08:00"`, never `"8:00"` or `"8am"`.
- You never write `closed`. Anything you leave out **is** closed. No weekend
  key means shut all weekend.
- If a building is open to all during the day and card-only at night, that is
  two periods in the same list — see `moffitt-library` in the data file.

### 4. Add it to the file

Append an object to the list in `data/buildings.json`. Mind the comma between
entries, and no trailing comma after the last one — that is the most common
JSON mistake and validation will catch it with a line number.

### 5. Check your work

```bash
uv run flask run --debug
```

If anything is wrong the server **will not start**, and it prints every
problem at once, naming the building:

```
3 problem(s) found in data/buildings.json:
  - buildings[1] (Moffitt Library).lat = -122.26 is outside Berkeley (37.84 to 37.9). Are lat and lng swapped?
  - buildings[1] (Moffitt Library).access_schedule['mon-fry'] key 'mon-fry' is not a day or day range. Use one of mon, tue, wed, thu, fri, sat, sun, or a range like 'mon-fri'.
  - buildings[2] (Dwinelle Hall).id = 'doe-library' is used by more than one building
```

Fix them all, restart, and check the pin lands on the right building on the
map at <http://127.0.0.1:5000/>.

---

## Adding a bathroom

**Phase 3.** Will cover: linking it to a `building_id`, floor and directions,
the nine ratings, and writing the review.

---

## Adding photos

**Phase 8**, when the Pillow script exists. Two rules that already apply:

1. **No people in any photo.** Not in the background, not reflected in a
   mirror, not feet under a stall door. Check before you commit.
2. **Originals never get committed.** Put them in `photos_raw/` (already
   gitignored). Phone photos embed GPS coordinates and timestamps, and this
   repo is public — the Phase 8 script strips that metadata and writes clean,
   resized copies into `public/static/photos/`, which is what ships.
