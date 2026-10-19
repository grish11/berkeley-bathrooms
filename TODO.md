# TODO

High-level only. Details live in the phase discussions.

## Phases

- [x] **Phase 1 — Setup.** Folders, uv, Flask hello world, public GitHub repo.
- [x] **Phase 2 — Map.** Vector map of campus (MapLibre GL JS + OpenFreeMap),
      3 sample building pins read from `buildings.json`, with startup
      validation of the JSON.
- [x] **Phase 3 — Building popup.** Hours, source, bathroom count and a hero
      photo per bathroom; clicking one opens a linkable detail dialog. Score,
      tier and the access dot are deferred to Phases 5 and 6.
- [ ] **Phase 4 — Bathroom detail view.** All photos, location, directions,
      single-restroom flag, every rating, overall score, tier, review.
- [x] **/add form.** Local-only page for adding a bathroom: building, floor,
      directions, gender, photos. Resizes and strips metadata on upload.
      Ratings and review still added by editing the JSON.
- [ ] **Phase 5 — Tiers.** Score→tier in one function. Iron → Challenger, each
      with a color, used for pins and tier text. Building tier = best bathroom.
- [ ] **Phase 6 — Access by day/time.** Weekly per-building schedule in
      America/Los_Angeles. Anything not covered counts as Closed.
- [ ] **Phase 7 — Hall of Fame / Hall of Shame.** Separate page at
      `/hall-of-fame`, ranked, entries link to detail views. Add nav.
- [ ] **Phase 8 — Photo pipeline.** Resize and compress photos before
      committing. Metadata stripping is done by hand, outside this repo.
- [ ] **Phase 9 — Deploy to Vercel.** Connect the repo, verify static paths and
      the Python version, add `excludeFiles` if the bundle gets large.

## Data to fix

- [ ] **Fill in access hours for all 169 buildings.** Every building was
      imported from OpenStreetMap with an empty `access_schedule: {}`, meaning
      "not researched yet". Work through
      [docs/HOURS_CHECKLIST.md](docs/HOURS_CHECKLIST.md). Coordinates are
      already correct and need no attention.
- [ ] **Phase 6 needs an "hours unknown" state.** An empty schedule currently
      evaluates as Closed, which would show a confident red dot for buildings
      nobody has looked up. That is a lie to visitors — it needs its own grey
      state.
- [ ] **Prune the building list.** 169 is everything plausible on campus,
      including dorms and buildings you may never rate. Delete rows from
      `data/buildings.json` that do not belong.
- [ ] Decide the `bathrooms.json` schema (Phase 3), then finish the second half
      of `docs/DATA_FORMAT.md`.

## Photo safety — do before any photo is committed

- [ ] **Strip metadata from every image before committing.** Done manually.
      Phone photos embed GPS coordinates, exact timestamps and device info, and
      this repo is public -- committing a raw photo publishes where I was and
      when. There is no script for this; it is on me every time.
- [ ] Keep originals in `photos_raw/` only — already gitignored, never commit.
- [ ] Spot-check each photo with `exiftool` and confirm it returns nothing
      before committing it.
- [ ] Re-check every photo for people before committing: background, mirror
      reflections, feet under stall doors. No people, ever.

## Docs to write

- [x] `docs/DATA_FORMAT.md` — buildings done; bathrooms section pending Phase 3
- [x] `docs/ADDING_BATHROOMS.md` — buildings done; bathrooms/photos pending
- [ ] `README.md` — intentionally empty for now
- [x] `docs/ARCHITECTURE.md`

## Later, deliberately not in v1

- [ ] Filters: single restroom only, open now, minimum tier
- [ ] "Find me peace NOW" using the visitor's location
- [ ] Check access for a chosen day/time instead of now
- [ ] Community ratings via CalNet login — needs a real database, because a
      deployed Vercel Function cannot write files
