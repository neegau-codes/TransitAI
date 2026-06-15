from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Location:
    id: int
    name: str
    latitude: float
    longitude: float
    type: str  # 'metro_station', 'railway_station', 'bus_stop', 'transfer_point'

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "type": self.type
        }

@dataclass
class Segment:
    id: int
    source_id: int
    source_name: str
    destination_id: int
    destination_name: str
    mode: str  # 'metro', 'train', 'bus', 'walk'
    route_name: str  # e.g., 'Kochi Metro Blue Line', 'Venad Express (16302)'
    duration: int  # in minutes
    cost: float  # in INR
    provider: str  # e.g., 'KMRL', 'Indian Railways', 'KSRTC'
    schedule: List[str] = field(default_factory=list)  # list of departure times, e.g. ['08:00', '08:30']

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "destination_id": self.destination_id,
            "destination_name": self.destination_name,
            "mode": self.mode,
            "route_name": self.route_name,
            "duration": self.duration,
            "cost": self.cost,
            "provider": self.provider,
            "schedule": self.schedule
        }

@dataclass
class RouteOption:
    segments: List[Segment]
    total_duration: int  # minutes
    total_cost: float  # INR
    transfers: int
    type: str  # 'Fastest', 'Cheapest', 'Fewest Transfers'

    def to_dict(self):
        return {
            "segments": [s.to_dict() for s in self.segments],
            "total_duration": self.total_duration,
            "total_cost": self.total_cost,
            "transfers": self.transfers,
            "type": self.type
        }
