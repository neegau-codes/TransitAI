from flask import Flask, render_template, request, jsonify
import datetime
import logging
import re
from database.db import get_db_connection
from route_engine import RouteEngine
from nlp_parser import NLPParser
from recommendation_engine import RecommendationEngine

app = Flask(__name__)

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize engine, parser, and recommendation engine
route_engine = RouteEngine()
nlp_parser = NLPParser()
rec_engine = RecommendationEngine()

class APIError(Exception):
    """Standard API Error Exception"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

@app.errorhandler(APIError)
def handle_api_error(error):
    response = {"error": error.message}
    if error.payload:
        response.update(error.payload)
    return jsonify(response), error.status_code

@app.errorhandler(Exception)
def handle_generic_error(error):
    logger.exception("Unexpected error occurred")
    return jsonify({"error": "An internal server error occurred."}), 500

def _get_location_coords_map():
    """Returns dict mapping location_id and lower-cased name to (longitude, latitude)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude FROM locations")
        rows = cursor.fetchall()
        id_map = {}
        name_map = {}
        for r in rows:
            if r["latitude"] is not None and r["longitude"] is not None:
                lon = float(r["longitude"])
                lat = float(r["latitude"])
                id_map[r["id"]] = (lon, lat)
                name_map[r["name"].lower()] = (lon, lat)
        return id_map, name_map
    except Exception:
        return {}, {}
    finally:
        if conn:
            conn.close()

def normalize_route(raw_route, label="Option", route_id="r1", id_map=None, name_map=None):
    """Normalizes raw RouteEngine option into the agreed API response schema."""
    if not raw_route:
        return None

    if id_map is None or name_map is None:
        id_map, name_map = _get_location_coords_map()

    raw_segments = raw_route.get("segments", [])
    total_duration = raw_route.get("total_duration") or raw_route.get("duration") or 0
    total_cost = raw_route.get("total_cost") or raw_route.get("cost") or 0.0
    transfers = raw_route.get("transfers", 0)

    legs = []
    coords = []
    walking_mins = 0.0
    primary_mode = "transit"
    primary_provider = "Multi-Modal"

    for seg in raw_segments:
        if hasattr(seg, "to_dict"):
            seg_dict = seg.to_dict()
        elif isinstance(seg, dict):
            seg_dict = seg
        else:
            seg_dict = getattr(seg, "__dict__", {})

        mode = seg_dict.get("mode", "transit")
        dur = seg_dict.get("duration", 0)
        cost = seg_dict.get("cost", 0.0)
        provider = seg_dict.get("provider", "Transit")
        source_name = seg_dict.get("source_name", "")
        dest_name = seg_dict.get("destination_name", "")
        route_name = seg_dict.get("route_name", "")
        src_id = seg_dict.get("source_id")
        dst_id = seg_dict.get("destination_id")

        if mode == 'walk':
            walking_mins += dur
            status = "ESTIMATED"
            source = "CALCULATED_ESTIMATE"
        else:
            primary_mode = mode
            primary_provider = provider
            status = "SCHEDULED"
            source = "STATIC_SCHEDULE"

        dept = "N/A"
        arr = "N/A"
        m_dept = re.search(r'Dep:\s*(\d{2}:\d{2})', route_name)
        m_arr = re.search(r'Arr:\s*(\d{2}:\d{2})', route_name)
        if m_dept:
            dept = m_dept.group(1)
        if m_arr:
            arr = m_arr.group(1)

        leg = {
            "mode": mode,
            "provider": provider,
            "from": source_name,
            "to": dest_name,
            "departure": dept,
            "arrival": arr,
            "duration_minutes": dur,
            "cost": cost,
            "status": status,
            "source": source,
            # Legacy attributes for frontend compatibility
            "id": seg_dict.get("id"),
            "source_id": src_id,
            "destination_id": dst_id,
            "source_name": source_name,
            "destination_name": dest_name,
            "route_name": route_name,
            "duration": dur
        }
        legs.append(leg)

        # Coordinate extraction [longitude, latitude]
        src_coord = id_map.get(src_id) or name_map.get(source_name.lower())
        dst_coord = id_map.get(dst_id) or name_map.get(dest_name.lower())

        if src_coord:
            point = [src_coord[0], src_coord[1]]
            if not coords or coords[-1] != point:
                coords.append(point)

        if dst_coord:
            point = [dst_coord[0], dst_coord[1]]
            if not coords or coords[-1] != point:
                coords.append(point)

    return {
        "route_id": route_id,
        "label": label,
        "mode": primary_mode,
        "provider": primary_provider,
        "source": "STATIC_SCHEDULE",
        "status": "SCHEDULED",
        "duration_minutes": total_duration,
        "transfers": transfers,
        "walking_minutes": round(walking_mins, 1),
        "fare": {
            "amount": float(total_cost),
            "currency": "INR",
            "status": "SCHEDULED"
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        },
        "legs": legs,
        # Legacy attributes for frontend compatibility
        "segments": legs,
        "total_duration": total_duration,
        "total_cost": float(total_cost),
        "cost": float(total_cost),
        "duration": total_duration,
        "type": label
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/locations', methods=['GET'])
def get_locations():
    """Returns all available locations (stops/stations) in the database."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, latitude, longitude FROM locations ORDER BY name")
        rows = cursor.fetchall()
        
        locations = [{
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],
            "latitude": float(r["latitude"]) if r["latitude"] is not None else 0.0,
            "longitude": float(r["longitude"]) if r["longitude"] is not None else 0.0
        } for r in rows]
        return jsonify(locations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/stations', methods=['GET'])
def get_stations():
    """Returns actual database station records with numeric float coordinates."""
    return get_locations()

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns truthful data availability status."""
    return jsonify({
        "status": "OPERATIONAL",
        "data_policy": "SCHEDULED_AND_ESTIMATED_ONLY",
        "providers": {
            "kochi_metro": {
                "type": "STATIC_SCHEDULE",
                "status": "SCHEDULED"
            },
            "indian_railways": {
                "type": "STATIC_SCHEDULE",
                "status": "SCHEDULED"
            },
            "ksrtc_bus": {
                "type": "STATIC_SCHEDULE",
                "status": "SCHEDULED"
            },
            "walking": {
                "type": "ESTIMATED",
                "status": "ESTIMATED"
            }
        },
        "realtime_telemetry": "UNAVAILABLE"
    })

@app.route('/api/live', methods=['GET'])
def get_live():
    """Explicitly reports realtime telemetry as unavailable."""
    return jsonify({
        "status": "UNAVAILABLE",
        "message": "Realtime telemetry is currently unavailable. Route data relies on static schedules and calculated estimates.",
        "data_policy": "SCHEDULED_AND_ESTIMATED_ONLY"
    })

@app.route('/api/search', methods=['POST'])
def search_routes():
    """
    Handles route searches.
    Supports both V2 natural-language queries (with 'query') and structured searches (with 'source', 'destination').
    """
    data = request.json or {}

    parsed_params = None
    query_str = None

    # Check for natural-language query input
    if "query" in data and isinstance(data["query"], str) and data["query"].strip():
        query_str = data["query"].strip()
        parsed_params = nlp_parser.parse_query(query_str)
        v2_intent = nlp_parser.to_v2_intent(parsed_params=parsed_params)

        source = v2_intent.get("origin")
        destination = v2_intent.get("destination")
        dep_time = v2_intent.get("depart_after") or datetime.datetime.now().strftime("%H:%M")
        budget = v2_intent.get("budget")
        deadline = v2_intent.get("arrive_before")

        search_dep_time = dep_time
        if not search_dep_time or (deadline and dep_time == deadline):
            search_dep_time = datetime.datetime.now().strftime("%H:%M")

        if not source and not destination:
            missing = parsed_params.get("missing", [])
            suggestion = parsed_params.get("suggestion", "Please specify your start and end locations.")
            raise APIError(
                suggestion,
                422,
                {
                    "parsed_params": parsed_params,
                    "missing": missing,
                    "suggestion": suggestion,
                }
            )

        if not source or not destination:
            v2_routes = []
            norm_fastest = None
            norm_cheapest = None
            norm_fewest = None
            raw_routes = []
            results = {}
        else:
            constraints = {
                "budget_limit": budget,
                "arrival_deadline": deadline,
                "excluded_modes": parsed_params.get("additional_constraints", {}).get("excluded_modes", [])
            }

            results = route_engine.find_routes(source, destination, search_dep_time, constraints=constraints)
            if "error" in results:
                v2_routes = []
                norm_fastest = None
                norm_cheapest = None
                norm_fewest = None
                raw_routes = []
            else:
                v2_routes = rec_engine.generate_v2_recommendations(results)
                id_map, name_map = _get_location_coords_map()
                norm_fastest = normalize_route(results.get("fastest"), label="Fastest Route", route_id="r_fastest", id_map=id_map, name_map=name_map)
                norm_cheapest = normalize_route(results.get("cheapest"), label="Cheapest Route", route_id="r_cheapest", id_map=id_map, name_map=name_map)
                norm_fewest = normalize_route(results.get("fewest_transfers"), label="Fewest Transfers", route_id="r_fewest_transfers", id_map=id_map, name_map=name_map)
                raw_routes = results.get("raw_routes", [])

        for vr in v2_routes:
            if "total_duration" not in vr:
                vr["total_duration"] = vr.get("duration_minutes", 0)
            if "total_cost" not in vr:
                vr["total_cost"] = vr.get("fare", {}).get("amount", 0.0)
            if "cost" not in vr:
                vr["cost"] = vr.get("fare", {}).get("amount", 0.0)
            if "duration" not in vr:
                vr["duration"] = vr.get("duration_minutes", 0)
            if "type" not in vr:
                vr["type"] = vr.get("label", "").lower()
            if "segments" not in vr:
                vr["segments"] = vr.get("legs", [])

        intent_obj = v2_intent
        meta_obj = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "data_policy": "SCHEDULED_AND_ESTIMATED_ONLY"
        }

        return jsonify({
            "query": query_str,
            "intent": intent_obj,
            "parsed_params": parsed_params,
            "routes": v2_routes,
            "recommendations": {
                "fastest": norm_fastest,
                "cheapest": norm_cheapest,
                "fewest_transfers": norm_fewest
            },
            "meta": meta_obj,
            "status": "OK",
            # Legacy keys for backward compatibility
            "fastest": norm_fastest,
            "cheapest": norm_cheapest,
            "fewest_transfers": norm_fewest,
            "raw_routes": raw_routes
        })

    # Structured search path
    source = data.get("source")
    destination = data.get("destination")
    dep_time = data.get("departure_time")

    if not source or not isinstance(source, str) or not source.strip():
        raise APIError("Source is required.", 400)
    if not destination or not isinstance(destination, str) or not destination.strip():
        raise APIError("Destination is required.", 400)

    if not dep_time:
        dep_time = datetime.datetime.now().strftime("%H:%M")

    results = route_engine.find_routes(source, destination, dep_time)
    if "error" in results:
        raise APIError(results["error"], 400)

    id_map, name_map = _get_location_coords_map()

    norm_fastest = normalize_route(results.get("fastest"), label="Fastest Route", route_id="r_fastest", id_map=id_map, name_map=name_map)
    norm_cheapest = normalize_route(results.get("cheapest"), label="Cheapest Route", route_id="r_cheapest", id_map=id_map, name_map=name_map)
    norm_fewest = normalize_route(results.get("fewest_transfers"), label="Fewest Transfers", route_id="r_fewest_transfers", id_map=id_map, name_map=name_map)

    v2_routes = rec_engine.generate_v2_recommendations(results)
    for vr in v2_routes:
        if "total_duration" not in vr:
            vr["total_duration"] = vr.get("duration_minutes", 0)
        if "total_cost" not in vr:
            vr["total_cost"] = vr.get("fare", {}).get("amount", 0.0)
        if "cost" not in vr:
            vr["cost"] = vr.get("fare", {}).get("amount", 0.0)
        if "duration" not in vr:
            vr["duration"] = vr.get("duration_minutes", 0)
        if "type" not in vr:
            vr["type"] = vr.get("label", "").lower()
        if "segments" not in vr:
            vr["segments"] = vr.get("legs", [])

    all_routes = v2_routes if v2_routes else [r for r in [norm_fastest, norm_cheapest, norm_fewest] if r is not None]

    recommendations_obj = {
        "BEST": v2_routes[0] if len(v2_routes) > 0 else norm_fastest,
        "FASTEST": norm_fastest,
        "CHEAPEST": norm_cheapest,
        "LEAST WALKING": v2_routes[3] if len(v2_routes) > 3 else (v2_routes[0] if len(v2_routes) > 0 else norm_fastest),
        "fastest": norm_fastest,
        "cheapest": norm_cheapest,
        "fewest_transfers": norm_fewest
    }

    intent_obj = {
        "origin": source,
        "destination": destination,
        "departure_time": dep_time,
        "arrival_deadline": None,
        "mode_preferences": ["train", "metro", "bus", "walk"]
    }

    meta_obj = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "data_policy": "SCHEDULED_AND_ESTIMATED_ONLY"
    }

    response_data = {
        "query": f"{source} to {destination}",
        "intent": intent_obj,
        "routes": all_routes,
        "recommendations": recommendations_obj,
        "meta": meta_obj,
        "status": "OK",
        # Legacy keys for backward compatibility
        "fastest": norm_fastest,
        "cheapest": norm_cheapest,
        "fewest_transfers": norm_fewest,
        "raw_routes": results.get("raw_routes", [])
    }
    return jsonify(response_data)


@app.route('/api/routes', methods=['GET'])
def get_routes_v2():
    """V2 GET /api/routes endpoint."""
    from_loc = request.args.get("from")
    to_loc = request.args.get("to")
    travel_date = request.args.get("date", datetime.date.today().isoformat())

    if not from_loc or not to_loc:
        raise APIError("'from' and 'to' parameters are required.", 400)

    dep_time = datetime.datetime.now().strftime("%H:%M")
    routes_res = route_engine.find_routes(from_loc, to_loc, dep_time)

    if "error" in routes_res:
        v2_routes = []
    else:
        v2_routes = rec_engine.generate_v2_recommendations(routes_res)

    return jsonify({
        "request": {
            "origin": from_loc,
            "destination": to_loc,
            "date": travel_date
        },
        "routes": v2_routes,
        "generated_at": datetime.datetime.now().isoformat()
    })

@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """Legacy compatibility endpoint delegating to search_routes."""
    return search_routes()

if __name__ == '__main__':
    # Running local server
    app.run(debug=True, host='127.0.0.1', port=5000)
