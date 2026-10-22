# Adding buildings and bathrooms

A practical walkthrough. For the field-by-field reference see
[DATA_FORMAT.md](DATA_FORMAT.md).

## The quick way: the `/add` form

Most of the time you do not need this guide. Run the server locally and open
<http://127.0.0.1:5000/add>:

```bash
uv run flask --app app run --debug
```

Pick the building from the dropdown, fill in floor, directions and which room
it is, choose the photos, and submit. It saves the photos — **resized and with
all metadata stripped** — and writes the entry into `data/bathrooms.json` for
you. Then commit the JSON and the new photos.

The form deliberately does not collect ratings or the review: those are
written afterwards by editing the JSON, which is what the rest of this guide
covers. The form only exists in debug mode (see
[ARCHITECTURE.md](ARCHITECTURE.md) for why).

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

**The quick way: use the form.** Run the server and open
<http://127.0.0.1:5000/add>. Pick the building, type the floor and directions,
choose which room it is, attach the photos, submit. It saves the photos and
writes the entry for you.

That page only exists while running locally. It writes files, which a deployed
site must not let strangers do — and could not do anyway, since a Vercel
Function's filesystem is read-only. So the workflow is: add bathrooms locally,
then commit the JSON and photos it produced.

Photos sent through the form are resized to 1600px and saved with **all
metadata removed**, so no GPS coordinates or timestamps reach the repo. You
still have to check there are no people in the shot.

Ratings and the review are not in the form yet; add those by editing
`data/bathrooms.json` afterwards.

### Doing it by hand instead

### 1. Take the photos

A hero shot of the room, plus any extra shots that help someone find it — the
entrance, the hallway, the door.

**No people. Ever.** Not in the background, not reflected in a mirror, not feet
under a stall door. Check every shot before it goes anywhere near the repo.

### 2. Strip the metadata and shrink it

Phone photos embed **GPS coordinates, timestamps and device info**, and this
repo is public — committing one straight off a phone publishes where you were
and when.

If you added the bathroom through the `/add` form, this is already done:
`photos.py` rebuilds each upload from its pixels alone, so no metadata
survives, and resizes it to 1600px on the long edge.

Copying a photo in by hand means doing both yourself:

```bash
exiftool -all= -overwrite_original photo.jpg   # strip everything
exiftool photo.jpg                             # confirm nothing is left
```

Shrink it too. An 8 MB phone photo makes the page slow; around 1600px on the
long edge is plenty.

Keep the original somewhere on your laptop outside this repo, and put the
cleaned copy in `public/static/photos/`.

### 3. Add the entry

Append an object to the list in `data/bathrooms.json`. See
[DATA_FORMAT.md](DATA_FORMAT.md) for every field and a full example.

The two fields worth care:

- **`building_id`** must exactly match an `id` in `buildings.json`. Look it up;
  do not guess.
- **`hero_photo`** is a bare filename, not a path.

### 4. Check it

```bash
uv run flask run --debug
```

The server refuses to start if anything is wrong, and names it:

```
3 problem(s) found in data/bathrooms.json:
  - bathrooms[0] (wheeler-hall-4th).building_id = 'wheler-hall' does not match any building in buildings.json
  - bathrooms[0] (wheeler-hall-4th).hero_photo = 'wheeler.jpg' does not exist in public/static/photos/
  - bathrooms[0] (wheeler-hall-4th).ratings.privacy is missing
```

Then click that building's dot on the map: the popup should show its hours and
your photo. Click the photo for the full detail.

You can also go straight there with `http://127.0.0.1:5000/#<bathroom-id>`.
