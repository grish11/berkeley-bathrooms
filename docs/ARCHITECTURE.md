# Architecture

How the files fit together and what happens when someone loads a page.

## File and folder structure

```
berkeley_bathrooms/
├── app.py                   # The Flask app + all routes. Vercel's entrypoint.
├── data.py                  # Loads + validates data/*.json at startup
├── pyproject.toml           # Project metadata + dependencies (managed by uv)
├── uv.lock                  # Exact pinned versions. Committed on purpose.
├── .python-version          # "3.14" — pins the interpreter locally AND on Vercel
├── .gitignore
├── README.md
├── CLAUDE.md                # Instructions for the AI assistant helping build this
│
├── data/                    # Hand-edited JSON. This is the "database".
│   ├── buildings.json       #   id, name, lat, lng, access_schedule
│   └── bathrooms.json       #   (Phase 3) id, building_id, ratings, review, photos
│
├── templates/               # Jinja (HTML) templates. Flask looks here by default.
│   ├── base.html            #   Shared layout: <head>, header, nav, footer
│   └── index.html           #   The map page; extends base.html
│
├── public/                  # Served directly by Vercel's CDN at the URL root.
│   └── static/              #   -> so this is reachable at /static/...
│       ├── css/style.css
│       ├── js/map.js        #   Leaflet setup -- the only JavaScript here
│       └── photos/          #   Compressed, EXIF-stripped bathroom photos
│
├── scripts/
│   └── compress_photos.py   # Pillow: photos_raw/ -> public/static/photos/ (Phase 8)
│
└── docs/
    ├── ARCHITECTURE.md      # This file
    ├── DATA_FORMAT.md       # Every JSON field, its type, an example
    └── ADDING_BATHROOMS.md  # Step-by-step: add a building, bathroom, photos
```

Not in git: `.venv/` (uv rebuilds it from `uv.lock`) and `photos_raw/` (the
full-resolution originals, which carry EXIF GPS data).

## Why this layout

Three constraints shaped it, and the first two come from Vercel.

**1. `app.py` must be in the root with a variable named `app`.** Vercel's Python
runtime looks for a `Flask` instance named `app` at a handful of known
filenames — `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` — in the
project root or in `src/`/`app/`. Satisfying that convention means we need no
`vercel.json` and no `api/index.py` wrapper at all. Most Flask-on-Vercel
tutorials online still show that older wrapper approach; it is no longer
necessary. As a bonus, `app.py` is also the filename Flask's own CLI
auto-discovers, so `flask run` works with no arguments.

**2. Static files go in `public/`, not Flask's `static/`.** Vercel's docs state
plainly that `app.static_folder` "should not be used for static files on
Vercel"; files in `public/` are served from the CDN instead, never reaching
Python. Because Vercel serves `public/` at the URL root, a file at
`public/static/css/style.css` is live at `/static/css/style.css`.

So that local development matches production exactly, `app.py` points Flask's
static folder at that same directory and keeps the same URL prefix:

```python
app = Flask(__name__, static_folder="public/static", static_url_path="/static")
```

The payoff: `/static/css/style.css` resolves identically in both environments,
and `url_for('static', filename=...)` needs no changes at deploy time. (The
leading slash on `static_url_path` is mandatory — Werkzeug raises
`ValueError: URL rule 'static/<path:filename>' must start with a slash.`
without it.)

**3. Flat Python files, not a package.** Phase 1 was one `app.py`; Phase 2
added `data.py` beside it. Later phases keep adding siblings rather than
nesting: `tiers.py` (the single score→tier function) and `access.py` (weekly
schedule → current access state, using `zoneinfo`). Nothing has to move when
they arrive.

**Corollary: all the rules live in Python.** Scores, tiers and access states
are computed server-side and handed to the templates already finished. The
JavaScript only draws the map. That way there is exactly one place where the
rating formula or the tier thresholds are defined.

## How a page request flows

Locally, running `uv run flask run --debug`:

```
Browser requests GET /
  │
  ├─ /static/... ?  → Flask's built-in static handler reads public/static/
  │                   and returns the file. (Dev convenience only.)
  │
  └─ otherwise     → Werkzeug matches the URL against the @app.route rules
                     │
                     └─ index() in app.py
                        │
                        └─ render_template("index.html")
                           │
                           ├─ index.html extends base.html
                           ├─ Jinja fills in {% block content %}
                           └─ url_for('static', ...) → "/static/css/style.css"
                           │
                           └─ returns HTML string
                              │
                              └─ Flask wraps it in a 200 response
```

Deployed on Vercel, one branch changes — static files never reach Python:

```
Browser requests GET /
  │
  ├─ /static/... ?  → Vercel CDN serves public/static/... directly.
  │                   Python is never invoked. This is the important difference.
  │
  └─ otherwise     → request is routed to a single Vercel Function
                     │
                     └─ the Function loads `app` from app.py and calls it
                        as a WSGI application
                        │
                        └─ ...identical to the local flow from here down
```

The whole Flask app becomes **one** Vercel Function; Vercel routes every
non-static request to it.

## Data flow

JSON is read from disk **once at startup** and rendered into templates. There
is no database and no write path — the site is read-only, and the ratings are
mine alone.

```
data/buildings.json ──→ data.load_buildings()
                          │  validates every field; raises DataError listing
                          │  all problems if anything is wrong
                          ↓
                        app.BUILDINGS  (module-level, loaded at import)
                          ↓
                        render_template("index.html", buildings=...)
                          ↓
                        {{ buildings|tojson }} embedded in a
                        <script type="application/json"> block
                          ↓
                        map.js: JSON.parse → one Leaflet marker per building
```

Loading at import time rather than per request means a typo stops the server
immediately with a readable error, and on Vercel the files are parsed once per
function instance instead of on every request.

### Why the data is embedded in the page rather than fetched

`CLAUDE.md` asks for the JavaScript to live in its own file, which rules out
putting Jinja syntax inside `map.js`. The two ways to get Python data into a
separate `.js` file are an API endpoint it fetches, or an inert
`<script type="application/json">` block in the HTML that it reads. The second
is used here: no extra route, no second network round-trip, no loading state to
handle, and the data is already in the page the moment the map initialises.
Flask's `tojson` filter escapes the output so it is safe inside a script tag.

If the data ever grows large enough that the HTML gets heavy, switching to a
`/api/buildings` route is a small, contained change.

### The read-only constraint

A deployed Vercel Function has a read-only filesystem, so the app can never
save changes back to these files. That is why community ratings (explicitly out
of scope for v1) will require a real database.

## Reference

- Flask quickstart — https://flask.palletsprojects.com/en/stable/quickstart/
- Flask CLI — https://flask.palletsprojects.com/en/stable/cli/
- Jinja template inheritance — https://jinja.palletsprojects.com/en/stable/templates/#template-inheritance
- Vercel + Flask — https://vercel.com/docs/frameworks/backend/flask
- Vercel Python runtime — https://vercel.com/docs/functions/runtimes/python
- uv projects — https://docs.astral.sh/uv/guides/projects/
- Leaflet API reference — https://leafletjs.com/reference.html
- OSM tile usage policy — https://operations.osmfoundation.org/policies/tiles/
