/**
 * api.js - Centralized API Service & Data Normalization Layer for TransitAI
 */

import { USE_MOCK_API, MOCK_LOCATIONS, MOCK_SEARCH_RESPONSE } from './mockData.js';

// Base URL configured via environment variable fallback or location origin
const API_BASE_URL = (window.VITE_API_BASE_URL || window.API_BASE_URL || "").replace(/\/$/, "");

/**
 * Normalizes raw route segments and route options from backend response into internal contract schema.
 */
function normalizeLeg(segment) {
  if (!segment) return null;
  
  let mode = (segment.mode || segment.transport_mode || "transit").toLowerCase();
  if (mode === "walk" || mode === "walking") mode = "walk";
  else if (mode === "train" || mode === "rail" || mode === "railway") mode = "train";
  else if (mode === "metro" || mode === "subway") mode = "metro";
  else if (mode === "bus") mode = "bus";

  const departure = segment.departure || (segment.schedule && segment.schedule[0]) || null;
  const arrival = segment.arrival || null;
  
  // Clean status mapping: LIVE | SCHEDULED | ESTIMATED | UNAVAILABLE
  let rawStatus = (segment.status || "SCHEDULED").toUpperCase();
  let status = "SCHEDULED";
  if (rawStatus === "LIVE") status = "LIVE";
  else if (rawStatus === "ESTIMATED") status = "ESTIMATED";
  else if (rawStatus === "UNAVAILABLE") status = "UNAVAILABLE";
  else status = "SCHEDULED";

  return {
    mode: mode,
    provider: segment.provider || (mode === "metro" ? "Kochi Metro" : mode === "train" ? "Indian Railways" : "KSRTC"),
    from: segment.source_name || segment.from || "Origin",
    to: segment.destination_name || segment.to || "Destination",
    departure: departure,
    arrival: arrival,
    duration_minutes: segment.duration || segment.duration_minutes || 0,
    fare: {
      amount: typeof segment.cost === 'number' ? segment.cost : (segment.fare?.amount || 0),
      currency: "INR",
      status: status
    },
    status: status,
    source: segment.source || (mode === "metro" ? "KMRL Live" : mode === "train" ? "IRCTC Schedule" : "KSRTC Schedule")
  };
}

function normalizeRoute(rawRoute, defaultLabel = "Recommended") {
  if (!rawRoute) return null;

  // Raw route can be a dict from backend like { type, total_duration, total_cost, transfers, segments }
  // or a recommendation object { category, explanation, route: { segments... } }
  const routeObj = rawRoute.route || rawRoute;
  const label = rawRoute.category || rawRoute.type || defaultLabel;
  const segments = routeObj.segments || routeObj.legs || [];
  const normalizedLegs = segments.map(normalizeLeg).filter(Boolean);

  const duration_minutes = routeObj.total_duration || routeObj.duration_minutes || 
    normalizedLegs.reduce((sum, leg) => sum + (leg.duration_minutes || 0), 0);

  const totalCost = typeof routeObj.total_cost === 'number' ? routeObj.total_cost : 
    (routeObj.fare?.amount || normalizedLegs.reduce((sum, leg) => sum + (leg.fare?.amount || 0), 0));

  const transfers = typeof routeObj.transfers === 'number' ? routeObj.transfers : 
    Math.max(0, normalizedLegs.filter(l => l.mode !== 'walk').length - 1);

  const walking_minutes = normalizedLegs
    .filter(l => l.mode === 'walk')
    .reduce((sum, leg) => sum + (leg.duration_minutes || 0), 0);

  // Overall status evaluation from legs
  let status = "SCHEDULED";
  if (normalizedLegs.some(l => l.status === "LIVE")) status = "LIVE";
  else if (normalizedLegs.some(l => l.status === "UNAVAILABLE")) status = "UNAVAILABLE";
  else if (normalizedLegs.some(l => l.status === "ESTIMATED")) status = "ESTIMATED";

  return {
    route_id: routeObj.id || routeObj.route_id || `rt_${Math.random().toString(36).substr(2, 9)}`,
    label: label,
    category: label,
    duration_minutes: duration_minutes,
    fare: {
      amount: totalCost,
      currency: "INR",
      status: status
    },
    transfers: transfers,
    walking_minutes: walking_minutes,
    status: status,
    legs: normalizedLegs,
    explanation: rawRoute.explanation || null
  };
}

export function normalizeSearchResponse(data) {
  if (!data) return { intent: null, routes: [], status: "OK" };

  let routes = [];

  // 1. Direct routes array in standard contract
  if (Array.isArray(data.routes)) {
    routes = data.routes.map(r => normalizeRoute(r));
  }
  // 2. Recommendations format from recommendation_engine / ai-search
  else if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
    routes = data.recommendations.map(r => normalizeRoute(r));
  }
  // 3. Structured object format { fastest, cheapest, fewest_transfers, balanced }
  else {
    const keys = ["fastest", "cheapest", "fewest_transfers", "balanced"];
    keys.forEach(k => {
      if (data[k]) {
        const norm = normalizeRoute(data[k], k.replace('_', ' ').toUpperCase());
        if (norm) routes.push(norm);
      }
    });
  }

  // Deduplicate or sanitize routes
  const intent = data.intent || data.parsed_params || null;
  const status = data.status || (data.error ? "ERROR" : "OK");

  return {
    intent: intent ? {
      origin: intent.source || intent.origin || null,
      destination: intent.destination || null,
      date: intent.travel_date || intent.date || null,
      arrive_before: intent.arrival_deadline || intent.arrive_before || null,
      depart_after: intent.departure_time || intent.depart_after || null,
      budget: intent.budget_limit || intent.budget || null,
      preferred_modes: intent.preferred_modes || []
    } : null,
    routes: routes,
    status: status,
    raw: data
  };
}

/**
 * Generic fetch wrapper with timeout & JSON error handling
 */
async function requestAPI(endpoint, options = {}) {
  if (USE_MOCK_API) {
    await new Promise(resolve => setTimeout(resolve, 300));
    return null; // Signals caller to use mock
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 12000);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        ...(options.headers || {})
      },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const message = errData.error || errData.message || `API error (${response.status})`;
      const err = new Error(message);
      err.status = response.status;
      err.payload = errData;
      throw err;
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

export const api = {
  /**
   * Natural Language / AI Search (POST /api/search)
   */
  async search(query) {
    if (USE_MOCK_API) {
      return normalizeSearchResponse(MOCK_SEARCH_RESPONSE);
    }

    try {
      // Send query object to POST /api/search or fallback to /api/ai-search
      const data = await requestAPI('/api/search', {
        method: 'POST',
        body: JSON.stringify({ query: query })
      });
      return normalizeSearchResponse(data);
    } catch (err) {
      // Fallback try /api/ai-search if endpoint is split
      try {
        const data = await requestAPI('/api/ai-search', {
          method: 'POST',
          body: JSON.stringify({ query: query })
        });
        return normalizeSearchResponse(data);
      } catch (innerErr) {
        throw innerErr;
      }
    }
  },

  /**
   * Structured Route Search (GET or POST /api/routes / /api/search)
   */
  async getRoutes(from, to, date, departureTime, optimization = "FASTEST") {
    if (USE_MOCK_API) {
      return normalizeSearchResponse(MOCK_SEARCH_RESPONSE);
    }

    // Call structured POST /api/search
    const data = await requestAPI('/api/search', {
      method: 'POST',
      body: JSON.stringify({
        source: from,
        destination: to,
        departure_time: departureTime || "10:00",
        date: date,
        optimization: optimization
      })
    });
    return normalizeSearchResponse(data);
  },

  /**
   * Get all stations / locations for autocomplete (GET /api/locations)
   */
  async getLocations() {
    if (USE_MOCK_API) {
      return MOCK_LOCATIONS;
    }
    try {
      const locations = await requestAPI('/api/locations');
      return Array.isArray(locations) ? locations : [];
    } catch (err) {
      console.warn("Failed to fetch locations, returning empty array", err);
      return [];
    }
  },

  /**
   * Get live route telemetry (GET /api/live/{routeId})
   */
  async getLive(routeId) {
    if (USE_MOCK_API) {
      return { routeId, status: "LIVE", delay_minutes: 0, updated_at: new Date().toISOString() };
    }
    try {
      return await requestAPI(`/api/live/${encodeURIComponent(routeId)}`);
    } catch (err) {
      return { routeId, status: "SCHEDULED", error: err.message };
    }
  }
};
