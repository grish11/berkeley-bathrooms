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

import json

from flask import flash, redirect, render_template, request, url_for

import data
import photos


def _write_bathrooms(bathrooms: list[dict]) -> None:
    """Save bathrooms.json, formatted the same way it is edited by hand."""
    path = data.DATA_DIR / "bathrooms.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bathrooms, f, indent=2, ensure_ascii=False)
        f.write("\n")


def register(app):
    """Attach the /add routes to the app. Called only in debug mode."""

    @app.route("/add")
    def add_form():
        buildings = sorted(data.load_buildings(), key=lambda b: b["name"].lower())
        return render_template("add.html", buildings=buildings, genders=data.GENDERS)

    @app.post("/add")
    def add_submit():
        buildings = data.load_buildings()
        bathrooms = data.load_bathrooms(buildings)

        building_id = request.form.get("building_id", "").strip()
        floor = request.form.get("floor", "").strip()
        directions = request.form.get("directions", "").strip()
        gender = request.form.get("gender", "").strip()
        single_restroom = request.form.get("single_restroom") == "on"
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
        bathrooms.append({
            "id": bathroom_id,
            "building_id": building_id,
            "floor": floor,
            "directions": directions,
            "single_restroom": single_restroom,
            "gender": gender,
            "hero_photo": hero_name,
            "extra_photos": extra_names,
        })
        _write_bathrooms(bathrooms)

        building_name = next(b["name"] for b in buildings if b["id"] == building_id)
        flash(f"Added {building_name}, floor {floor}.", "ok")
        return redirect(url_for("add_form"))
