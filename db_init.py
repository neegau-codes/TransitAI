import sqlite3
import os
import json

DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "transit.db")

def init_db():
    # Ensure database directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create locations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            latitude REAL,
            longitude REAL,
            type TEXT NOT NULL
        )
    """)
    
    # Create segments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            destination_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            route_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            cost REAL NOT NULL,
            provider TEXT,
            schedule TEXT,
            FOREIGN KEY (source_id) REFERENCES locations(id),
            FOREIGN KEY (destination_id) REFERENCES locations(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database schema initialized successfully.")

def seed_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Clear existing data to avoid duplication
    cursor.execute("DELETE FROM segments")
    cursor.execute("DELETE FROM locations")
    conn.commit()
    
    # Sample Locations
    locations = [
        # Aluva Hub
        ("Aluva Railway Station", 10.1081, 76.3563, "railway_station"),
        ("Aluva Metro Station", 10.1095, 76.3570, "metro_station"),
        ("Aluva Bus Stand", 10.1090, 76.3558, "bus_stop"),
        # Kalamassery Hub
        ("Kalamassery Metro Station", 10.0520, 76.3210, "metro_station"),
        ("Kalamassery Bus Stop", 10.0515, 76.3205, "bus_stop"),
        # Edappally Hub
        ("Edappally Metro Station", 10.0245, 76.3078, "metro_station"),
        ("Edappally Bus Stop", 10.0240, 76.3070, "bus_stop"),
        # Kaloor Hub
        ("Kaloor Metro Station", 9.9912, 76.2905, "metro_station"),
        ("Kaloor Bus Stop", 9.9908, 76.2900, "bus_stop"),
        # Ernakulam Town (North) Hub
        ("Ernakulam Town Railway Station", 9.9922, 76.2870, "railway_station"),
        ("Town Hall Metro Station", 9.9918, 76.2885, "metro_station"),
        ("North Bus Stop", 9.9910, 76.2865, "bus_stop"),
        # Ernakulam South Hub
        ("Ernakulam Junction Railway Station", 9.9678, 76.2860, "railway_station"),
        ("Ernakulam South Metro Station", 9.9682, 76.2875, "metro_station"),
        ("South Bus Stop", 9.9670, 76.2855, "bus_stop"),
        # Vytila Hub
        ("Vytila Metro Station", 9.9690, 76.3200, "metro_station"),
        ("Vytila Mobility Hub", 9.9685, 76.3210, "bus_stop"),
        # Tripunithura Hub
        ("Tripunithura Railway Station", 9.9520, 76.3500, "railway_station"),
        ("Tripunithura Metro Station", 9.9535, 76.3512, "metro_station"),
        ("Tripunithura Bus Stand", 9.9515, 76.3490, "bus_stop")
    ]
    
    cursor.executemany(
        "INSERT INTO locations (name, latitude, longitude, type) VALUES (?, ?, ?, ?)",
        locations
    )
    conn.commit()
    
    # Retrieve inserted location IDs
    cursor.execute("SELECT name, id FROM locations")
    loc_id = {name: id for name, id in cursor.fetchall()}
    
    # Schedules definitions
    metro_sched = json.dumps([f"{h:02d}:{m:02d}" for h in range(6, 23) for m in (0, 10, 20, 30, 40, 50)])
    bus_sched = json.dumps([f"{h:02d}:{m:02d}" for h in range(6, 22) for m in (0, 15, 30, 45)])
    
    train_aluva_to_town = json.dumps(["07:30", "08:45", "10:15", "11:30", "13:00", "15:45", "18:20", "20:10"])
    train_town_to_aluva = json.dumps(["08:15", "09:30", "11:00", "12:15", "13:45", "16:30", "19:05", "20:55"])
    
    train_aluva_to_south = json.dumps(["06:15", "08:00", "09:40", "11:10", "14:15", "17:30", "19:45"])
    train_south_to_aluva = json.dumps(["07:00", "08:45", "10:30", "12:00", "15:00", "18:15", "20:30"])
    
    train_town_to_south = json.dumps(["07:50", "09:05", "10:35", "11:50", "13:20", "16:05", "18:40", "20:30"])
    train_south_to_town = json.dumps(["07:20", "08:35", "10:05", "11:20", "12:50", "15:35", "18:10", "20:00"])
    
    train_south_to_trip = json.dumps(["06:45", "08:30", "10:00", "12:15", "15:30", "18:45", "21:00"])
    train_trip_to_south = json.dumps(["07:15", "09:00", "10:30", "12:45", "16:00", "19:15", "21:30"])
    
    segments = [
        # --- METRO SYSTEM (KMRL) ---
        # Aluva <-> Kalamassery
        (loc_id["Aluva Metro Station"], loc_id["Kalamassery Metro Station"], "metro", "Kochi Metro Line 1", 8, 20.0, "KMRL", metro_sched),
        (loc_id["Kalamassery Metro Station"], loc_id["Aluva Metro Station"], "metro", "Kochi Metro Line 1", 8, 20.0, "KMRL", metro_sched),
        
        # Kalamassery <-> Edappally
        (loc_id["Kalamassery Metro Station"], loc_id["Edappally Metro Station"], "metro", "Kochi Metro Line 1", 6, 20.0, "KMRL", metro_sched),
        (loc_id["Edappally Metro Station"], loc_id["Kalamassery Metro Station"], "metro", "Kochi Metro Line 1", 6, 20.0, "KMRL", metro_sched),
        
        # Edappally <-> Kaloor
        (loc_id["Edappally Metro Station"], loc_id["Kaloor Metro Station"], "metro", "Kochi Metro Line 1", 5, 10.0, "KMRL", metro_sched),
        (loc_id["Kaloor Metro Station"], loc_id["Edappally Metro Station"], "metro", "Kochi Metro Line 1", 5, 10.0, "KMRL", metro_sched),
        
        # Kaloor <-> Town Hall
        (loc_id["Kaloor Metro Station"], loc_id["Town Hall Metro Station"], "metro", "Kochi Metro Line 1", 4, 10.0, "KMRL", metro_sched),
        (loc_id["Town Hall Metro Station"], loc_id["Kaloor Metro Station"], "metro", "Kochi Metro Line 1", 4, 10.0, "KMRL", metro_sched),
        
        # Town Hall <-> Ernakulam South
        (loc_id["Town Hall Metro Station"], loc_id["Ernakulam South Metro Station"], "metro", "Kochi Metro Line 1", 5, 10.0, "KMRL", metro_sched),
        (loc_id["Ernakulam South Metro Station"], loc_id["Town Hall Metro Station"], "metro", "Kochi Metro Line 1", 5, 10.0, "KMRL", metro_sched),
        
        # Ernakulam South <-> Vytila
        (loc_id["Ernakulam South Metro Station"], loc_id["Vytila Metro Station"], "metro", "Kochi Metro Line 1", 7, 20.0, "KMRL", metro_sched),
        (loc_id["Vytila Metro Station"], loc_id["Ernakulam South Metro Station"], "metro", "Kochi Metro Line 1", 7, 20.0, "KMRL", metro_sched),
        
        # Vytila <-> Tripunithura
        (loc_id["Vytila Metro Station"], loc_id["Tripunithura Metro Station"], "metro", "Kochi Metro Line 1", 8, 20.0, "KMRL", metro_sched),
        (loc_id["Tripunithura Metro Station"], loc_id["Vytila Metro Station"], "metro", "Kochi Metro Line 1", 8, 20.0, "KMRL", metro_sched),
        
        # --- RAILWAY SYSTEM (Indian Railways) ---
        # Aluva <-> Ernakulam Town (North)
        (loc_id["Aluva Railway Station"], loc_id["Ernakulam Town Railway Station"], "train", "Venad Express (16302)", 18, 15.0, "Indian Railways", train_aluva_to_town),
        (loc_id["Ernakulam Town Railway Station"], loc_id["Aluva Railway Station"], "train", "Venad Express (16301)", 18, 15.0, "Indian Railways", train_town_to_aluva),
        
        # Aluva <-> Ernakulam Junction (South)
        (loc_id["Aluva Railway Station"], loc_id["Ernakulam Junction Railway Station"], "train", "Parasuram Express (16650)", 22, 15.0, "Indian Railways", train_aluva_to_south),
        (loc_id["Ernakulam Junction Railway Station"], loc_id["Aluva Railway Station"], "train", "Parasuram Express (16649)", 22, 15.0, "Indian Railways", train_south_to_aluva),
        
        # Ernakulam Town <-> Ernakulam Junction
        (loc_id["Ernakulam Town Railway Station"], loc_id["Ernakulam Junction Railway Station"], "train", "Ernakulam Shuttle (06451)", 10, 10.0, "Indian Railways", train_town_to_south),
        (loc_id["Ernakulam Junction Railway Station"], loc_id["Ernakulam Town Railway Station"], "train", "Ernakulam Shuttle (06452)", 10, 10.0, "Indian Railways", train_south_to_town),
        
        # Ernakulam Junction <-> Tripunithura
        (loc_id["Ernakulam Junction Railway Station"], loc_id["Tripunithura Railway Station"], "train", "Tea Garden Express (16188)", 12, 10.0, "Indian Railways", train_south_to_trip),
        (loc_id["Tripunithura Railway Station"], loc_id["Ernakulam Junction Railway Station"], "train", "Tea Garden Express (16187)", 12, 10.0, "Indian Railways", train_trip_to_south),
        
        # --- BUS SERVICES (KSRTC & Private) ---
        # Aluva <-> Kalamassery
        (loc_id["Aluva Bus Stand"], loc_id["Kalamassery Bus Stop"], "bus", "KSRTC Ordinary (Suburban)", 15, 10.0, "KSRTC", bus_sched),
        (loc_id["Kalamassery Bus Stop"], loc_id["Aluva Bus Stand"], "bus", "KSRTC Ordinary (Suburban)", 15, 10.0, "KSRTC", bus_sched),
        
        # Kalamassery <-> Edappally
        (loc_id["Kalamassery Bus Stop"], loc_id["Edappally Bus Stop"], "bus", "Private Bus Line 12", 12, 10.0, "Private Bus", bus_sched),
        (loc_id["Edappally Bus Stop"], loc_id["Kalamassery Bus Stop"], "bus", "Private Bus Line 12", 12, 10.0, "Private Bus", bus_sched),
        
        # Edappally <-> Kaloor
        (loc_id["Edappally Bus Stop"], loc_id["Kaloor Bus Stop"], "bus", "Private Bus Line 12", 10, 8.0, "Private Bus", bus_sched),
        (loc_id["Kaloor Bus Stop"], loc_id["Edappally Bus Stop"], "bus", "Private Bus Line 12", 10, 8.0, "Private Bus", bus_sched),
        
        # Kaloor <-> North Bus Stop
        (loc_id["Kaloor Bus Stop"], loc_id["North Bus Stop"], "bus", "KSRTC Ordinary (Suburban)", 8, 8.0, "KSRTC", bus_sched),
        (loc_id["North Bus Stop"], loc_id["Kaloor Bus Stop"], "bus", "KSRTC Ordinary (Suburban)", 8, 8.0, "KSRTC", bus_sched),
        
        # North Bus Stop <-> South Bus Stop
        (loc_id["North Bus Stop"], loc_id["South Bus Stop"], "bus", "KSRTC Town Circular", 10, 8.0, "KSRTC", bus_sched),
        (loc_id["South Bus Stop"], loc_id["North Bus Stop"], "bus", "KSRTC Town Circular", 10, 8.0, "KSRTC", bus_sched),
        
        # South Bus Stop <-> Vytila Mobility Hub
        (loc_id["South Bus Stop"], loc_id["Vytila Mobility Hub"], "bus", "Private Bus Line 25", 15, 10.0, "Private Bus", bus_sched),
        (loc_id["Vytila Mobility Hub"], loc_id["South Bus Stop"], "bus", "Private Bus Line 25", 15, 10.0, "Private Bus", bus_sched),
        
        # Vytila Mobility Hub <-> Tripunithura Bus Stand
        (loc_id["Vytila Mobility Hub"], loc_id["Tripunithura Bus Stand"], "bus", "KSRTC Ordinary (Suburban)", 15, 10.0, "KSRTC", bus_sched),
        (loc_id["Tripunithura Bus Stand"], loc_id["Vytila Mobility Hub"], "bus", "KSRTC Ordinary (Suburban)", 15, 10.0, "KSRTC", bus_sched),
        
        # Direct Express Bus (Aluva <-> Vytila)
        (loc_id["Aluva Bus Stand"], loc_id["Vytila Mobility Hub"], "bus", "KSRTC Fast Passenger (Direct)", 40, 28.0, "KSRTC", bus_sched),
        (loc_id["Vytila Mobility Hub"], loc_id["Aluva Bus Stand"], "bus", "KSRTC Fast Passenger (Direct)", 40, 28.0, "KSRTC", bus_sched),

        # --- WALKING TRANSFERS (0 cost, quick links within hubs) ---
        # Aluva
        (loc_id["Aluva Railway Station"], loc_id["Aluva Metro Station"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        (loc_id["Aluva Metro Station"], loc_id["Aluva Railway Station"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        (loc_id["Aluva Bus Stand"], loc_id["Aluva Metro Station"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["Aluva Metro Station"], loc_id["Aluva Bus Stand"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["Aluva Railway Station"], loc_id["Aluva Bus Stand"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        (loc_id["Aluva Bus Stand"], loc_id["Aluva Railway Station"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        
        # Kalamassery
        (loc_id["Kalamassery Metro Station"], loc_id["Kalamassery Bus Stop"], "walk", "Walking Transfer", 2, 0.0, "Walk", None),
        (loc_id["Kalamassery Bus Stop"], loc_id["Kalamassery Metro Station"], "walk", "Walking Transfer", 2, 0.0, "Walk", None),
        
        # Edappally
        (loc_id["Edappally Metro Station"], loc_id["Edappally Bus Stop"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        (loc_id["Edappally Bus Stop"], loc_id["Edappally Metro Station"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        
        # Kaloor
        (loc_id["Kaloor Metro Station"], loc_id["Kaloor Bus Stop"], "walk", "Walking Transfer", 2, 0.0, "Walk", None),
        (loc_id["Kaloor Bus Stop"], loc_id["Kaloor Metro Station"], "walk", "Walking Transfer", 2, 0.0, "Walk", None),
        
        # Ernakulam Town / Town Hall (North)
        (loc_id["Town Hall Metro Station"], loc_id["Ernakulam Town Railway Station"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        (loc_id["Ernakulam Town Railway Station"], loc_id["Town Hall Metro Station"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        (loc_id["Town Hall Metro Station"], loc_id["North Bus Stop"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["North Bus Stop"], loc_id["Town Hall Metro Station"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["Ernakulam Town Railway Station"], loc_id["North Bus Stop"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        (loc_id["North Bus Stop"], loc_id["Ernakulam Town Railway Station"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        
        # Ernakulam South / Junction
        (loc_id["Ernakulam South Metro Station"], loc_id["Ernakulam Junction Railway Station"], "walk", "Walking Transfer", 6, 0.0, "Walk", None),
        (loc_id["Ernakulam Junction Railway Station"], loc_id["Ernakulam South Metro Station"], "walk", "Walking Transfer", 6, 0.0, "Walk", None),
        (loc_id["Ernakulam South Metro Station"], loc_id["South Bus Stop"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["South Bus Stop"], loc_id["Ernakulam South Metro Station"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["Ernakulam Junction Railway Station"], loc_id["South Bus Stop"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        (loc_id["South Bus Stop"], loc_id["Ernakulam Junction Railway Station"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        
        # Vytila
        (loc_id["Vytila Metro Station"], loc_id["Vytila Mobility Hub"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        (loc_id["Vytila Mobility Hub"], loc_id["Vytila Metro Station"], "walk", "Walking Transfer", 3, 0.0, "Walk", None),
        
        # Tripunithura
        (loc_id["Tripunithura Metro Station"], loc_id["Tripunithura Railway Station"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        (loc_id["Tripunithura Railway Station"], loc_id["Tripunithura Metro Station"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        (loc_id["Tripunithura Metro Station"], loc_id["Tripunithura Bus Stand"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["Tripunithura Bus Stand"], loc_id["Tripunithura Metro Station"], "walk", "Walking Transfer", 4, 0.0, "Walk", None),
        (loc_id["Tripunithura Railway Station"], loc_id["Tripunithura Bus Stand"], "walk", "Walking Transfer", 5, 0.0, "Walk", None),
        (loc_id["Tripunithura Bus Stand"], loc_id["Tripunithura Railway Station"], "walk", "Walking Transfer", 5, 0.0, "Walk", None)
    ]
    
    cursor.executemany(
        "INSERT INTO segments (source_id, destination_id, mode, route_name, duration, cost, provider, schedule) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        segments
    )
    conn.commit()
    conn.close()
    print("Database seeded with sample data successfully.")

if __name__ == "__main__":
    init_db()
    seed_db()
