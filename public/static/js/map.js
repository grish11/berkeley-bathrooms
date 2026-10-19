/* Berkeley Bathrooms — the map.
 *
 * This is all of the JavaScript in the project. Its whole job is:
 *   1. read the building data that Flask embedded in the page
 *   2. create a MapLibre map centred on campus
 *   3. drop one pin per building
 *
 * Everything else -- scores, tiers, access states -- is computed in Python.
 * Keeping it that way means there is only one place where the rules live.
 *
 * Why MapLibre GL JS rather than Leaflet: vector tiles. Leaflet was drawing
 * pre-rendered raster image tiles, which look flat and go blurry between zoom
 * levels. MapLibre renders the map from vector data in the browser with WebGL,
 * so text stays sharp, zooming is smooth, and the map can rotate and tilt.
 * MapLibre is the open-source fork of Mapbox GL JS and needs no account or
 * access token.
 *
 * Docs: https://maplibre.org/maplibre-gl-js/docs/
 */

// MapLibre v6 ships as an ES module only -- there is no UMD build, so unlike
// Leaflet's global `L` it has to be imported. That is why index.html loads
// this file with <script type="module">.
//
// Note the `* as` form. MapLibre's module has no *default* export, only named
// ones (Map, Marker, Popup, ...), so `import maplibregl from "..."` silently
// gives you undefined and the first `maplibregl.Map(...)` throws. Importing
// the whole namespace gives an object holding all the named exports, which
// keeps the familiar `maplibregl.Thing` spelling used throughout the docs.
import * as maplibregl from "https://unpkg.com/maplibre-gl@6.14.0/dist/maplibre-gl.mjs";

// Fallback view, used only if there are no buildings to fit the map around.
// Note the order: MapLibre takes coordinates as [longitude, latitude] -- the
// opposite of Leaflet and of most of what you read elsewhere. Getting it
// backwards puts your map in Antarctica.
const CAMPUS_CENTER = [-122.2585, 37.8719];
const INITIAL_ZOOM = 15.5;

// The basemap. OpenFreeMap serves OpenStreetMap-derived vector tiles for free
// with no API key or account. https://openfreemap.org/
//
// "positron" is the pale, low-contrast style. A muted basemap is the right
// choice here because from Phase 5 the pin color carries real information
// (the building's tier) -- a busy, colorful map would fight those pins for
// attention. Swap the last path segment to try the alternatives:
//   positron  pale grey, minimal labels  (current)
//   bright    full color, OSM-like
//   liberty   full color, closest to a typical street map
const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

// How each gender value is written out. The outline colour is a quick cue,
// but the word is what makes it unambiguous -- see style.css.
const GENDER_LABELS = {
  men: "Men's",
  women: "Women's",
  all_gender: "All-gender",
};

// Dot color lives in style.css (.building-dot). Phase 5 will vary it per
// building by its tier, at which point it moves back in here.

// --- 1. Read the data Flask put in the page -------------------------------
//
// index.html rendered a <script type="application/json"> block containing the
// buildings list. Because its type is not JavaScript, the browser left it
// alone as text; JSON.parse turns that text into real JS objects.
const buildings = JSON.parse(
  document.getElementById("buildings-data").textContent,
);

// --- 2. Create the map ----------------------------------------------------
//
// https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/
const map = new maplibregl.Map({
  container: "map", // id of the <div> to draw into
  style: MAP_STYLE,
  center: CAMPUS_CENTER,
  zoom: INITIAL_ZOOM,
  attributionControl: false, // replaced below with one that has our credit
});

// Zoom buttons and a compass. The compass appears because the map can be
// rotated (right-click drag, or two-finger twist on a phone).
map.addControl(new maplibregl.NavigationControl(), "top-right");

// OpenFreeMap requires visible credit, and it supplies the text itself: the
// style's source points at a TileJSON which carries the attribution string,
// and MapLibre reads it from there. So no custom text is passed here --
// adding one would print the same credit twice, joined by a "|".
//
// The only reason this control is created by hand (with attributionControl
// false on the map above) is compact: true, which collapses the credit to an
// (i) button on narrow screens instead of a long line across the map.
map.addControl(new maplibregl.AttributionControl({ compact: true }));

// --- 3. Helpers for building the popup and the dialog ---------------------
//
// Everything below builds DOM nodes and sets .textContent rather than pasting
// strings of HTML. textContent treats its input as plain text, so a stray "<"
// in a building name or a review can never be interpreted as markup.

/** A <p> (or any tag) carrying plain text. */
function textEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text;
  return el;
}

/** The hours source: a clickable link when it is a URL, plain text otherwise. */
function sourceEl(source) {
  const wrap = document.createElement("p");
  wrap.className = "popup-source";
  wrap.append("Source: ");

  if (source.startsWith("http")) {
    const a = document.createElement("a");
    // Only the host, so a long library URL does not blow out the popup width.
    a.textContent = new URL(source).hostname.replace(/^www\./, "");
    a.href = source;
    a.target = "_blank";
    a.rel = "noopener";
    wrap.append(a);
  } else {
    wrap.append(source);
  }
  return wrap;
}

/** Fill the dialog with one bathroom's details and show it. */
function openBathroom(bathroom, building) {
  const body = document.getElementById("bathroom-dialog-body");
  body.replaceChildren();

  body.append(textEl("h2", "dialog-title", building.name));

  const where = [GENDER_LABELS[bathroom.gender] ?? bathroom.gender];
  where.push(`Floor ${bathroom.floor}`);
  if (bathroom.single_restroom) where.push("single restroom");
  body.append(textEl("p", "dialog-where", where.join(" · ")));

  body.append(textEl("p", "dialog-directions", bathroom.directions));

  // review is optional: a bathroom can be photographed before it is rated.
  if (bathroom.review) {
    body.append(textEl("p", "dialog-review", bathroom.review));
  }

  // Hero photo first, then any extras that help you find the place.
  const gallery = document.createElement("div");
  gallery.className = "dialog-gallery";
  for (const file of [bathroom.hero_photo, ...bathroom.extra_photos]) {
    const img = document.createElement("img");
    img.src = `/static/photos/${file}`;
    img.alt = `${building.name}, floor ${bathroom.floor}`;
    img.loading = "lazy";
    gallery.append(img);
  }
  body.append(gallery);

  if (bathroom.date_rated) {
    body.append(textEl("p", "dialog-date", `Rated ${bathroom.date_rated}`));
  }

  // Putting the id in the URL makes a single bathroom linkable and shareable,
  // and makes the browser's back button close the dialog. Phase 7's rankings
  // will link to these same addresses.
  if (location.hash !== `#${bathroom.id}`) {
    history.pushState(null, "", `#${bathroom.id}`);
  }

  const dialog = document.getElementById("bathroom-dialog");
  if (!dialog.open) dialog.showModal();
}

/** Close the dialog and drop the bathroom id from the URL. */
function closeBathroom() {
  const dialog = document.getElementById("bathroom-dialog");
  if (dialog.open) dialog.close();
  if (location.hash) history.pushState(null, "", location.pathname);
}

/** Build the popup shown when a building dot is clicked. */
function buildingPopupContent(building) {
  const root = document.createElement("div");
  root.className = "popup";

  root.append(textEl("h3", "popup-name", building.name));

  // hours_display is [] when no hours are published, which is true for most
  // campus buildings. Saying so is honest; showing "Closed" would not be.
  if (building.hours_display.length > 0) {
    const list = document.createElement("ul");
    list.className = "popup-hours";
    for (const line of building.hours_display) {
      list.append(textEl("li", null, line));
    }
    root.append(list);
  } else {
    root.append(textEl("p", "popup-no-hours", "Hours not posted"));
  }

  root.append(sourceEl(building.hours_source));

  if (building.bathrooms.length === 0) {
    root.append(textEl("p", "popup-none", "No bathrooms rated here yet"));
    return root;
  }

  const count = building.bathrooms.length;
  root.append(textEl("p", "popup-count",
    `${count} bathroom${count === 1 ? "" : "s"} · tap a photo for details`));

  const strip = document.createElement("div");
  strip.className = "popup-photos";
  for (const bathroom of building.bathrooms) {
    const button = document.createElement("button");
    button.type = "button";
    // The gender class is what colours the outline -- see style.css.
    button.className = `popup-photo gender-${bathroom.gender}`;
    button.title = `${GENDER_LABELS[bathroom.gender] ?? ""} · Floor ${bathroom.floor}`;

    const img = document.createElement("img");
    img.src = `/static/photos/${bathroom.hero_photo}`;
    img.alt = `${building.name}, floor ${bathroom.floor}`;
    img.loading = "lazy";

    button.append(img, textEl("span", "popup-photo-floor", `Floor ${bathroom.floor}`));
    button.addEventListener("click", () => openBathroom(bathroom, building));
    strip.append(button);
  }
  root.append(strip);

  return root;
}

// --- 4. One dot per building ----------------------------------------------

for (const building of buildings) {
  // A plain dot rather than MapLibre's default teardrop pin. With 120
  // buildings on screen, big pins overlap into an unreadable pile; small dots
  // stay distinct. Passing `element` replaces MapLibre's default marker
  // graphic entirely, and the styling lives in .building-dot in style.css.
  const dot = document.createElement("div");
  // Blue when there is at least one bathroom here, grey when there is not --
  // so the map shows at a glance where there is something to look at. The
  // colours live in style.css.
  dot.className = building.bathrooms.length > 0
    ? "building-dot"
    : "building-dot is-unrated";

  const popup = new maplibregl.Popup({ offset: 12, maxWidth: "300px" })
    .setDOMContent(buildingPopupContent(building));

  new maplibregl.Marker({ element: dot, anchor: "center" })
    .setLngLat([building.lng, building.lat]) // again: lng first
    .setPopup(popup)
    .addTo(map);
}

// Zoom the map so every building is visible, rather than trusting a
// hardcoded zoom that would go stale as buildings are added.
// LngLatBounds grows to contain each coordinate it is given.
if (buildings.length > 0) {
  const bounds = new maplibregl.LngLatBounds();
  for (const b of buildings) bounds.extend([b.lng, b.lat]);
  map.fitBounds(bounds, { padding: 40, duration: 0 });
}

// --- 5. Opening a bathroom straight from the URL --------------------------

/** Find a bathroom by id across every building. */
function findBathroom(id) {
  for (const building of buildings) {
    const match = building.bathrooms.find((b) => b.id === id);
    if (match) return { bathroom: match, building };
  }
  return null;
}

/** Show whatever the current URL points at: a bathroom, or nothing. */
function syncFromHash() {
  const id = location.hash.slice(1);
  const found = id ? findBathroom(id) : null;

  if (found) {
    openBathroom(found.bathroom, found.building);
  } else {
    const dialog = document.getElementById("bathroom-dialog");
    if (dialog.open) dialog.close();
  }
}

// popstate fires on back/forward, so the back button closes the dialog.
window.addEventListener("popstate", syncFromHash);
document.getElementById("bathroom-dialog-close")
  .addEventListener("click", closeBathroom);
// <dialog> fires `close` for Escape too, so the URL is tidied either way.
document.getElementById("bathroom-dialog")
  .addEventListener("close", () => {
    if (location.hash) history.pushState(null, "", location.pathname);
  });

// Opening /#wheeler-hall-4th-floor directly goes straight to that bathroom.
syncFromHash();
