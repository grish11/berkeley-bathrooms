/* Berkeley Bathrooms — the map.
 *
 * This is all of the JavaScript in the project. Its whole job is:
 *   1. read the building data that Flask embedded in the page
 *   2. create a Leaflet map centred on campus
 *   3. drop one pin per building
 *
 * Everything else -- scores, tiers, access states -- is computed in Python.
 * Keeping it that way means there is only one place where the rules live.
 *
 * Docs: https://leafletjs.com/reference.html
 */

// Wrapping everything in a function keeps these names out of the global
// scope, so they cannot collide with Leaflet's or a future script's.
(function () {
  "use strict";

  // Roughly the middle of campus. Zoom 16 fits the central blocks on screen;
  // higher numbers zoom in closer.
  var CAMPUS_CENTER = [37.8719, -122.2585];
  var INITIAL_ZOOM = 16;

  // --- 1. Read the data Flask put in the page -----------------------------
  //
  // index.html rendered a <script type="application/json"> block containing
  // the buildings list. Because its type is not JavaScript, the browser left
  // it alone as text; JSON.parse turns that text into real JS objects.
  var dataElement = document.getElementById("buildings-data");
  var buildings = JSON.parse(dataElement.textContent);

  // --- 2. Create the map --------------------------------------------------
  //
  // L is the global that leaflet.js defines. L.map() attaches a map to the
  // element with id="map"; setView() points it at a location and zoom level.
  // https://leafletjs.com/reference.html#map
  var map = L.map("map").setView(CAMPUS_CENTER, INITIAL_ZOOM);

  // A tile layer is the actual map imagery: a grid of small images that
  // Leaflet requests as you pan and zoom. {z}/{x}/{y} are placeholders
  // Leaflet fills in for zoom, column and row.
  //
  // The attribution is not optional -- OpenStreetMap's tile usage policy
  // requires visible credit, and asks that it not be hidden behind a toggle.
  // https://operations.osmfoundation.org/policies/tiles/
  // https://leafletjs.com/reference.html#tilelayer
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  // --- 3. One pin per building --------------------------------------------
  //
  // Phase 3 replaces this basic popup with the real one (access state,
  // bathroom count, hero photos) and Phase 5 colors the pins by tier.
  buildings.forEach(function (building) {
    var marker = L.marker([building.lat, building.lng]).addTo(map);

    // Build the popup as a DOM element and set .textContent rather than
    // pasting a string of HTML. textContent treats the name as plain text, so
    // a stray "<" in a building name can never be interpreted as markup.
    var label = document.createElement("strong");
    label.textContent = building.name;

    marker.bindPopup(label);
  });
})();
