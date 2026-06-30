// ─────────────────────────────────────────────────────────────────
// SATVision — Application Constants
// ─────────────────────────────────────────────────────────────────

/** Default Leaflet zoom level when flying to a searched location. */
export const DEFAULT_ZOOM = 13.5;

/**
 * Root URL for the backend inference server.
 * Update this to your current HuggingFace Space or deployment endpoint.
 */
export const BACKEND_URL = 'https://satvision-app.hf.space';

// ─────────────────────────────────────────────────────────────────
// Featured Flood Events — Pre-loaded 10m Zoom Anchors
// ─────────────────────────────────────────────────────────────────

/**
 * @typedef {Object} FeaturedEvent
 * @property {string} label   - Human-readable display label for the dropdown.
 * @property {string} value   - Unique key used to identify the event.
 * @property {number} [lat]   - Latitude of the event center.
 * @property {number} [lon]   - Longitude of the event center.
 * @property {string} [date]  - ISO date string (YYYY-MM-DD) of the event.
 * @property {number} [zoom]  - Preferred Leaflet zoom level for the event.
 */

/** @type {FeaturedEvent[]} */
export const FEATURED_EVENTS = [
  {
    label: 'Custom Date / Live Search',
    value: 'custom',
  },
  {
    label: 'Lake Manchar / Dadu - Sep 2022',
    value: 'manchar',
    lat: 26.435,
    lon: 67.680,
    date: '2022-09-10',
    zoom: 12.5,
  },
  {
    label: 'Nowshera (Kabul River) - Sep 2022',
    value: 'nowshera',
    lat: 34.012,
    lon: 71.985,
    date: '2022-09-02',
    zoom: 13.5,
  },
  {
    label: 'Kasur Floods - Aug 2023',
    value: 'kasur',
    lat: 31.025,
    lon: 74.620,
    date: '2023-08-28',
    zoom: 13.5,
  },
];
