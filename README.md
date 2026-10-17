# Berkeley Bathrooms

> Because you deserve to poop in peace.

An interactive map of UC Berkeley's campus (plus a few spots just off it) showing
bathrooms that I personally visited, photographed, and rated. One pin per
building, colored by tier. Click a pin to see the bathrooms inside it; click a
photo to see the full breakdown, including a review I probably should have
toned down.

**Status:** Phase 1 — Flask skeleton. The map arrives in Phase 2.

## The rules

- **No people in photos. Ever.** Not in the background, not reflected in a
  mirror, not a shoe under a stall door. If someone is in the shot, it does not
  go in the repo.
- Original photos stay on my laptop in `photos_raw/` (gitignored). Only
  stripped, resized copies are committed, because phone photos carry EXIF GPS
  coordinates and this repo is public.

## Run it locally

Requires [uv](https://docs.astral.sh/uv/). Python 3.14 is pinned in
`.python-version`; uv will fetch it if you don't have it.

```bash
uv sync          # create .venv and install dependencies from uv.lock
uv run flask run --debug
```

Then open <http://127.0.0.1:5000/>.

No `--app` flag is needed: Flask auto-discovers a file named `app.py`
([docs](https://flask.palletsprojects.com/en/stable/cli/)). `--debug` turns on
auto-reload and the in-browser error page, so you can leave the server running
while you edit.

To add a dependency, use `uv add <package>` rather than editing
`pyproject.toml` by hand — it resolves and updates `uv.lock` in one step.

## Adding bathrooms

Everything is hand-edited JSON in `data/`. See
[docs/ADDING_BATHROOMS.md](docs/ADDING_BATHROOMS.md) for the walkthrough and
[docs/DATA_FORMAT.md](docs/DATA_FORMAT.md) for every field.

## How it's built

Flask + Jinja templates on the backend, Leaflet with OpenStreetMap tiles for the
map, plain JSON files for data (no database), and Pillow for photo compression.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Deploy

Hosted on [Vercel](https://vercel.com/docs/frameworks/backend/flask), deployed
automatically from this GitHub repo. Vercel needs no config file here: it
auto-detects the `app` object in `app.py` as the entrypoint, installs
dependencies from `pyproject.toml`, and serves everything under `public/` from
its CDN. Pushing to `master` deploys.

## Found something wrong?

Hours change, bathrooms get renovated, standards drift.
[Open an issue](https://github.com/grish11/berkeley-bathrooms/issues/new).
