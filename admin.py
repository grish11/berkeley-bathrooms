"""The /add form for putting a new bathroom on the map.

THIS IS A LOCAL TOOL. app.py only registers it when running in debug mode, so
it does not exist on the deployed site. That is deliberate and important:

  1. It writes files. A form that saves uploads and edits JSON, reachable by
     anyone on the internet, is a way to fill someone's server with whatever
     a stranger feels like uploading.
  2. It could not work deployed anyway. A Vercel Function has a read-only
     filesystem, so neither the photo nor the JSON edit could be saved.

So the workflow is: run the server locally, add bathrooms through the form,
then commit the JSON and photos it produced.
"""

from __future__ import annotations

import datetime
import json

from flask import flash, redirect, render_template, request, url_for

import data
import photos
import tiers


def _write_bathrooms(bathrooms: list[dict]) -> None:
    """Save bathrooms.json, formatted the same way it is edited by hand."""
    path = data.DATA_DIR / "bathrooms.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bathrooms, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _read_ratings(form, errors: list[str]) -> dict | None:
    """Pull the nine category ratings off the submitted form.

    Ratings are all-or-nothing. Leave every box empty and you get a bathroom
    with no ratings -- the normal state for one photographed today and judged
    later, which data.py already treats as valid. Fill them all in and they
    are saved. Filling in *some* is almost always a half-finished form rather
    than an intention, so it is reported rather than quietly saved.

    Returns the ratings dict, or None for "not rated". Anything wrong is
    appended to `errors` and None comes back.
    """
    ratings: dict[str, int] = {}
    blank: list[str] = []

    for category in data.RATING_CATEGORIES:
        raw = form.get(f"rating_{category}", "").strip()

        if not raw:
            blank.append(category)
            continue

        try:
            value = int(raw)
        except ValueError:
            errors.append(f"{category.replace('_', ' ').title()} must be a whole number 1-10.")
            continue

        if not 1 <= value <= 10:
            errors.append(f"{category.replace('_', ' ').title()} = {value} must be between 1 and 10.")
        else:
            ratings[category] = value

    if not ratings:
        return None  # nothing filled in: a bathroom awaiting judgement

    if blank:
        missing = ", ".join(c.replace("_", " ") for c in blank)
        errors.append(
            f"Either rate every category or none of them -- still empty: {missing}."
        )
        return None

    return ratings


def register(app):
    """Attach the /add routes to the app. Called only in debug mode."""

    @app.route("/add")
    def add_form():
        buildings = sorted(data.load_buildings(), key=lambda b: b["name"].lower())
        return render_template(
            "add.html",
            buildings=buildings,
            genders=data.GENDERS,
            categories=data.RATING_CATEGORIES,
            tiers=tiers.TIERS,
            today=datetime.date.today().isoformat(),
        )

    @app.post("/add")
    def add_submit():
        buildings = data.load_buildings()
        bathrooms = data.load_bathrooms(buildings)

        building_id = request.form.get("building_id", "").strip()
        floor = request.form.get("floor", "").strip()
        directions = request.form.get("directions", "").strip()
        gender = request.form.get("gender", "").strip()
        single_restroom = request.form.get("single_restroom") == "on"
        review = request.form.get("review", "").strip()
        date_rated = request.form.get("date_rated", "").strip()
        hero = request.files.get("hero_photo")

        # Checked here rather than left to data.py's validation, because a
        # person is filling this in and should be told what is wrong while the
        # form is still in front of them -- not by the server refusing to boot.
        errors = []
        known_ids = {b["id"] for b in buildings}
        if building_id not in known_ids:
            errors.append("Pick a building from the list.")
        if not floor:
            errors.append("Floor is required -- '1', '4', 'Basement'.")
        if not directions:
            errors.append("Say how to find it once inside.")
        if gender not in data.GENDERS:
            errors.append("Pick which room this is.")
        if hero is None or not hero.filename:
            errors.append("A hero photo is required -- it is what shows on the map.")

        # Appends its own problems to `errors`; returns None when unrated.
        ratings = _read_ratings(request.form, errors)

        if date_rated:
            try:
                datetime.date.fromisoformat(date_rated)
            except ValueError:
                errors.append(f"Date rated {date_rated!r} must be written YYYY-MM-DD.")

        if errors:
            for message in errors:
                flash(message, "error")
            return redirect(url_for("add_form"))

        stem = photos.slugify(f"{building_id}-{floor}")
        bathroom_id = stem
        existing_ids = {b["id"] for b in bathrooms}
        suffix = 2
        while bathroom_id in existing_ids:
            bathroom_id = f"{stem}-{suffix}"
            suffix += 1

        try:
            hero_name = photos.save_upload(hero, f"{bathroom_id}-hero")
            extra_names = [
                photos.save_upload(f, f"{bathroom_id}-{i + 1}")
                for i, f in enumerate(request.files.getlist("extra_photos"))
                if f and f.filename
            ]
        except photos.PhotoError as exc:
            flash(str(exc), "error")
            return redirect(url_for("add_form"))

        # No ratings or review yet -- those are added later by editing the
        # JSON, and data.py treats them as optional for exactly this reason.
        entry = {
            "id": bathroom_id,
            "building_id": building_id,
            "floor": floor,
            "directions": directions,
            "single_restroom": single_restroom,
            "gender": gender,
            "hero_photo": hero_name,
            "extra_photos": extra_names,
        }

        # Only written when actually supplied. data.py treats all three as
        # optional, so an unrated bathroom stays a clean entry with no empty
        # keys to tidy up later.
        if ratings:
            entry["ratings"] = ratings
        if review:
            entry["review"] = review
        if date_rated:
            entry["date_rated"] = date_rated

        bathrooms.append(entry)
        _write_bathrooms(bathrooms)

        building_name = next(b["name"] for b in buildings if b["id"] == building_id)
        if ratings:
            score = tiers.overall_score(ratings)
            tier = tiers.tier_for_score(score)
            flash(
                f"Added {building_name}, floor {floor} -- {score}/10, {tier['name']}.",
                "ok",
            )
        else:
            flash(
                f"Added {building_name}, floor {floor}. No ratings yet.",
                "ok",
            )
        return redirect(url_for("add_form"))
