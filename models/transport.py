from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

VALID_STATUSES = {"LIVE", "SCHEDULED", "ESTIMATED", "UNAVAILABLE"}
VALID_SOURCES = {"KMRL", "RAILWAY", "KSRTC", "ESTIMATED"}

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
class JourneyLeg:
    id: int = 0
    source_id: int = 0
    source_name: str = ""
    destination_id: int = 0
    destination_name: str = ""
    mode: str = "walk"  # 'metro', 'train', 'bus', 'walk'
    route_name: str = ""
    duration: int = 0  # in minutes
    cost: float = 0.0  # in INR
    provider: str = "ESTIMATED"  # 'KMRL', 'RAILWAY', 'KSRTC', 'ESTIMATED'
    schedule: List[str] = field(default_factory=list)

    # V2 explicit fields
    departure: str = ""
    arrival: str = ""
    status: str = "SCHEDULED"  # 'LIVE', 'SCHEDULED', 'ESTIMATED', 'UNAVAILABLE'
    source: str = "KMRL"      # 'KMRL', 'RAILWAY', 'KSRTC', 'ESTIMATED'
    geometry: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Normalize status & source defaults based on mode / provider
        if self.mode and self.mode.lower() == "walk":
            self.status = "ESTIMATED"
            self.source = "ESTIMATED"
            if not self.provider or self.provider == "Walk":
                self.provider = "ESTIMATED"
        else:
            if self.provider and self.provider.upper() in VALID_SOURCES:
                self.source = self.provider.upper()
                self.provider = self.provider.upper()
            elif self.provider == "Indian Railways":
                self.source = "RAILWAY"
                self.provider = "RAILWAY"
            elif self.provider in ("Metro Systems", "Metro"):
                self.source = "KMRL"
                self.provider = "KMRL"
            elif self.provider in ("Bus Systems", "Bus"):
                self.source = "KSRTC"
                self.provider = "KSRTC"
            else:
                self.source = "ESTIMATED"
                self.status = "ESTIMATED"
                if not self.provider:
                    self.provider = "ESTIMATED"

        if self.status not in VALID_STATUSES:
            self.status = "SCHEDULED"

    @property
    def duration_minutes(self) -> int:
        return self.duration

    @property
    def from_location(self) -> str:
        return self.source_name

    @property
    def to_location(self) -> str:
        return self.destination_name

    def to_dict(self):
        """Backward-compatible dictionary representation."""
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
            "schedule": self.schedule,
            "status": self.status,
            "source": self.source,
            # Explicit departure/arrival times set by route_engine (HH:MM format).
            # These are preserved here so recommendation_engine and normalize_route
            # can use them directly without re-parsing route_name.
            "departure": self.departure if self.departure else None,
            "arrival": self.arrival if self.arrival else None,
        }

    def to_v2_dict(self) -> Dict[str, Any]:
        """V2 API contract representation for a journey leg."""
        # Extract times if present in route_name e.g. "(Dep: 08:10, Arr: 08:50)"
        dept = self.departure
        arr = self.arrival
        if not dept or not arr:
            import re
            m = re.search(r'Dep:\s*(\d{2}:\d{2}),\s*Arr:\s*(\d{2}:\d{2})', self.route_name)
            if m:
                dept = dept or m.group(1)
                arr = arr or m.group(2)

        mode_upper = self.mode.upper() if self.mode else "WALK"
        if mode_upper == "TRAIN":
            mode_upper = "TRAIN"

        res = {
            "mode": mode_upper,
            "from": self.source_name,
            "to": self.destination_name,
            "departure": dept or None,
            "arrival": arr or None,
            "duration_minutes": self.duration,
            "fare": {
                "amount": self.cost,
                "currency": "INR",
                "status": self.status
            },
            "status": self.status,
            "source": self.source
        }
        if self.geometry is not None:
            res["geometry"] = self.geometry
        return res

# Alias Segment to JourneyLeg for full backward compatibility
Segment = JourneyLeg

@dataclass
class Journey:
    segments: List[JourneyLeg] = field(default_factory=list)
    total_duration: int = 0  # minutes
    total_cost: float = 0.0  # INR
    transfers: int = 0
    type: str = "BEST"      # Legacy/internal label: 'Fastest', 'Cheapest', 'Fewest Transfers', 'BEST'
    # V2 explicit fields

    route_id: Optional[str] = None
    label: Optional[str] = None  # 'BEST', 'FASTEST', 'CHEAPEST', 'LEAST WALKING'
    walking_minutes: int = 0
    status: str = "SCHEDULED"
    legs: List[JourneyLeg] = field(default_factory=list)

    def __post_init__(self):
        if self.segments and not self.legs:
            self.legs = self.segments
        elif self.legs and not self.segments:
            self.segments = self.legs

        # Calculate walking minutes if not set
        if not self.walking_minutes and self.legs:
            self.walking_minutes = sum(l.duration for l in self.legs if l.mode.lower() == "walk")

        # Set status based on leg statuses (if any leg is LIVE -> LIVE, else SCHEDULED)
        if self.legs:
            if any(l.status == "LIVE" for l in self.legs):
                self.status = "LIVE"
            elif all(l.status == "ESTIMATED" for l in self.legs):
                self.status = "ESTIMATED"

    def to_dict(self):
        """Backward-compatible dictionary representation."""
        return {
            "segments": [s.to_dict() for s in self.segments],
            "total_duration": self.total_duration,
            "total_cost": self.total_cost,
            "transfers": self.transfers,
            "type": self.type,
            "route_id": self.route_id,
            "label": self.label or self.type,
            "walking_minutes": self.walking_minutes,
            "status": self.status
        }

    def to_v2_dict(self) -> Dict[str, Any]:
        """V2 API contract representation for a journey / route option."""
        lbl = self.label
        if not lbl:
            t = (self.type or "").upper()
            if "FASTEST" in t:
                lbl = "FASTEST"
            elif "CHEAPEST" in t:
                lbl = "CHEAPEST"
            elif "WALK" in t:
                lbl = "LEAST WALKING"
            else:
                lbl = "BEST"

        return {
            "route_id": self.route_id or "ta_001",
            "label": lbl,
            "duration_minutes": self.total_duration,
            "fare": {
                "amount": self.total_cost,
                "currency": "INR",
                "status": self.status
            },
            "transfers": self.transfers,
            "walking_minutes": self.walking_minutes,
            "status": self.status,
            "legs": [l.to_v2_dict() for l in (self.legs or self.segments)]
        }

# Alias RouteOption to Journey for full backward compatibility
RouteOption = Journey
