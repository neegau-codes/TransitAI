import json
from typing import List
from providers.base_provider import TransportProvider
from models.transport import Segment

# Note: In a real-world system, this provider would fetch from KSRTC or state transport scheduling APIs.
# For this MVP, it queries the SQLite database to mock API data.

class BusProvider(TransportProvider):
    def get_provider_name(self) -> str:
        return "Bus Services"

    def get_all_segments(self, db_connection) -> List[Segment]:
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT s.id, s.source_id, loc1.name as source_name, 
                   s.destination_id, loc2.name as destination_name, 
                   s.mode, s.route_name, s.duration, s.cost, s.provider, s.schedule
            FROM segments s
            JOIN locations loc1 ON s.source_id = loc1.id
            JOIN locations loc2 ON s.destination_id = loc2.id
            WHERE s.mode = 'bus'
        """)
        rows = cursor.fetchall()
        
        segments = []
        for r in rows:
            schedule_list = []
            if r[10]:
                try:
                    schedule_list = json.loads(r[10])
                except json.JSONDecodeError:
                    schedule_list = [x.strip() for x in r[10].split(",") if x.strip()]
            
            segments.append(Segment(
                id=r[0],
                source_id=r[1],
                source_name=r[2],
                destination_id=r[3],
                destination_name=r[4],
                mode=r[5],
                route_name=r[6],
                duration=r[7],
                cost=r[8],
                provider=r[9] if r[9] else self.get_provider_name(),
                schedule=schedule_list
            ))
        return segments
