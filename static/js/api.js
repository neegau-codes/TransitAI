/**
 * api.js - Centralized API Service & Data Normalization Layer for TransitAI
 * Expo Demo build — uses POST /api/search (natural-language) and GET /api/stations.
 * /api/live is NOT used in this build.
 */

import { USE_MOCK_API, MOCK_LOCATIONS, MOCK_SEARCH_RESPONSE } from './mockData.js';

// Base URL — falls back to same-origin when Flask serves the frontend directly
const API_BASE_URL = (window.VITE_API_BASE_URL || window.API_BASE_URL || '').replace(/\/$/, '');

/**
 * Normalize any status value to one of the four canonical values.
 * LIVE is kept for backend compatibility but must NOT be rendered as a
 * realtime indicator in the Expo UI.
 */
export const normalizeStatus = value => {
  const s = String(value || 'UNAVAILABLE').toUpperCase();
  return ['SCHEDULED', 'ESTIMATED', 'UNAVAILABLE', 'LIVE'].includes(s) ? s : 'UNAVAILABLE';
};

/** Normalize a single leg / segment object from the backend. */
function normalizeLeg(segment) {
  if (!segment) return null;

  let mode = (segment.mode || segment.transport_mode || 'transit').toLowerCase();
  if (mode === 'walk' || mode === 'walking') mode = 'walk';
  else if (mode === 'train' || mode === 'rail' || mode === 'railway') mode = 'train';
  else if (mode === 'metro' || mode === 'subway') mode = 'metro';
  else if (mode === 'bus') mode = 'bus';

  const departure = segment.departure || (segment.schedule && segment.schedule[0]) || null;
  const arrival   = segment.arrival || null;
  const status    = normalizeStatus(segment.status);

  // Preserve explicit nulls for missing optional data — do NOT default to 0
  const fareAmount = typeof segment.cost === 'number'
    ? segment.cost
    : (typeof segment.fare?.amount === 'number' ? segment.fare.amount : null);

  return {
    mode,
    provider:         segment.provider || null,
    from:             segment.source_name || segment.from || null,
    to:               segment.destination_name || segment.to || null,
    departure,
    arrival,
    duration_minutes: segment.duration ?? segment.duration_minutes ?? null,
    fare: {
      amount:   fareAmount,
      currency: segment.fare?.currency || 'INR',
      status:   normalizeStatus(segment.fare?.status)
    },
    status,
    source:   segment.source || null,
    geometry: segment.geometry || null
  };
}

/** Normalize a single route object from the backend. */
function normalizeRoute(rawRoute, defaultLabel = 'Route') {
  if (!rawRoute) return null;

  // Route can be a direct object OR wrapped in { route: {...}, category, explanation }
  const routeObj = rawRoute.route || rawRoute;
  const label    = rawRoute.category || rawRoute.label || rawRoute.type || defaultLabel;
  const segments = routeObj.segments || routeObj.legs || [];
  const normalizedLegs = segments.map(normalizeLeg).filter(Boolean);

  // Preserve explicit backend values; do NOT compute fallbacks to 0
  const duration_minutes = routeObj.duration_minutes ?? routeObj.total_duration ?? null;

  const costVal = typeof routeObj.cost === 'number'   ? routeObj.cost
                : typeof routeObj.total_cost === 'number' ? routeObj.total_cost
                : (routeObj.fare?.amount ?? null);

  const transfers      = routeObj.transfers      ?? null;
  const walking_minutes = routeObj.walking_minutes ?? null;

  // Determine overall status — use top-level first, then derive from legs
  let rawStatus = routeObj.status;
  if (!rawStatus && normalizedLegs.length > 0) {
    if      (normalizedLegs.some(l => l.status === 'LIVE'))        rawStatus = 'LIVE';
    else if (normalizedLegs.some(l => l.status === 'UNAVAILABLE')) rawStatus = 'UNAVAILABLE';
    else if (normalizedLegs.some(l => l.status === 'ESTIMATED'))   rawStatus = 'ESTIMATED';
    else                                                            rawStatus = 'SCHEDULED';
  }
  const status = normalizeStatus(rawStatus);

  return {
    route_id:         routeObj.id || routeObj.route_id || null,
    trip_id:          routeObj.trip_id || null,   // Preserved — not displayed unless needed
    label,
    category:         label,
    duration_minutes,
    mode:             routeObj.mode || (normalizedLegs[0] ? normalizedLegs[0].mode : null),
    provider:         routeObj.provider || null,
    source:           routeObj.source || null,
    geometry:         routeObj.geometry || null,
    fare: {
      amount:   costVal,
      currency: routeObj.fare?.currency || 'INR',
      status:   normalizeStatus(routeObj.fare?.status || status)
    },
    transfers,
    walking_minutes,
    status,
    legs:             normalizedLegs,
    explanation:      rawRoute.explanation || null
  };
}

/**
 * Normalize the raw /api/search response into the canonical frontend structure.
 * Handles three shapes:
 *   1. { routes: [...], intent, recommendations }   ← V2 contract (primary)
 *   2. { recommendations: [...] }                    ← recommendation list
 *   3. { fastest, cheapest, fewest_transfers, ... }  ← legacy object keys
 */
export function normalizeSearchResponse(data) {
  if (!data) return { intent: null, routes: [], recommendations: null, status: 'OK' };

  let routes = [];
  let recommendations = null;

  // 1. Primary V2 shape (Array or Dict)
  if (Array.isArray(data.routes) && data.routes.length > 0) {
    routes = data.routes.map(r => normalizeRoute(r)).filter(Boolean);
  }
  else if (data.routes && typeof data.routes === 'object' && !Array.isArray(data.routes)) {
    const keys = ['best', 'fastest', 'cheapest', 'fewest_transfers', 'least_walking', 'balanced'];
    keys.forEach(k => {
      if (data.routes[k]) {
        const norm = normalizeRoute(data.routes[k], k.replace(/_/g, ' ').toUpperCase());
        if (norm) routes.push(norm);
      }
    });
    // Also include any other route objects in data.routes not in keys except raw_routes
    Object.keys(data.routes).forEach(k => {
      if (!keys.includes(k) && k !== 'raw_routes' && data.routes[k]) {
        const norm = normalizeRoute(data.routes[k], k.replace(/_/g, ' ').toUpperCase());
        if (norm) routes.push(norm);
      }
    });
  }
  // 2. Recommendation list
  else if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
    routes = data.recommendations.map(r => normalizeRoute(r)).filter(Boolean);
  }
  // 3. Legacy named keys at root
  else {
    const keys = ['fastest', 'cheapest', 'fewest_transfers', 'balanced', 'best', 'least_walking'];
    keys.forEach(k => {
      if (data[k]) {
        const norm = normalizeRoute(data[k], k.replace(/_/g, ' ').toUpperCase());
        if (norm) routes.push(norm);
      }
    });
  }

  // Consume recommendations object if provided separately
  if (data.recommendations && typeof data.recommendations === 'object' && !Array.isArray(data.recommendations)) {
    recommendations = {};
    ['BEST', 'FASTEST', 'CHEAPEST', 'LEAST WALKING'].forEach(key => {
      const rawKey = key.toLowerCase().replace(' ', '_');
      if (data.recommendations[rawKey] || data.recommendations[key]) {
        recommendations[key] = normalizeRoute(data.recommendations[rawKey] || data.recommendations[key], key);
      }
    });
    if (Object.keys(recommendations).length === 0) recommendations = null;
  }

  const intent = data.intent || data.parsed_params || null;

  return {
    intent: intent ? {
      origin:          intent.source || intent.origin || null,
      destination:     intent.destination || null,
      date:            intent.travel_date || intent.date || null,
      arrive_before:   intent.arrival_deadline || intent.arrive_before || null,
      depart_after:    intent.departure_time || intent.depart_after || null,
      budget:          intent.budget_limit || intent.budget || null,
      preferred_modes: intent.preferred_modes || []
    } : null,
    routes,
    recommendations,
    status: data.status || (data.error ? 'ERROR' : 'OK'),
    raw: data
  };
}

/** Generic fetch with 12 s timeout and structured error handling. */
async function requestAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId  = setTimeout(() => controller.abort(), 12000);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(options.headers || {})
      },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const err     = new Error(errData.error || errData.message || `API error (${response.status})`);
      err.code      = errData.code || String(response.status);
      err.httpStatus = response.status;
      throw err;
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (!error.code) error.code = 'NETWORK_ERROR';
    throw error;
  }
}

export const api = {
  /**
   * Natural-language search — POST /api/search { "query": "..." }
   * This is the primary Expo Demo search path.
   * Do NOT convert to station IDs; the NLP is entirely backend-owned.
   */
  async search(query) {
    if (USE_MOCK_API) return normalizeSearchResponse(MOCK_SEARCH_RESPONSE);
    const data = await requestAPI('/api/search', {
      method: 'POST',
      body:   JSON.stringify({ query })
    });
    return normalizeSearchResponse(data);
  },

  /**
   * Station / location list for autocomplete — GET /api/stations
   * Normalizes coordinates to numeric values. Validates with isFinite.
   */
  async getLocations() {
    if (USE_MOCK_API) return MOCK_LOCATIONS;
    try {
      const payload = await requestAPI('/api/stations');
      const items   = Array.isArray(payload) ? payload : (payload?.data || []);
      return items.map(s => ({
        ...s,
        latitude:  Number(s.latitude),
        longitude: Number(s.longitude)
      })).filter(s => Number.isFinite(s.latitude) && Number.isFinite(s.longitude));
    } catch (err) {
      console.warn('Failed to fetch /api/stations — returning empty list', err);
      return [];
    }
  },

  /**
   * Provider health status — GET /api/status
   * If the response is empty or unavailable, the UI falls back to the static banner.
   */
  async getStatus() {
    if (USE_MOCK_API) return { data: {} };
    try {
      return await requestAPI('/api/status');
    } catch (_) {
      return { data: {} };
    }
  },

  /**
   * getLive() — NOT used in Expo Demo.
   * Retained stub to avoid import errors in any file that references it.
   * Real-time integration is future scope.
   */
  async getLive(_routeId) {
    console.info('getLive() is disabled for Expo. Real-time is future scope.');
    return { status: 'UNAVAILABLE' };
  }
};
