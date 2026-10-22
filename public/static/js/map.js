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

// The nine rating categories, in the order they are shown, with the wording
// used on screen. 10 is always best, which is why two of these read oddly
// until you know that: 10 Echo means silent, 10 Busyness means empty.
const RATING_LABELS = {
  peace: "Peace",
  cleanliness: "Cleanliness",
  privacy: "Privacy",
  echo: "Echo",
  stall_gaps: "Stall gaps",
  toilet_paper: "Toilet paper",
  smell: "Smell",
  temperature: "Temperature",
  busyness: "Busyness",
};

// Where "Report an issue" sends people. GitHub issues are doing the job a
// database would otherwise do here: anyone with a GitHub account can send a
// correction, suggest a bathroom, or supply a building's real hours, and
// moderating it means closing an issue. No accounts to build, nothing to host.
const REPO_URL = "https://github.com/grish11/berkeley-bathrooms";

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

/** "8/10 · Master", coloured by the tier. Returns null when unrated.
 *
 * The score and the tier name both arrive from Python already worked out --
 * tiers.py owns both rules, so nothing here has to know the cutoffs. */
function scoreEl(bathroom, className) {
  if (bathroom.score === null || !bathroom.tier) return null;

  const el = document.createElement("p");
  el.className = className;

  const score = textEl("span", "score-number", `${bathroom.score}/10`);
  const tier = textEl("span", "tier-name", bathroom.tier.name);
  // Challenger is the only tier painted with a gradient; the rest are a flat
  // colour. Both are set through the same variable so the CSS stays one rule.
  tier.style.setProperty("--tier", bathroom.tier.gradient ?? bathroom.tier.color);
  if (bathroom.tier.gradient) tier.classList.add("tier-gradient");

  el.append(score, document.createTextNode(" · "), tier);
  return el;
}

/** Open one photo on its own, filling the screen. */
function openPhoto(src, alt) {
  const dialog = document.getElementById("photo-dialog");
  const img = document.getElementById("photo-dialog-img");
  img.src = src;
  img.alt = alt;
  if (!dialog.open) dialog.showModal();
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

  const score = scoreEl(bathroom, "dialog-score");
  if (score) body.append(score);

  body.append(textEl("p", "dialog-directions", bathroom.directions));

  // Hero photo first, then any extras that help you find the place. The strip
  // scrolls sideways rather than stacking, so several photos are comparable at
  // a glance instead of one screen apart; click one to see it full size.
  const gallery = document.createElement("div");
  gallery.className = "dialog-gallery";
  for (const file of [bathroom.hero_photo, ...bathroom.extra_photos]) {
    const src = `/static/photos/${file}`;
    const alt = `${building.name}, floor ${bathroom.floor}`;

    // A button, not a bare image: keyboard-reachable and announced as a
    // control, the same reasoning as the popup's hero photos.
    const button = document.createElement("button");
    button.type = "button";
    button.className = "gallery-photo";
    button.title = "Click to enlarge";

    const img = document.createElement("img");
    img.src = src;
    img.alt = alt;
    img.loading = "lazy";

    button.append(img);
    button.addEventListener("click", () => openPhoto(src, alt));
    gallery.append(button);
  }
  body.append(gallery);

  // Every category, so you can see WHY the overall score came out where it
  // did. Skipped entirely for a bathroom that has not been rated yet.
  if (bathroom.ratings) {
    const list = document.createElement("dl");
    list.className = "dialog-ratings";
    for (const [key, label] of Object.entries(RATING_LABELS)) {
      const value = bathroom.ratings[key];
      if (value === undefined) continue;

      list.append(textEl("dt", null, label));

      const dd = document.createElement("dd");
      // A bar as well as the number: nine numbers in a column are hard to
      // compare, nine bars are not.
      const bar = document.createElement("span");
      bar.className = "rating-bar";
      bar.style.setProperty("--fill", `${value * 10}%`);
      dd.append(bar, textEl("span", "rating-value", `${value}/10`));
      list.append(dd);
    }
    body.append(list);
  }

  // The review goes last, under the evidence it is explaining.
  if (bathroom.review) {
    const reviews = document.createElement("section");
    reviews.className = "dialog-reviews";
    reviews.append(textEl("h3", "reviews-heading", "Reviews"));

    const entry = document.createElement("article");
    entry.className = "review";
    entry.append(textEl("p", "review-author", "Creator"));
    entry.append(textEl("p", "review-text", bathroom.review));
    if (bathroom.date_rated) {
      entry.append(textEl("p", "review-date", bathroom.date_rated));
    }
    reviews.append(entry);
    body.append(reviews);
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

/** A "Report an issue" link, prefilled with the building it came from.
 *
 * GitHub reads `title` and `body` out of the query string and fills the new
 * issue form in with them, so the reporter starts with the building already
 * identified and a prompt for what is useful to say.
 * https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue
 *
 * encodeURIComponent is what makes that safe: a building name with an "&" or
 * a "#" in it would otherwise be read as the end of the parameter.
 */
function reportEl(building) {
  const title = `${building.name}: `;
  const body = [
    `Building: ${building.name} (\`${building.id}\`)`,
    "",
    "What is wrong or missing? For example:",
    "- The hours are wrong, or there are none listed yet",
    "- There is a bathroom here that is not on the map",
    "- Something about an existing bathroom is out of date",
    "",
    "If you are sending hours, please say where you found them.",
  ].join("\n");

  const link = document.createElement("a");
  link.className = "popup-report";
  link.href =
    `${REPO_URL}/issues/new` +
    `?title=${encodeURIComponent(title)}` +
    `&body=${encodeURIComponent(body)}`;
  link.target = "_blank";
  link.rel = "noopener";
  link.textContent = "Report an issue";
  return link;
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
    root.append(reportEl(building));
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

    const caption = textEl("span", "popup-photo-floor", `Floor ${bathroom.floor}`);
    button.append(img, caption);

    const score = scoreEl(bathroom, "popup-score");
    if (score) button.append(score);
    button.addEventListener("click", () => openBathroom(bathroom, building));
    strip.append(button);
  }
  root.append(strip);
  root.append(reportEl(building));

  return root;
}

// --- 4. One dot per building ----------------------------------------------

for (const building of buildings) {
  // A plain dot rather than MapLibre's default teardrop pin. With 120
  // buildings on screen, big pins overlap into an unreadable pile; small dots
  // stay distinct. Passing `element` replaces MapLibre's default marker
  // graphic entirely, and the styling lives in .building-dot in style.css.
  const dot = document.createElement("div");
  dot.className = "building-dot";

  if (building.bathrooms.length === 0) {
    // Nothing here yet -- grey, so the map shows at a glance where there is
    // something to look at. Everything else stays Berkeley Blue: the tier
    // colour belongs to a bathroom, and a dot is a whole building.
    dot.classList.add("is-unrated");
  } else if (building.tier) {
    // Not painted on, but worth having on hover.
    dot.title = `${building.name} — ${building.tier.name}`;
  }

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

// Clicking the enlarged photo -- picture or backdrop -- closes it. Escape
// already works, because <dialog> handles that itself.
const photoDialog = document.getElementById("photo-dialog");
photoDialog.addEventListener("click", () => photoDialog.close());
// Dropping the src frees the decoded image rather than keeping every photo
// you have ever enlarged in memory for the life of the page.
photoDialog.addEventListener("close", () => {
  document.getElementById("photo-dialog-img").removeAttribute("src");
});

// Opening /#wheeler-hall-4th-floor directly goes straight to that bathroom.
syncFromHash();
