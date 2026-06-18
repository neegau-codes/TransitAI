import os
import sys
import sqlite3
import json
import math

# Add the workspace directory to the path so we can import ingestion modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import DATABASE_PATH
from ingestion.metro_importer import MetroImporter
from ingestion.railway_importer import RailwayImporter
from ingestion.bus_importer import BusImporter
from ingestion.validation import DataValidator

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculates the Haversine distance in km between two coordinate pairs."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999.0
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def rebuild_db():
    print("=" * 60)
    print("               TransitAI Database Rebuild Utility")
    print("=" * 60)

    # 1. Delete existing database file
    if os.path.exists(DATABASE_PATH):
        try:
            os.remove(DATABASE_PATH)
            print(f"Removed existing database at {DATABASE_PATH}")
        except Exception as e:
            print(f"Error removing existing database: {e}")
            sys.exit(1)

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    # 2. Connect and execute schema
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "schema.sql")
    if not os.path.exists(schema_path):
        print(f"Error: schema.sql not found at {schema_path}")
        sys.exit(1)

    print("Initializing database schema...")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    print("Database schema created.")

    # 3. Load and insert locations
    locations_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ingestion", "data", "locations.json")
    if not os.path.exists(locations_path):
        print(f"Error: locations.json not found at {locations_path}")
        sys.exit(1)

    print("Seeding locations...")
    with open(locations_path, "r") as f:
        locations_data = json.load(f)

    for loc in locations_data:
        cursor.execute(
            """
            INSERT INTO locations (name, city, state, latitude, longitude, type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (loc["name"], loc["city"], loc["state"], loc["latitude"], loc["longitude"], loc["type"])
        )
    conn.commit()
    print(f"Successfully seeded {len(locations_data)} locations.")

    # Retrieve inserted locations to calculate walk connections
    cursor.execute("SELECT id, name, city, latitude, longitude FROM locations")
    db_locations = [dict(row) for row in cursor.execute("SELECT id, name, city, latitude, longitude FROM locations").fetchall()]

    # 4. Generate Walking Transfers (distance-based within the same city)
    print("Generating walking transfers...")
    walk_provider_id = cursor.execute("SELECT id FROM providers WHERE provider_name = 'Walk'").fetchone()
    if not walk_provider_id:
        cursor.execute("INSERT INTO providers (provider_name, transport_type) VALUES ('Walk', 'walk')")
        conn.commit()

    walk_count = 0
    for i in range(len(db_locations)):
        for j in range(i + 1, len(db_locations)):
            loc1 = db_locations[i]
            loc2 = db_locations[j]

            # Only walk between locations in the same city
            if loc1["city"] != loc2["city"]:
                continue

            dist = calculate_distance_km(loc1["latitude"], loc1["longitude"], loc2["latitude"], loc2["longitude"])
            
            # If locations are closer than 0.6 km (600 meters)
            if dist <= 0.6:
                # Walk speed: 5 km/h -> duration = (dist / 5.0) * 60 minutes
                duration = max(int(round((dist / 5.0) * 60.0)), 2)
                
                # Insert bidirectional walk routes
                cursor.execute(
                    """
                    INSERT INTO routes (source_location_id, destination_location_id, transport_mode, provider, duration_minutes, cost, distance_km, route_name)
                    VALUES (?, ?, 'walk', 'Walk', ?, 0.0, ?, 'Walking Transfer')
                    """,
                    (loc1["id"], loc2["id"], duration, dist)
                )
                cursor.execute(
                    """
                    INSERT INTO routes (source_location_id, destination_location_id, transport_mode, provider, duration_minutes, cost, distance_km, route_name)
                    VALUES (?, ?, 'walk', 'Walk', ?, 0.0, ?, 'Walking Transfer')
                    """,
                    (loc2["id"], loc1["id"], duration, dist)
                )
                walk_count += 2
    
    conn.commit()
    conn.close()
    print(f"Generated and seeded {walk_count} walking transfer routes.")

    # 5. Run importers
    print("\nRunning Metro data importer...")
    MetroImporter(DATABASE_PATH).run()

    print("\nRunning Railway data importer...")
    RailwayImporter(DATABASE_PATH).run()

    print("\nRunning Bus data importer...")
    BusImporter(DATABASE_PATH).run()

    # 6. Run Validation
    print("\nRunning Data Integrity Checks...")
    validator = DataValidator(DATABASE_PATH)
    report = validator.run_validation()
    validator.print_report(report)

if __name__ == "__main__":
    rebuild_db()
