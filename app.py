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
    """Handles structured route searches."""
    data = request.json or {}
    source = data.get("source")
    destination = data.get("destination")
    departure_time = data.get("departure_time")
    
    if not source or not isinstance(source, str) or not source.strip():
        raise APIError("Source is required.", 400)
    if not destination or not isinstance(destination, str) or not destination.strip():
        raise APIError("Destination is required.", 400)
        
    if not departure_time:
        departure_time = datetime.datetime.now().strftime("%H:%M")
        
    results = route_engine.find_routes(source, destination, departure_time)
    if "error" in results:
        raise APIError(results["error"], 400)

    id_map, name_map = _get_location_coords_map()

    norm_fastest = normalize_route(results.get("fastest"), label="Fastest Route", route_id="r_fastest", id_map=id_map, name_map=name_map)
    norm_cheapest = normalize_route(results.get("cheapest"), label="Cheapest Route", route_id="r_cheapest", id_map=id_map, name_map=name_map)
    norm_fewest = normalize_route(results.get("fewest_transfers"), label="Fewest Transfers", route_id="r_fewest_transfers", id_map=id_map, name_map=name_map)

    all_routes = [r for r in [norm_fastest, norm_cheapest, norm_fewest] if r is not None]

    recommendations_obj = {
        "fastest": norm_fastest,
        "cheapest": norm_cheapest,
        "fewest_transfers": norm_fewest
    }

    intent_obj = {
        "origin": source,
        "destination": destination,
        "departure_time": departure_time,
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
        # Legacy keys for backward compatibility
        "fastest": norm_fastest,
        "cheapest": norm_cheapest,
        "fewest_transfers": norm_fewest,
        "raw_routes": results.get("raw_routes", [])
    }
    return jsonify(response_data)

@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """Handles natural language travel queries by parsing them first."""
    data = request.json or {}
    query = data.get("query")
    
    if not query or not isinstance(query, str) or not query.strip():
        raise APIError("Query is required.", 400)
        
    # 1. Parse natural language using NLPParser
    parsed_params = nlp_parser.parse_query(query)
    
    source = parsed_params.get("source")
    destination = parsed_params.get("destination")
    dep_time = parsed_params.get("departure_time")
    budget = parsed_params.get("budget_limit")
    deadline = parsed_params.get("arrival_deadline")
    
    search_dep_time = dep_time
    if not search_dep_time or (deadline and dep_time == deadline):
        search_dep_time = datetime.datetime.now().strftime("%H:%M")
    
    # 2. Check if we extracted source and destination successfully
    if not source or not destination:
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
            
    # 3. Build constraints dictionary
    constraints = {
        "budget_limit": budget,
        "arrival_deadline": deadline,
        "excluded_modes": parsed_params.get("additional_constraints", {}).get("excluded_modes", [])
    }
    
    # 4. Perform route search using constraints
    results = route_engine.find_routes(source, destination, search_dep_time, constraints=constraints)
    if "error" in results:
        raise APIError(results["error"], 400)

    id_map, name_map = _get_location_coords_map()

    norm_fastest = normalize_route(results.get("fastest"), label="Fastest Route", route_id="r_fastest", id_map=id_map, name_map=name_map)
    norm_cheapest = normalize_route(results.get("cheapest"), label="Cheapest Route", route_id="r_cheapest", id_map=id_map, name_map=name_map)
    norm_fewest = normalize_route(results.get("fewest_transfers"), label="Fewest Transfers", route_id="r_fewest_transfers", id_map=id_map, name_map=name_map)

    all_routes = [r for r in [norm_fastest, norm_cheapest, norm_fewest] if r is not None]

    recommendations_obj = {
        "fastest": norm_fastest,
        "cheapest": norm_cheapest,
        "fewest_transfers": norm_fewest
    }

    intent_obj = {
        "origin": source,
        "destination": destination,
        "departure_time": dep_time,
        "arrival_deadline": deadline,
        "mode_preferences": ["train", "metro", "bus", "walk"]
    }

    meta_obj = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "data_policy": "SCHEDULED_AND_ESTIMATED_ONLY"
    }
        
    return jsonify({
        "query": query,
        "intent": intent_obj,
        "parsed_params": parsed_params,
        "routes": all_routes,
        "recommendations": recommendations_obj,
        "meta": meta_obj,
        # Legacy keys for backward compatibility
        "fastest": norm_fastest,
        "cheapest": norm_cheapest,
        "fewest_transfers": norm_fewest,
        "raw_routes": results.get("raw_routes", [])
    })

if __name__ == '__main__':
    # Running local server
    app.run(debug=True, host='127.0.0.1', port=5000)

