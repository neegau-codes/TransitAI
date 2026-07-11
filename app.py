from flask import Flask, render_template, request, jsonify
import datetime
import logging
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
            "latitude": r["latitude"],
            "longitude": r["longitude"]
        } for r in rows]
        return jsonify(locations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

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
        
    recommendations = rec_engine.generate_recommendations(results)
    
    response_data = {
        **results,
        "recommendations": recommendations
    }
    return jsonify(response_data)

@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """Handles natural language travel queries by parsing them first."""
    data = request.json or {}
    query = data.get("query")
    
    if not query or not isinstance(query, str) or not query.strip():
        raise APIError("Query is required.", 400)
        
    # 1. Parse natural language using NLPParser (wraps AIQueryParser)
    parsed_params = nlp_parser.parse_query(query)
    
    source = parsed_params.get("source")
    destination = parsed_params.get("destination")
    dep_time = parsed_params.get("departure_time")
    budget = parsed_params.get("budget_limit")
    deadline = parsed_params.get("arrival_deadline")
    
    # If deadline is equal to dep_time, it means the single time in the query was
    # an arrival deadline. So we want to depart *now* (current time) to meet that deadline.
    search_dep_time = dep_time
    if deadline and dep_time == deadline:
        search_dep_time = datetime.datetime.now().strftime("%H:%M")
    
    # 2. Check if we extracted source and destination successfully
    if not source or not destination:
        # Parser returns structured incomplete-query hints; surface them to the client
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
    routes = route_engine.find_routes(source, destination, search_dep_time, constraints=constraints)
    
    # 5. Generate recommendations if search succeeded
    if "error" not in routes:
        recommendations = rec_engine.generate_recommendations(routes)
    else:
        recommendations = []
        
    return jsonify({
        "parsed_params": parsed_params,
        "routes": routes,
        "recommendations": recommendations
    })

if __name__ == '__main__':
    # Running local server
    app.run(debug=True, host='127.0.0.1', port=5000)
