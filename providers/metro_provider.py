import json
from typing import List
from providers.base_provider import TransportProvider
from models.transport import Segment

# Note: In a real-world system, this provider would fetch from Kochi Metro (KMRL).
# For this MVP, it queries the SQLite database to mock API data.

class MetroProvider(TransportProvider):
    def get_provider_name(self) -> str:
        return "Metro Systems"

    def get_all_segments(self, db_connection) -> List[Segment]:
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT r.id, r.source_location_id, loc1.name as source_name, 
                   r.destination_location_id, loc2.name as destination_name, 
                   r.transport_mode, r.route_name, r.duration_minutes, r.cost, r.provider,
                   group_concat(s.departure_time, ',') as schedule_list
            FROM routes r
            JOIN locations loc1 ON r.source_location_id = loc1.id
            JOIN locations loc2 ON r.destination_location_id = loc2.id
            LEFT JOIN schedules s ON r.id = s.route_id
            WHERE r.transport_mode = 'metro'
            GROUP BY r.id
        """)
        rows = cursor.fetchall()
        
        segments = []
        for r in rows:
            schedule_list = []
            if r["schedule_list"]:
                try:
                    schedule_list = sorted([x.strip() for x in r["schedule_list"].split(",") if x.strip()])
                except Exception:
                    schedule_list = []
            
            segments.append(Segment(
                id=r["id"],
                source_id=r["source_location_id"],
                source_name=r["source_name"],
                destination_id=r["destination_location_id"],
                destination_name=r["destination_name"],
                mode=r["transport_mode"],
                route_name=r["route_name"],
                duration=r["duration_minutes"],
                cost=r["cost"],
                provider=r["provider"] if r["provider"] else self.get_provider_name(),
                schedule=schedule_list
            ))
        return segments
