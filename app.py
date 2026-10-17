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


@app.route("/")
def index():
    """The map page. Phase 2 puts an actual Leaflet map here."""
    return render_template("index.html")
