"""
recommendation_engine.py
Generates explanations and ranks route recommendations using a weighted scoring system.
"""

import re
from typing import List, Dict, Any, Tuple

# Configuration for recommendation weights
# All metrics are normalized (0 to 1) where 0 is best.
WEIGHTS = {
    "Best Overall": {
        "duration": 0.30,
        "cost": 0.20,
        "transfers": 0.15,
        "waiting_time": 0.15,
        "walking": 0.10,
        "comfort": 0.10,
        "reliability": 0.0,
        "mode_changes": 0.0
    },
    "Fastest": {
        "duration": 0.60,
        "transfers": 0.10,
        "waiting_time": 0.20,
        "walking": 0.10,
        "cost": 0.0,
        "comfort": 0.0,
        "reliability": 0.0,
        "mode_changes": 0.0
    },
    "Cheapest": {
        "cost": 0.60,
        "duration": 0.20,
        "waiting_time": 0.10,
        "transfers": 0.10,
        "walking": 0.0,
        "comfort": 0.0,
        "reliability": 0.0,
        "mode_changes": 0.0
    },
    "Least Walking": {
        "walking": 0.70,
        "transfers": 0.15,
        "duration": 0.15,
        "cost": 0.0,
        "waiting_time": 0.0,
        "comfort": 0.0,
        "reliability": 0.0,
        "mode_changes": 0.0
    },
    "Least Waiting": {
        "waiting_time": 0.70,
        "transfers": 0.15,
        "duration": 0.15,
        "cost": 0.0,
        "walking": 0.0,
        "comfort": 0.0,
        "reliability": 0.0,
        "mode_changes": 0.0
    },
    "Most Comfortable": {
        "transfers": 0.35,
        "walking": 0.35,
        "waiting_time": 0.20,
        "mode_changes": 0.10,
        "cost": 0.0,
        "duration": 0.0,
        "comfort": 0.0,
        "reliability": 0.0
    },
    "Balanced Route": {
        "duration": 0.25,
        "cost": 0.25,
        "transfers": 0.15,
        "waiting_time": 0.15,
        "walking": 0.10,
        "reliability": 0.10,
        "comfort": 0.0,
        "mode_changes": 0.0
    }
}

class RecommendationEngine:
    def __init__(self):
        pass
        
    def _parse_time(self, t_str: str) -> int:
        """Helper to parse HH:MM into minutes."""
        try:
            h, m = map(int, t_str.split(':'))
            return h * 60 + m
        except (ValueError, AttributeError):
            return 0
            
    def _extract_metrics(self, raw_route: Dict[str, Any]) -> Dict[str, float]:
        """
        Extracts raw metrics for scoring.
        Calculates waiting time, walking distance (via duration), and mode changes.
        """
        duration = float(raw_route.get("duration", 0))
        cost = float(raw_route.get("cost", 0))
        transfers = float(raw_route.get("transfers", 0))
        
        segments = raw_route.get("segments", [])
        
        walking_time = 0.0
        waiting_time = 0.0
        mode_changes = 0.0
        
        last_mode = None
        
        for seg in segments:
            mode = getattr(seg, 'mode', '')
            seg_duration = getattr(seg, 'duration', 0)
            route_name = getattr(seg, 'route_name', '')
            
            if mode == 'walk':
                walking_time += seg_duration
                
            if last_mode is not None and mode != last_mode:
                mode_changes += 1
            last_mode = mode
            
            # Extract waiting time if embedded in route_name
            # e.g., "Bus A (Dep: 08:10, Arr: 08:50)"
            m = re.search(r'Dep:\s*(\d{2}:\d{2}),\s*Arr:\s*(\d{2}:\d{2})', route_name)
            if m:
                dep_mins = self._parse_time(m.group(1))
                arr_mins = self._parse_time(m.group(2))
                
                # Handle midnight crossing
                if arr_mins < dep_mins:
                    arr_mins += 24 * 60
                    
                actual_ride_time = arr_mins - dep_mins
                wait = seg_duration - actual_ride_time
                if wait > 0:
                    waiting_time += wait
                    
        # Derive Reliability and Comfort penalties (lower is better)
        reliability = transfers * 10.0 + waiting_time * 0.5
        comfort = walking_time * 1.0 + transfers * 15.0
        
        return {
            "duration": duration,
            "cost": cost,
            "transfers": transfers,
            "walking": walking_time,
            "waiting_time": waiting_time,
            "mode_changes": mode_changes,
            "reliability": reliability,
            "comfort": comfort
        }

    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalizes a value between 0 and 1. (0 is best/lowest)"""
        if max_val <= min_val:
            return 0.0
        return (value - min_val) / (max_val - min_val)

    def _generate_explanation(self, category: str, transfers: int) -> str:
        """Returns a human-readable explanation for the category."""
        if category == "Cheapest":
            return "Lowest fare among available routes."
        elif category == "Fastest":
            return f"Fastest arrival with {int(transfers)} transfer(s)."
        elif category == "Least Walking":
            return "Minimal walking distance."
        elif category == "Least Waiting":
            return "Minimal waiting time."
        elif category == "Most Comfortable":
            return f"Most comfortable with {int(transfers)} transfer(s)."
        elif category == "Best Overall":
            return "Balanced travel time and cost."
        elif category == "Balanced Route":
            return "Balanced travel time and cost with high reliability."
        return f"Recommended for {category}."

    def generate_recommendations(self, routes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyzes raw routes and constructs weighted recommendations.
        Maintains backwards compatibility with frontend response structures.
        """
        recommendations = []
        raw_routes = routes.get("raw_routes", [])
        
        if not raw_routes:
            return recommendations
            
        # 1. Extract metrics for all routes
        route_metrics = []
        for idx, r in enumerate(raw_routes):
            metrics = self._extract_metrics(r)
            route_metrics.append((idx, r, metrics))
            
        # 2. Find min/max for normalization
        metric_keys = ["duration", "cost", "transfers", "walking", "waiting_time", 
                       "mode_changes", "reliability", "comfort"]
                       
        min_max = {}
        for key in metric_keys:
            vals = [m[key] for _, _, m in route_metrics]
            min_max[key] = (min(vals), max(vals))
            
        # 3. Score each route for each category
        scored_routes = {cat: [] for cat in WEIGHTS.keys()}
        
        for idx, r, metrics in route_metrics:
            norm = {}
            for key in metric_keys:
                norm[key] = self._normalize(metrics[key], min_max[key][0], min_max[key][1])
                
            for cat, weights in WEIGHTS.items():
                score = sum(norm[k] * w for k, w in weights.items())
                scored_routes[cat].append({
                    "id": idx,
                    "score": score,
                    "route": r,
                    "metrics": metrics
                })
                
        # 4. Tie-breaking and deterministic sorting
        for cat in scored_routes:
            scored_routes[cat].sort(key=lambda x: (
                x["score"],
                x["metrics"]["transfers"],
                x["metrics"]["waiting_time"],
                x["metrics"]["cost"],
                x["metrics"]["duration"],
                x["id"]
            ))
            
        # 5. Select unique routes for categories whenever possible
        assigned_route_ids = set()
        
        # Category order priority
        categories_to_assign = ["Best Overall", "Fastest", "Cheapest", "Most Comfortable", 
                                "Least Walking", "Least Waiting", "Balanced Route"]
                                
        for cat in categories_to_assign:
            if cat not in scored_routes:
                continue
                
            candidates = scored_routes[cat]
            best_choice = candidates[0]
            
            # Try to find a unique route that hasn't been assigned yet
            # Only pick it if its score isn't terrible compared to the absolute best
            best_score = best_choice["score"]
            for cand in candidates:
                if cand["id"] not in assigned_route_ids:
                    # Allow up to 10% worse score for uniqueness
                    if cand["score"] <= best_score + 0.10:
                        best_choice = cand
                    break
                    
            assigned_route_ids.add(best_choice["id"])
            
            # Convert segments to dicts if they are objects for the 'route' payload
            formatted_segments = []
            for s in best_choice["route"]["segments"]:
                if hasattr(s, "to_dict"):
                    formatted_segments.append(s.to_dict())
                else:
                    formatted_segments.append(s)
            
            route_payload = {
                "segments": formatted_segments,
                "total_duration": best_choice["route"]["duration"],
                "total_cost": best_choice["route"]["cost"],
                "transfers": best_choice["route"]["transfers"],
                "type": cat
            }
            
            explanation = self._generate_explanation(cat, best_choice["metrics"]["transfers"])
            
            v2_label = {
                "Best Overall": "BEST",
                "Fastest": "FASTEST",
                "Cheapest": "CHEAPEST",
                "Least Walking": "LEAST WALKING"
            }.get(cat, cat)

            recommendations.append({
                "category": cat,
                "label": v2_label,
                "explanation": explanation,
                "tradeoff": "None",  # Maintained for backwards compatibility
                "total_time": best_choice["route"]["duration"],
                "total_cost": best_choice["route"]["cost"],
                "transfers": best_choice["route"]["transfers"],
                "route": route_payload
            })
            
        return recommendations

    def generate_v2_recommendations(self, routes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates recommendations adhering strictly to the V2 four public labels:
        BEST, FASTEST, CHEAPEST, LEAST WALKING.
        """
        label_map = {
            "Best Overall": "BEST",
            "Fastest": "FASTEST",
            "Cheapest": "CHEAPEST",
            "Least Walking": "LEAST WALKING"
        }
        recs = self.generate_recommendations(routes)
        v2_routes = []
        seen_labels = set()

        for r in recs:
            v2_lbl = label_map.get(r["category"])
            if v2_lbl and v2_lbl not in seen_labels:
                seen_labels.add(v2_lbl)
                route_payload = r.get("route", {})
                raw_segments = route_payload.get("segments", [])

                legs = []
                walking_mins = 0
                coords = []
                for seg in raw_segments:
                    if hasattr(seg, "to_dict"):
                        seg_dict = seg.to_dict()
                    elif isinstance(seg, dict):
                        seg_dict = seg
                    else:
                        seg_dict = getattr(seg, "__dict__", {})

                    mode = seg_dict.get("mode", "walk")
                    if mode == "walk":
                        walking_mins += seg_dict.get("duration", 0)

                    # Ensure leg format matches V2 schema
                    dept = seg_dict.get("departure")
                    arr = seg_dict.get("arrival")
                    if not dept or not arr:
                        import re
                        m = re.search(r'Dep:\s*(\d{2}:\d{2}),\s*Arr:\s*(\d{2}:\d{2})', seg_dict.get("route_name", ""))
                        if m:
                            dept = dept or m.group(1)
                            arr = arr or m.group(2)

                    legs.append({
                        "mode": mode.upper(),
                        "from": seg_dict.get("source_name") or seg_dict.get("from"),
                        "to": seg_dict.get("destination_name") or seg_dict.get("to"),
                        "departure": dept or None,
                        "arrival": arr or None,
                        "duration_minutes": seg_dict.get("duration", 0),
                        "fare": {
                            "amount": seg_dict.get("cost", 0.0),
                            "currency": "INR",
                            "status": seg_dict.get("status", "SCHEDULED")
                        },
                        "status": seg_dict.get("status", "ESTIMATED" if mode == "walk" else "SCHEDULED"),
                        "source": seg_dict.get("source", "ESTIMATED" if mode == "walk" else "KMRL")
                    })

                v2_routes.append({
                    "route_id": f"ta_{len(v2_routes)+1:03d}",
                    "label": v2_lbl,
                    "duration_minutes": r["total_time"],
                    "fare": {
                        "amount": r["total_cost"],
                        "currency": "INR",
                        "status": "SCHEDULED"
                    },
                    "transfers": r["transfers"],
                    "walking_minutes": walking_mins,
                    "status": "SCHEDULED",
                    "legs": legs
                })

        return v2_routes
