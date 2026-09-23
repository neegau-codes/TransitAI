/**
 * TransitMap.js - Dynamic route geometry renderer for TransitAI Expo Demo.
 *
 * Reads route geometry (GeoJSON LineString) from the selected route.
 * Validates every coordinate pair. Computes an SVG projection from the
 * geometry's own bounding box — no hardcoded coordinates, no external libraries.
 *
 * GeoJSON convention: coordinates are [longitude, latitude].
 *
 * If geometry is missing or invalid, shows a graceful placeholder.
 * Route cards and timeline continue to work regardless of map state.
 */

/** Validate a single [lon, lat] pair. */
function isValidCoord(lon, lat) {
  return Number.isFinite(Number(lon)) && Number.isFinite(Number(lat));
}

/** Extract and validate coordinates from a GeoJSON geometry object. */
function extractCoords(geometry) {
  if (!geometry || geometry.type !== 'LineString' || !Array.isArray(geometry.coordinates)) return [];
  return geometry.coordinates.filter(c => Array.isArray(c) && isValidCoord(c[0], c[1]));
}

/**
 * Build a linear projection: maps a geographic bounding box to SVG viewport.
 * Returns a function (lon, lat) → { x, y }.
 * Adds padding around the edge so pins are not clipped.
 */
function buildProjection(coords, svgW = 600, svgH = 480, pad = 48) {
  const lons = coords.map(c => Number(c[0]));
  const lats  = coords.map(c => Number(c[1]));

  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  const minLat  = Math.min(...lats),  maxLat  = Math.max(...lats);

  // Guard against a degenerate case (single point or all same coords)
  const lonSpan = maxLon - minLon || 0.01;
  const latSpan  = maxLat  - minLat  || 0.01;

  const scaleX = (svgW - pad * 2) / lonSpan;
  // Note: SVG Y increases downward; latitude increases upward → flip Y
  const scaleY = (svgH - pad * 2) / latSpan;

  return (lon, lat) => ({
    x: pad + (Number(lon) - minLon) * scaleX,
    y: svgH - pad - (Number(lat) - minLat) * scaleY
  });
}

/** Choose a stroke colour based on mode. */
function modeStroke(mode) {
  const m = (mode || '').toLowerCase();
  if (m === 'metro')                 return '#087F73'; // deep-teal
  if (m === 'train' || m === 'rail') return '#005696'; // accent-rail
  if (m === 'bus')                   return '#D97706'; // amber-600
  return '#66716D';                                    // slate-sec
}

const SVG_W = 600;
const SVG_H = 480;
const PAD   = 48;

export function renderTransitMap(route) {
  const originName = route?.legs?.[0]?.from || 'Origin';
  const destName   = route?.legs?.[route.legs.length - 1]?.to || 'Destination';

  // ── Map content ──────────────────────────────────────────────────────────
  const mapContent = buildMapSVGContent(route, originName, destName);

  return `
    <div class="sticky top-20 flex flex-col gap-3">
      <div class="relative w-full h-[480px] bg-[#F4F6F3] border border-border-subtle rounded-lg overflow-hidden flex flex-col" id="map-canvas-container">

        <!-- Header info bar -->
        <div class="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">
          <div class="bg-surface/95 border border-border-subtle rounded-md px-3 py-1.5 text-xs text-text-primary font-medium pointer-events-auto shadow-sm flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-primary"></span>
            <span>Route Map: ${escHtml(originName)} → ${escHtml(destName)}</span>
          </div>
          <div class="bg-surface/90 border border-border-subtle rounded-md px-2 py-1 text-[10px] text-slate-sec pointer-events-auto">
            STATIC TIMETABLE
          </div>
        </div>

        ${mapContent}
      </div>
    </div>
  `;
}

function buildMapSVGContent(route, originName, destName) {
  const geometry = route?.geometry || null;
  const coords   = extractCoords(geometry);

  // ── No geometry — graceful placeholder ───────────────────────────────────
  if (coords.length < 2) {
    return `
      <div class="w-full h-full flex flex-col items-center justify-center text-center gap-3 p-6">
        <span class="material-symbols-outlined text-4xl text-muted-slate">map</span>
        <div class="text-sm font-semibold text-charcoal">Route geometry unavailable</div>
        <div class="text-xs text-slate-sec max-w-xs">
          The journey timeline and route cards above remain fully functional.
        </div>
      </div>
    `;
  }

  // ── Build projection ──────────────────────────────────────────────────────
  const project = buildProjection(coords, SVG_W, SVG_H, PAD);
  const projected = coords.map(c => project(c[0], c[1]));

  // Route mode for colour
  const routeMode = route?.mode || route?.legs?.[0]?.mode || 'transit';
  const strokeColor = modeStroke(routeMode);

  // Polyline points string
  const polylinePoints = projected.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // Origin & destination projected coords
  const pOrigin = projected[0];
  const pDest   = projected[projected.length - 1];

  // Intermediate stop pins from legs (if they have geometry or we can infer from route legs)
  const intermediatePins = buildIntermediatePins(route, project);

  return `
    <svg class="w-full h-full" viewBox="0 0 ${SVG_W} ${SVG_H}" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern height="32" id="mapGrid" patternUnits="userSpaceOnUse" width="32">
          <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#E5E9E4" stroke-width="0.75"></path>
        </pattern>
      </defs>

      <!-- Background -->
      <rect fill="#F5F7F4" height="100%" width="100%"></rect>
      <rect fill="url(#mapGrid)" height="100%" width="100%"></rect>

      <!-- Corridor label -->
      <text fill="#B0BAB6" font-size="10" font-weight="600" letter-spacing="2"
            x="${(SVG_W / 2 - 80).toFixed(0)}" y="${(SVG_H - 14).toFixed(0)}">KERALA TRANSIT CORRIDOR</text>

      <!-- Route polyline -->
      <polyline
        points="${polylinePoints}"
        stroke="${strokeColor}"
        stroke-width="3.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        fill="none"
        opacity="0.85"
      />

      <!-- Intermediate stop pins -->
      ${intermediatePins}

      <!-- Origin pin -->
      <g transform="translate(${pOrigin.x.toFixed(1)},${pOrigin.y.toFixed(1)})">
        <circle cx="0" cy="0" r="9" fill="#FFFFFF" stroke="#087F73" stroke-width="3"/>
        <circle cx="0" cy="0" r="4" fill="#087F73"/>
        ${labelBox(originName, 12, -13, 'left')}
      </g>

      <!-- Destination pin -->
      <g transform="translate(${pDest.x.toFixed(1)},${pDest.y.toFixed(1)})">
        <circle cx="0" cy="0" r="11" fill="#FFFFFF" stroke="${strokeColor}" stroke-width="3.5"/>
        <circle cx="0" cy="0" r="5" fill="${strokeColor}"/>
        ${labelBox(destName, 14, -13, 'right')}
      </g>
    </svg>
  `;
}

/**
 * Build intermediate stop pins from leg waypoints.
 * Only shown when legs have coordinate data.
 */
function buildIntermediatePins(route, project) {
  if (!route?.legs || route.legs.length < 2) return '';
  const pins = [];

  // Use geometry waypoints from legs if present
  route.legs.forEach((leg, i) => {
    if (i === 0 || i === route.legs.length - 1) return; // skip origin/dest
    const g = leg.geometry;
    if (!g || !Array.isArray(g.coordinates) || g.coordinates.length === 0) return;
    const midIdx = Math.floor(g.coordinates.length / 2);
    const c = g.coordinates[midIdx];
    if (!isValidCoord(c[0], c[1])) return;
    const p = project(c[0], c[1]);
    pins.push(`
      <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="5"
        fill="#FFFFFF" stroke="#66716D" stroke-width="2" opacity="0.8"/>
    `);
  });

  return pins.join('');
}

/** Simple inline SVG label box. direction: 'left' (label right of pin) | 'right' (label left of pin) */
function labelBox(name, xOffset, yOffset, direction) {
  const label = (name || '').toUpperCase().slice(0, 22);
  const w     = Math.min(label.length * 6 + 16, 180);
  const x     = direction === 'right' ? -(xOffset + w) : xOffset;
  return `
    <rect fill="#FFFFFF" height="22" rx="3" stroke="#CBD0CB" stroke-width="1" width="${w}" x="${x}" y="${yOffset}"></rect>
    <text fill="#1A201E" font-family="Inter,sans-serif" font-size="9" font-weight="700" x="${x + 6}" y="${yOffset + 14}">${escSvg(label)}</text>
  `;
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escSvg(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
