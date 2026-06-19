"""
route_engine.py
Upgraded routing engine for TransitAI.
Uses NetworkX MultiDiGraph, handles schedule constraints, transfers, and optimization criteria.
"""

import networkx as nx
import sqlite3
from typing import List, Dict, Any, Tuple, Optional
from database.db import get_db_connection
from models.transport import Location, Segment, RouteOption
from providers.railway_provider import RailwayProvider
from providers.metro_provider import MetroProvider
from providers.bus_provider import BusProvider
import scheduler

class RouteEngine:
    def __init__(self):
        # Initialize providers
        self.providers = [
            RailwayProvider(),
            MetroProvider(),
            BusProvider()
        ]
        # Configurable scoring weights
        self.weight_time = 0.4
        self.weight_cost = 0.4
        self.weight_transfers = 0.2

    def set_weights(self, time_w: float, cost_w: float, transfer_w: float):
        """Allows dynamic configuration of optimization weights."""
        total = time_w + cost_w + transfer_w
        if total > 0:
            self.weight_time = time_w / total
            self.weight_cost = cost_w / total
            self.weight_transfers = transfer_w / total

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
            SELECT r.id, r.source_location_id, loc1.name as source_name, 
                   r.destination_location_id, loc2.name as destination_name, 
                   r.transport_mode, r.route_name, r.duration_minutes, r.cost, r.provider
            FROM routes r
            JOIN locations loc1 ON r.source_location_id = loc1.id
            JOIN locations loc2 ON r.destination_location_id = loc2.id
            WHERE r.transport_mode = 'walk'
        """)
        rows = cursor.fetchall()
        segments = []
        for r in rows:
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
                provider=r["provider"] or "Walk",
                schedule=[]
            ))
        return segments

    def build_graph(self) -> Tuple[nx.MultiDiGraph, Dict[int, Location]]:
        """Builds a MultiDiGraph of the multi-modal transit network."""
        conn = get_db_connection()
        locations = self._load_locations(conn)
        
        # Collect all segments from providers
        all_segments = []
        for provider in self.providers:
            all_segments.extend(provider.get_all_segments(conn))
            
        # Add walking transfers
        all_segments.extend(self._load_walking_transfers(conn))
        conn.close()

        # Build Directed MultiGraph to support parallel edges (e.g. metro and bus between same nodes)
        G = nx.MultiDiGraph()
        
        # Add nodes
        for loc_id, loc in locations.items():
            G.add_node(loc_id, name=loc.name, type=loc.type, lat=loc.latitude, lon=loc.longitude)
            
        # Add edges
        for seg in all_segments:
            G.add_edge(
                seg.source_id, 
                seg.destination_id, 
                key=f"{seg.mode}_{seg.id}",
                duration=seg.duration,
                cost=seg.cost,
                mode=seg.mode,
                route_name=seg.route_name,
                provider=seg.provider,
                segment=seg
            )
            
        return G, locations

    def _simulate_schedule(
        self, 
        G: nx.MultiDiGraph, 
        path_node_ids: List[int], 
        departure_time_str: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Segment], int, float, int]:
        """
        Simulates travel along a specific node sequence path starting at departure_time_str.
        Returns the segments taken (with adjusted departure/arrival times),
        total duration (including wait), total cost, and transfer count.
        """
        current_mins = scheduler.time_to_mins(departure_time_str)
        start_mins = current_mins
        total_cost = 0.0
        segments_taken = []
        
        excluded_modes = []
        if constraints and "excluded_modes" in constraints:
            excluded_modes = constraints["excluded_modes"]

        for i in range(len(path_node_ids) - 1):
            u = path_node_ids[i]
            v = path_node_ids[i+1]
            
            # Find all multi-edges between u and v
            edges = G.get_edge_data(u, v)
            if not edges:
                raise ValueError(f"No edge between {u} and {v}")
                
            best_arrival = None
            best_segment = None
            best_wait = 0
            best_cost = 0.0
            
            for key, data in edges.items():
                seg = data['segment']
                
                # Check mode constraint
                if seg.mode in excluded_modes:
                    continue
                    
                if seg.mode == 'walk':
                    wait_time = 0
                    arrival = current_mins + seg.duration
                    cost = seg.cost
                else:
                    # Transit segment: calculate next departure
                    # If this is a transfer (previous segment was transit, and mode/route differs)
                    min_wait = 0
                    if segments_taken:
                        prev_seg = segments_taken[-1]
                        # Transfer required if switching routes/modes
                        if prev_seg.mode != 'walk' and (prev_seg.mode != seg.mode or prev_seg.route_name.split(" (Dep:")[0] != seg.route_name):
                            min_wait = 5  # 5 minutes transfer cushion
                    
                    next_dept_time = scheduler.get_next_departure(
                        seg.schedule, 
                        scheduler.mins_to_time(current_mins), 
                        min_wait
                    )
                    
                    if not next_dept_time:
                        # Skip this transit mode if no further departures
                        continue
                        
                    wait_time = scheduler.calculate_waiting_time(
                        scheduler.mins_to_time(current_mins), 
                        next_dept_time
                    )
                    arrival = current_mins + wait_time + seg.duration
                    cost = seg.cost
                    
                if best_arrival is None or arrival < best_arrival:
                    best_arrival = arrival
                    best_segment = seg
                    best_wait = wait_time
                    best_cost = cost
            
            if best_segment is None:
                raise ValueError(f"No valid transit connections from {u} to {v} in window")
                
            dept_str = scheduler.mins_to_time(current_mins + best_wait)
            arr_str = scheduler.mins_to_time(best_arrival)
            
            localized_seg = Segment(
                id=best_segment.id,
                source_id=best_segment.source_id,
                source_name=best_segment.source_name,
                destination_id=best_segment.destination_id,
                destination_name=best_segment.destination_name,
                mode=best_segment.mode,
                route_name=f"{best_segment.route_name} (Dep: {dept_str}, Arr: {arr_str})",
                duration=best_segment.duration + best_wait,  # includes waiting time
                cost=best_cost,
                provider=best_segment.provider,
                schedule=best_segment.schedule
            )
            
            segments_taken.append(localized_seg)
            current_mins = best_arrival
            total_cost += best_cost
            
        total_duration = current_mins - start_mins
        transfers = self._count_transfers(segments_taken)
        
        return segments_taken, total_duration, total_cost, transfers

    def _count_transfers(self, segments: List[Segment]) -> int:
        """
        Counts transfers as transitions between different non-walk transit runs.
        """
        transit_segments = [s for s in segments if s.mode != 'walk']
        if not transit_segments:
            return 0
            
        transfers = 0
        for i in range(len(transit_segments) - 1):
            s1 = transit_segments[i]
            s2 = transit_segments[i+1]
            
            # Clean route name of times: "Metro Line 1 (Dep: 09:00)" -> "Metro Line 1"
            name1 = s1.route_name.split(" (Dep:")[0]
            name2 = s2.route_name.split(" (Dep:")[0]
            
            if name1 != name2 or s1.mode != s2.mode:
                transfers += 1
        return transfers

    def find_routes(
        self, 
        source_query: str, 
        dest_query: str, 
        departure_time: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Finds and ranks routes between source and destination matching queries.
        Supports filtering by budget, arrival deadline, and ranking using balanced scoring.
        """
        G, locations = self.build_graph()
        
        # Match locations by name (case-insensitive)
        src_ids = [lid for lid, loc in locations.items() if source_query.lower() in loc.name.lower()]
        dst_ids = [lid for lid, loc in locations.items() if dest_query.lower() in loc.name.lower()]
        
        if not src_ids:
            return {"error": f"Source location '{source_query}' not found."}
        if not dst_ids:
            return {"error": f"Destination location '{dest_query}' not found."}
            
        # Find candidate paths up to length limit to avoid path explosion
        all_candidate_paths = []
        for s in src_ids:
            for d in dst_ids:
                if s == d:
                    continue
                try:
                    # Look for paths using simple topological search capped at 6 nodes (5 segments)
                    paths = list(nx.all_simple_paths(G, s, d, max_depth=5))
                    all_candidate_paths.extend(paths)
                except Exception:
                    continue

        if not all_candidate_paths:
            # Fallback to shortest path by hops
            for s in src_ids:
                for d in dst_ids:
                    if s == d:
                        continue
                    try:
                        path = nx.shortest_path(G, s, d)
                        all_candidate_paths.append(path)
                    except nx.NetworkXNoPath:
                        continue
                        
        if not all_candidate_paths:
            return {"error": f"No routes found between '{source_query}' and '{dest_query}'."}
            
        # Evaluate candidate paths using schedule simulation
        evaluated_routes = []
        seen_route_signatures = set()
        
        for path in all_candidate_paths:
            try:
                segs, dur, cost, transfers = self._simulate_schedule(G, path, departure_time, constraints)
                
                # Check budget constraint
                if constraints and constraints.get("budget_limit") is not None:
                    if cost > constraints["budget_limit"]:
                        continue
                        
                # Check arrival deadline constraint
                if constraints and constraints.get("arrival_deadline") is not None:
                    deadline_mins = scheduler.time_to_mins(constraints["arrival_deadline"])
                    arr_mins = scheduler.time_to_mins(departure_time) + dur
                    if arr_mins > deadline_mins:
                        continue
                
                # Deduplicate based on segment names & times
                sig = tuple((s.mode, s.route_name) for s in segs)
                if sig in seen_route_signatures:
                    continue
                seen_route_signatures.add(sig)
                
                evaluated_routes.append({
                    "segments": segs,
                    "duration": dur,
                    "cost": cost,
                    "transfers": transfers
                })
            except Exception:
                continue
                
        if not evaluated_routes:
            return {"error": "No valid schedules found matching your constraints."}

        # Calculate scores for balanced option
        # Normalize duration, cost, and transfers to a [0, 1] range to score fairly
        durations = [r["duration"] for r in evaluated_routes]
        costs = [r["cost"] for r in evaluated_routes]
        transfers_list = [r["transfers"] for r in evaluated_routes]
        
        max_dur, min_dur = max(durations), min(durations)
        max_cost, min_cost = max(costs), min(costs)
        max_trans, min_trans = max(transfers_list), min(transfers_list)
        
        for r in evaluated_routes:
            dur_norm = (r["duration"] - min_dur) / (max_dur - min_dur) if max_dur > min_dur else 0.0
            cost_norm = (r["cost"] - min_cost) / (max_cost - min_cost) if max_cost > min_cost else 0.0
            trans_norm = (r["transfers"] - min_trans) / (max_trans - min_trans) if max_trans > min_trans else 0.0
            
            r["score"] = (
                self.weight_time * dur_norm + 
                self.weight_cost * cost_norm + 
                self.weight_transfers * trans_norm
            )

        # Select recommendations
        # 1. Fastest Route (minimizing duration)
        fastest_raw = min(evaluated_routes, key=lambda x: (x["duration"], x["cost"]))
        fastest = RouteOption(
            segments=fastest_raw["segments"],
            total_duration=fastest_raw["duration"],
            total_cost=fastest_raw["cost"],
            transfers=fastest_raw["transfers"],
            type="Fastest Route"
        )
        
        # 2. Cheapest Route (minimizing cost)
        cheapest_raw = min(evaluated_routes, key=lambda x: (x["cost"], x["duration"]))
        cheapest = RouteOption(
            segments=cheapest_raw["segments"],
            total_duration=cheapest_raw["duration"],
            total_cost=cheapest_raw["cost"],
            transfers=cheapest_raw["transfers"],
            type="Cheapest Route"
        )
        
        # 3. Fewest Transfers Route (minimizing transfers)
        fewest_transfers_raw = min(evaluated_routes, key=lambda x: (x["transfers"], x["duration"]))
        fewest_transfers = RouteOption(
            segments=fewest_transfers_raw["segments"],
            total_duration=fewest_transfers_raw["duration"],
            total_cost=fewest_transfers_raw["cost"],
            transfers=fewest_transfers_raw["transfers"],
            type="Fewest Transfers"
        )

        # 4. Balanced Route (minimizing score)
        balanced_raw = min(evaluated_routes, key=lambda x: x["score"])
        balanced = RouteOption(
            segments=balanced_raw["segments"],
            total_duration=balanced_raw["duration"],
            total_cost=balanced_raw["cost"],
            transfers=balanced_raw["transfers"],
            type="Balanced Option"
        )

        # Raw list of all valid evaluated routes for recommendation engine ranking
        self.all_evaluated_routes = evaluated_routes

        return {
            "fastest": fastest.to_dict(),
            "cheapest": cheapest.to_dict(),
            "fewest_transfers": fewest_transfers.to_dict(),
            "balanced": balanced.to_dict(),
            "raw_routes": evaluated_routes  # Expose raw routes list for Rec Engine
        }
