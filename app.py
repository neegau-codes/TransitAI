from flask import Flask, render_template, request, jsonify
import datetime
from database.db import get_db_connection
from route_engine import RouteEngine
from nlp_parser import NLPParser

app = Flask(__name__)

# Initialize engine and parser
route_engine = RouteEngine()
nlp_parser = NLPParser()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/locations', methods=['GET'])
def get_locations():
    """Returns all available locations (stops/stations) in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM locations ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        
        locations = [{"id": r["id"], "name": r["name"], "type": r["type"]} for r in rows]
        return jsonify(locations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_routes():
    """Handles structured route searches."""
    data = request.json or {}
    source = data.get("source")
    destination = data.get("destination")
    departure_time = data.get("departure_time")
    
    if not source or not destination:
        return jsonify({"error": "Source and destination are required."}), 400
        
    if not departure_time:
        departure_time = datetime.datetime.now().strftime("%H:%M")
        
    try:
        results = route_engine.find_routes(source, destination, departure_time)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """Handles natural language travel queries by parsing them first."""
    data = request.json or {}
    query = data.get("query")
    
    if not query:
        return jsonify({"error": "Query is required."}), 400
        
    try:
        # 1. Parse natural language using NLPParser
        parsed_params = nlp_parser.parse_query(query)
        
        source = parsed_params.get("source")
        destination = parsed_params.get("destination")
        dep_time = parsed_params.get("departure_time")
        budget = parsed_params.get("budget")
        preference = parsed_params.get("preference")
        
        # 2. Check if we extracted source and destination successfully
        if not source or not destination:
            return jsonify({
                "parsed_params": parsed_params,
                "error": "Could not identify both start and end locations from your query. Please be more specific (e.g., 'from Aluva to Kaloor')."
            }), 200 # Return 200 with error details so frontend can show helpful correction advice
            
        # 3. Perform route search
        routes = route_engine.find_routes(source, destination, dep_time)
        
        # 4. Filter routes by budget if budget constraint is present
        # If the cheapest route exceeds budget, we mark the routes, or warn the user.
        # We return the routes along with parsing details.
        return jsonify({
            "parsed_params": parsed_params,
            "routes": routes
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Running local server
    app.run(debug=True, host='127.0.0.1', port=5000)
