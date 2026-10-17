# Data format

Reference for every field in `data/buildings.json` and `data/bathrooms.json`:
its type, whether it's required, and an example.

**Not written yet — this lands in Phase 2**, alongside the JSON files it
describes. Writing it now would mean documenting a schema we haven't agreed on.

The starting point from `CLAUDE.md`:

- `buildings.json` — `id`, `name`, `lat`, `lng`, `access_schedule`
- `bathrooms.json` — `id`, `building_id`, `floor`, `directions`, `single_stall`,
  `hero_photo`, `extra_photos`, `ratings`, `review`, `date_rated`

See [ARCHITECTURE.md](ARCHITECTURE.md) for how these files are loaded.
