import sqlite3
import os
from database.db import DATABASE_PATH

class BaseImporter:
    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self._conn = None

    def connect(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_location_id(self, cursor, name: str) -> int:
        """Finds the ID of a location by its name (exact, case-insensitive)."""
        cursor.execute("SELECT id FROM locations WHERE LOWER(name) = LOWER(?)", (name.strip(),))
        row = cursor.fetchone()
        if row:
            return row["id"]
        
        # Fallback partial matching
        cursor.execute("SELECT id, name FROM locations WHERE LOWER(name) LIKE LOWER(?)", (f"%{name.strip()}%",))
        rows = cursor.fetchall()
        if rows:
            # Return the exact/best match if possible
            return rows[0]["id"]
            
        raise ValueError(f"Location not found in database: '{name}'")

    def ensure_provider(self, cursor, provider_name: str, transport_type: str) -> int:
        """Ensures a provider exists in the providers table and returns its ID."""
        cursor.execute("SELECT id FROM providers WHERE provider_name = ?", (provider_name,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        
        cursor.execute(
            "INSERT INTO providers (provider_name, transport_type) VALUES (?, ?)",
            (provider_name, transport_type)
        )
        return cursor.lastrowid

    def insert_route(self, cursor, source_id: int, dest_id: int, mode: str, provider: str, duration: int, cost: float, distance: float, route_name: str) -> int:
        """Inserts a route entry and returns its ID."""
        cursor.execute(
            """
            INSERT INTO routes (source_location_id, destination_location_id, transport_mode, provider, duration_minutes, cost, distance_km, route_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, dest_id, mode, provider, duration, cost, distance, route_name)
        )
        return cursor.lastrowid

    def insert_schedule(self, cursor, route_id: int, departure_time: str, arrival_time: str):
        """Inserts a schedule entry."""
        cursor.execute(
            "INSERT INTO schedules (route_id, departure_time, arrival_time) VALUES (?, ?, ?)",
            (route_id, departure_time, arrival_time)
        )

    def time_to_mins(self, time_str: str) -> int:
        """Converts HH:MM format into minutes past midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    def mins_to_time(self, mins: int) -> str:
        """Converts minutes past midnight into HH:MM format."""
        mins = mins % 1440
        h = mins // 60
        m = mins % 60
        return f"{h:02d}:{m:02d}"

    def calculate_arrival(self, departure_time: str, duration_minutes: int) -> str:
        """Calculates arrival time string given a departure time and duration."""
        dept_mins = self.time_to_mins(departure_time)
        arr_mins = dept_mins + duration_minutes
        return self.mins_to_time(arr_mins)
