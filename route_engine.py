import networkx as nx
import json
import sqlite3
from typing import List, Dict, Any, Tuple
from database.db import get_db_connection
from models.transport import Location, Segment, RouteOption
from providers.railway_provider import RailwayProvider
from providers.metro_provider import MetroProvider
from providers.bus_provider import BusProvider

# Time conversion helpers
def time_to_mins(time_str: str) -> int:
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except Exception:
        return 0

def mins_to_time(mins: int) -> str:
    mins = mins % 1440
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"

class RouteEngine:
    def __init__(self):
        # Initialize providers
        self.providers = [
            RailwayProvider(),
            MetroProvider(),
            BusProvider()
        ]

    def _load_locations(self, conn) -> Dict[int, Location]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude, type FROM locations")
        rows = cursor.fetchall()
        locations = {}
        for r in rows:
            locations[r["id"]] = Location(
                id=r["id"],
                name=r["name"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                type=r["type"]
            )
        return locations

    def _load_walking_transfers(self, conn) -> List[Segment]:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.source_id, loc1.name as source_name, 
                   s.destination_id, loc2.name as destination_name, 
                   s.mode, s.route_name, s.duration, s.cost, s.provider, s.schedule
            FROM segments s
            JOIN locations loc1 ON s.source_id = loc1.id
            JOIN locations loc2 ON s.destination_id = loc2.id
            WHERE s.mode = 'walk'
        """)
        rows = cursor.fetchall()
        segments = []
        for r in rows:
            segments.append(Segment(
                id=r["id"],
                source_id=r["source_id"],
                source_name=r["source_name"],
                destination_id=r["destination_id"],
                destination_name=r["destination_name"],
                mode=r["mode"],
                route_name=r["route_name"],
                duration=r["duration"],
                cost=r["cost"],
                provider=r["provider"] or "Walk",
                schedule=[]
            ))
        return segments

    def build_graph(self) -> Tuple[nx.MultiDiGraph, Dict[int, Location]]:
        conn = get_db_connection()
        locations = self._load_locations(conn)
        
        # Collect all segments from providers
        all_segments = []
        for provider in self.providers:
            all_segments.extend(provider.get_all_segments(conn))
            
        # Add walking transfers
        all_segments.extend(self._load_walking_transfers(conn))
        conn.close()

        # Build Directed Graph
        G = nx.DiGraph()
        
        # Add nodes
        for loc_id, loc in locations.items():
            G.add_node(loc_id, name=loc.name, type=loc.type, lat=loc.latitude, lon=loc.longitude)
            
        # Add edges
        for seg in all_segments:
            G.add_edge(
                seg.source_id, 
                seg.destination_id, 
                duration=seg.duration,
                cost=seg.cost,
                mode=seg.mode,
                route_name=seg.route_name,
                provider=seg.provider,
                segment=seg
            )
            
        return G, locations

    def _simulate_schedule(self, G: nx.DiGraph, path_node_ids: List[int], departure_time_str: str) -> Tuple[List[Segment], int, float]:
        """
        Walks along the path, calculates real waiting times based on schedule,
        and returns the actual list of segments (with timing), total duration, and total cost.
        """
        current_mins = time_to_mins(departure_time_str)
        start_mins = current_mins
        total_cost = 0.0
        segments_taken = []
        
        for i in range(len(path_node_ids) - 1):
            u = path_node_ids[i]
            v = path_node_ids[i+1]
            
            # Find edge data between u and v
            data = G.get_edge_data(u, v)
            if not data:
                raise ValueError(f"No edge between {u} and {v}")
                
            seg = data['segment']
            
            # Walk segment: no schedule, can leave immediately
            if seg.mode == 'walk':
                wait_time = 0
                arrival = current_mins + seg.duration
                cost = seg.cost
            else:
                # Transit segment: find next departure
                if not seg.schedule:
                    # Fallback if schedule is missing: assume leaves in 5 mins
                    wait_time = 5
                else:
                    sched_mins = [time_to_mins(t) for t in seg.schedule]
                    # Filter for schedules after current time
                    valid_departures = [t for t in sched_mins if t >= current_mins]
                    if not valid_departures:
                        # If no more departures today, add a 60 min penalty wait
                        wait_time = 60
                    else:
                        next_dept = min(valid_departures)
                        wait_time = next_dept - current_mins
                        
                arrival = current_mins + wait_time + seg.duration
                cost = seg.cost
                
            # Create a localized segment copy with departure/arrival details
            dept_str = mins_to_time(current_mins + wait_time)
            arr_str = mins_to_time(arrival)
            
            localized_seg = Segment(
                id=seg.id,
                source_id=seg.source_id,
                source_name=seg.source_name,
                destination_id=seg.destination_id,
                destination_name=seg.destination_name,
                mode=seg.mode,
                route_name=f"{seg.route_name} (Dep: {dept_str}, Arr: {arr_str})",
                duration=seg.duration + wait_time,  # total duration including wait
                cost=cost,
                provider=seg.provider,
                schedule=seg.schedule
            )
            
            segments_taken.append(localized_seg)
            current_mins = arrival
            total_cost += cost
            
        total_duration = current_mins - start_mins
        return segments_taken, total_duration, total_cost

    def _count_transfers(self, segments: List[Segment]) -> int:
        """
        Counts transfers as transitions between different non-walk transit lines.
        """
        transit_routes = []
        for s in segments:
            if s.mode != 'walk':
                transit_routes.append(s.route_name.split(" (Dep:")[0])  # Strip time details
                
        if not transit_routes:
            return 0
            
        transfers = 0
        for i in range(len(transit_routes) - 1):
            # If the line name changes, that's a transfer
            if transit_routes[i] != transit_routes[i+1]:
                transfers += 1
        return transfers

    def find_routes(self, source_query: str, dest_query: str, departure_time: str) -> Dict[str, Any]:
        G, locations = self.build_graph()
        
        # Match locations by name (case-insensitive)
        src_ids = [lid for lid, loc in locations.items() if source_query.lower() in loc.name.lower()]
        dst_ids = [lid for lid, loc in locations.items() if dest_query.lower() in loc.name.lower()]
        
        if not src_ids:
            return {"error": f"Source location '{source_query}' not found."}
        if not dst_ids:
            return {"error": f"Destination location '{dest_query}' not found."}
            
        # Find all simple paths between any source and destination match
        # To avoid performance issues, we cap path length and search depth
        all_candidate_paths = []
        for s in src_ids:
            for d in dst_ids:
                if s == d:
                    continue
                try:
                    # Get K shortest paths by number of edges to find candidate topologies
                    paths = list(nx.shortest_simple_paths(G, s, d, weight='duration'))
                    # Take top 15 candidate paths
                    all_candidate_paths.extend(paths[:15])
                except nx.NetworkXNoPath:
                    continue
                    
        if not all_candidate_paths:
            return {"error": f"No routes found between '{source_query}' and '{dest_query}'."}
            
        # Evaluate each candidate path using schedule simulation
        evaluated_routes = []
        seen_paths = set()
        
        for path in all_candidate_paths:
            path_tuple = tuple(path)
            if path_tuple in seen_paths:
                continue
            seen_paths.add(path_tuple)
            
            try:
                segs, dur, cost = self._simulate_schedule(G, path, departure_time)
                transfers = self._count_transfers(segs)
                evaluated_routes.append({
                    "path_nodes": path,
                    "segments": segs,
                    "duration": dur,
                    "cost": cost,
                    "transfers": transfers
                })
            except Exception as e:
                # Skip invalid paths
                continue
                
        if not evaluated_routes:
            return {"error": "No valid schedules found for the travel window."}

        # Select the best for each preference category
        # 1. Fastest Route (min duration)
        fastest_raw = min(evaluated_routes, key=lambda x: x["duration"])
        fastest = RouteOption(
            segments=fastest_raw["segments"],
            total_duration=fastest_raw["duration"],
            total_cost=fastest_raw["cost"],
            transfers=fastest_raw["transfers"],
            type="Fastest Route"
        )
        
        # 2. Cheapest Route (min cost)
        cheapest_raw = min(evaluated_routes, key=lambda x: x["cost"])
        cheapest = RouteOption(
            segments=cheapest_raw["segments"],
            total_duration=cheapest_raw["duration"],
            total_cost=cheapest_raw["cost"],
            transfers=cheapest_raw["transfers"],
            type="Cheapest Route"
        )
        
        # 3. Fewest Transfers Route (min transfers, then duration)
        fewest_transfers_raw = min(evaluated_routes, key=lambda x: (x["transfers"], x["duration"]))
        fewest_transfers = RouteOption(
            segments=fewest_transfers_raw["segments"],
            total_duration=fewest_transfers_raw["duration"],
            total_cost=fewest_transfers_raw["cost"],
            transfers=fewest_transfers_raw["transfers"],
            type="Fewest Transfers"
        )

        return {
            "fastest": fastest.to_dict(),
            "cheapest": cheapest.to_dict(),
            "fewest_transfers": fewest_transfers.to_dict()
        }
