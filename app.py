"""Berkeley Bathrooms — Flask application.

This file is the whole backend for now. It lives in the project root and
exposes a module-level variable named `app`, because that is exactly what
Vercel's Python runtime auto-detects as the entrypoint, and also what
Flask's own CLI auto-discovers (so `flask run` needs no --app flag).

Docs:
  Flask app object    https://flask.palletsprojects.com/en/stable/api/#flask.Flask
  Flask CLI discovery https://flask.palletsprojects.com/en/stable/cli/
  Vercel entrypoints  https://vercel.com/docs/frameworks/backend/flask
"""

from flask import Flask, render_template

import data
import hours
import tiers

# Why static files are configured this way:
#
# Vercel's docs say Flask's static folder "should not be used for static files
# on Vercel" -- instead you put them in public/, which Vercel's CDN serves
# directly at the URL root, never touching Python. So public/static/css/x.css
# is live at /static/css/x.css in production.
#
# To make local development match that exactly, we point Flask's static folder
# at the same directory and keep the same URL prefix. Result: the URL
# /static/css/style.css works identically in both places, and
# url_for('static', ...) never has to change when we deploy.
#
# The leading slash on static_url_path is required -- Werkzeug rejects a URL
# rule that doesn't start with one.
app = Flask(__name__, static_folder="public/static", static_url_path="/static")

# Only used to sign the flash messages the local /add form shows. Nothing
# secret is stored in a session, and the form does not exist in production,
# so a fixed development value is fine here.
app.secret_key = "berkeley-bathrooms-local-dev"


# Load and validate the JSON once, at startup, rather than on every request.
# If there is a typo in data/buildings.json this raises data.DataError here --
# the server refuses to start and prints exactly what is wrong, which is much
# easier to debug than a half-broken map.
#
# Loading at import time also suits Vercel: the module is imported once when a
# function instance starts, so the files are read once and reused across
# requests rather than re-parsed each time.
BUILDINGS = data.load_buildings()
BATHROOMS = data.load_bathrooms(BUILDINGS)


def load_everything():
    """Read and validate both JSON files, returning (buildings, bathrooms).

    Flask's --debug reloader only watches *Python* files. Without re-reading
    here, editing data/buildings.json or data/bathrooms.json would change
    nothing until you stopped and restarted the server by hand -- the old data
    stays in memory and it looks like your edit was ignored.

    So in debug mode we re-read on every request: edit the JSON, hit refresh,
    see the change. A typo still raises data.DataError, which the debugger
    shows in the browser with the same clear message.

    In production the files cannot change while the app is running, so the
    data loaded at import is reused and nothing is re-parsed per request.
    """
    if app.debug:
        buildings = data.load_buildings()
        return buildings, data.load_bathrooms(buildings)
    return BUILDINGS, BATHROOMS


def build_map_data():
    """Buildings, each with its readable hours and its bathrooms attached.

    The template embeds this for map.js to read. Doing the joining and the
    hours formatting here rather than in JavaScript keeps to the rule in
    docs/ARCHITECTURE.md that all the rules live in Python -- the browser only
    draws what it is given.
    """
    buildings, bathrooms = load_everything()

    by_building = {}
    for bathroom in bathrooms:
        # A copy with the score and tier worked out, rather than editing the
        # loaded data in place: in production that list is reused for every
        # request, so mutating it would stack these keys up over time.
        score = tiers.overall_score(bathroom.get("ratings"))
        rated = {
            **bathroom,
            "score": score,
            "tier": tiers.tier_for_score(score),
        }
        by_building.setdefault(rated["building_id"], []).append(rated)

    result = []
    for building in buildings:
        mine = by_building.get(building["id"], [])
        result.append({
            **building,
            # [] means no hours are published, which is true for most campus
            # buildings. The popup says so rather than implying "closed".
            "hours_display": hours.format_schedule(building["access_schedule"]),
            "bathrooms": mine,
            # The building's tier is its BEST bathroom's tier, and is what
            # colours its dot. None when nothing here is rated yet.
            "tier": tiers.best_tier(mine),
        })
    return result


# The /add form is a LOCAL tool for adding bathrooms, and is only attached
# while developing. It writes photos and edits JSON, which a deployed site
# must not let strangers do -- and could not do anyway, since a Vercel
# Function's filesystem is read-only. Not registering the route at all is a
# stronger guarantee than checking a flag inside it.
if app.debug:
    import admin

    admin.register(app)


# How many entries each hall shows. Small enough that both are a glance
# rather than a scroll; raise them as the list of bathrooms grows.
HALL_OF_FAME_SIZE = 10
HALL_OF_SHAME_SIZE = 5

# Only a score of 4 or below is shameful. Without this the hall of shame is
# just "the bottom five", which on a short list means a perfectly decent
# bathroom gets pilloried for being less good than nine others.
HALL_OF_SHAME_MAX_SCORE = 4


def ranked_bathrooms():
    """Every rated bathroom, best first, each knowing its building.

    The map groups bathrooms under buildings; the halls rank them against each
    other regardless of building, so this flattens that back out. Bathrooms
    with no ratings yet are left out entirely -- they have no score to rank.
    """
    buildings, bathrooms = load_everything()
    names = {b["id"]: b["name"] for b in buildings}

    rated = []
    for bathroom in bathrooms:
        score = tiers.overall_score(bathroom.get("ratings"))
        if score is None:
            continue
        rated.append({
            **bathroom,
            "score": score,
            "tier": tiers.tier_for_score(score),
            "building_name": names.get(bathroom["building_id"], bathroom["building_id"]),
        })

    # Highest score first. The building name is the tie-breaker, so bathrooms
    # on the same score come out in a stable, readable order rather than
    # whatever order the file happened to list them in.
    rated.sort(key=lambda b: (-b["score"], b["building_name"], b["floor"]))
    return rated


@app.route("/hall-of-fame")
def hall_of_fame():
    """The best bathrooms on campus, and the worst.

    Both halls come from one sorted list: the fame list is the front of it and
    the shame list is the back, reversed so the worst bathroom is first --
    the hall of shame counts down to the bottom.
    """
    rated = ranked_bathrooms()

    fame = rated[:HALL_OF_FAME_SIZE]
    # Anything already in the fame list is excluded, so a short list cannot
    # put the same bathroom in both halls.
    famous = {b["id"] for b in fame}
    shame = [
        b for b in reversed(rated)
        if b["id"] not in famous and b["score"] <= HALL_OF_SHAME_MAX_SCORE
    ][:HALL_OF_SHAME_SIZE]

    return render_template(
        "hall_of_fame.html",
        fame=fame,
        shame=shame,
        total=len(rated),
    )


@app.route("/")
def index():
    """The map page.

    Passes the buildings -- with hours and bathrooms attached -- to the
    template, which embeds them in the page for public/static/js/map.js.
    """
    return render_template("index.html", buildings=build_map_data())
