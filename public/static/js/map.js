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
import maplibregl from "https://unpkg.com/maplibre-gl@6.14.0/dist/maplibre-gl.mjs";

// Roughly the middle of campus. Note the order: MapLibre takes coordinates as
// [longitude, latitude] -- the opposite of Leaflet and of most of what you
// read elsewhere. Getting it backwards puts your map in Antarctica.
const CAMPUS_CENTER = [-122.2585, 37.8719];
const INITIAL_ZOOM = 15.5;

// The basemap. OpenFreeMap serves OpenStreetMap-derived vector tiles for free
// with no API key or account. https://openfreemap.org/
const MAP_STYLE = "https://tiles.openfreemap.org/styles/dark";

// OpenFreeMap requires this credit, and its style JSON does not carry an
// attribution string, so MapLibre cannot add one on its own -- we must.
const ATTRIBUTION =
  '<a href="https://openfreemap.org/" target="_blank" rel="noopener">OpenFreeMap</a> ' +
  '&copy; <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">OpenMapTiles</a> ' +
  'Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';

// Pin color. Phase 5 replaces this with a per-building tier color.
const PIN_COLOR = "#fdb515"; // California Gold

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

// compact: true shows an (i) button on narrow screens instead of a long line
// of text, which keeps the credit visible without covering the map.
map.addControl(
  new maplibregl.AttributionControl({ compact: true, customAttribution: ATTRIBUTION }),
);

// --- 3. One pin per building ----------------------------------------------
//
// Phase 3 replaces this basic popup with the real one (access state, bathroom
// count, hero photos) and Phase 5 colors each pin by its building's tier.
for (const building of buildings) {
  // Build the popup as a DOM element and set .textContent rather than pasting
  // a string of HTML. textContent treats the name as plain text, so a stray
  // "<" in a building name can never be interpreted as markup.
  const label = document.createElement("strong");
  label.textContent = building.name;

  const popup = new maplibregl.Popup({ offset: 24 }).setDOMContent(label);

  new maplibregl.Marker({ color: PIN_COLOR })
    .setLngLat([building.lng, building.lat]) // again: lng first
    .setPopup(popup)
    .addTo(map);
}
