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


# Load and validate the JSON once, at startup, rather than on every request.
# If there is a typo in data/buildings.json this raises data.DataError here --
# the server refuses to start and prints exactly what is wrong, which is much
# easier to debug than a half-broken map.
#
# Loading at import time also suits Vercel: the module is imported once when a
# function instance starts, so the files are read once and reused across
# requests rather than re-parsed each time.
BUILDINGS = data.load_buildings()


@app.route("/")
def index():
    """The map page.

    Passes the buildings to the template, which embeds them in the page for
    the MapLibre code in public/static/js/map.js to read.
    """
    return render_template("index.html", buildings=BUILDINGS)
