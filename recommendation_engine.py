"""
recommendation_engine.py
Generates explanations and ranks route recommendations.
"""

from typing import List, Dict, Any

class RecommendationEngine:
    def __init__(self):
        pass

    def generate_recommendations(self, routes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyzes the available routes (fastest, cheapest, fewest_transfers, balanced)
        and constructs structured recommendations for Best Overall, Budget Friendly,
        and Most Comfortable.
        
        Args:
            routes: A dictionary mapping route keys to their detailed route dictionaries.
            
        Returns:
            A list of dictionary recommendations with category, explanation, tradeoffs,
            and route parameters.
        """
        recommendations = []
        
        # 1. Budget Friendly (corresponds to Cheapest Route)
        cheapest = routes.get("cheapest")
        if cheapest:
            fastest = routes.get("fastest")
            explanation = "Selected as Budget Friendly because it minimizes your out-of-pocket travel expenses."
            
            if fastest and fastest["total_duration"] < cheapest["total_duration"]:
                time_diff = cheapest["total_duration"] - fastest["total_duration"]
                cost_saved = fastest["total_cost"] - cheapest["total_cost"]
                tradeoff = f"Saves ₹{cost_saved:.2f} but takes an additional {time_diff} minutes compared to the fastest option."
            else:
                tradeoff = "This is also the fastest route available, offering the absolute best value without delay!"
                
            recommendations.append({
                "category": "Budget Friendly",
                "explanation": explanation,
                "tradeoff": tradeoff,
                "total_time": cheapest["total_duration"],
                "total_cost": cheapest["total_cost"],
                "transfers": cheapest["transfers"],
                "route": cheapest
            })
            
        # 2. Most Comfortable (corresponds to Fewest Transfers Route)
        fewest_trans = routes.get("fewest_transfers")
        if fewest_trans:
            fastest = routes.get("fastest")
            trans_count = fewest_trans["transfers"]
            explanation = "Selected as Most Comfortable because it provides the smoothest transit with the fewest vehicle switches."
            
            tradeoff_parts = []
            if trans_count == 0:
                tradeoff_parts.append("Provides a direct, zero-transfer path.")
            else:
                tradeoff_parts.append(f"Requires only {trans_count} transfer(s).")
                
            if fastest and fastest["total_duration"] < fewest_trans["total_duration"]:
                time_diff = fewest_trans["total_duration"] - fastest["total_duration"]
                tradeoff_parts.append(f"Adds {time_diff} minutes of travel time compared to the fastest option to avoid switching vehicles.")
            else:
                tradeoff_parts.append("No travel speed compromise is needed for this comfortable option.")
                
            recommendations.append({
                "category": "Most Comfortable",
                "explanation": explanation,
                "tradeoff": " ".join(tradeoff_parts),
                "total_time": fewest_trans["total_duration"],
                "total_cost": fewest_trans["total_cost"],
                "transfers": fewest_trans["transfers"],
                "route": fewest_trans
            })
            
        # 3. Best Overall (corresponds to Balanced Route)
        balanced = routes.get("balanced")
        if balanced:
            fastest = routes.get("fastest")
            cheapest = routes.get("cheapest")
            explanation = "Selected as Best Overall because it strikes the perfect balance between speed, affordability, and convenience."
            
            tradeoff_parts = []
            if fastest and fastest["total_duration"] < balanced["total_duration"]:
                time_diff = balanced["total_duration"] - fastest["total_duration"]
                tradeoff_parts.append(f"Takes {time_diff} minutes longer than the fastest route")
            if cheapest and cheapest["total_cost"] < balanced["total_cost"]:
                cost_diff = balanced["total_cost"] - cheapest["total_cost"]
                tradeoff_parts.append(f"and costs ₹{cost_diff:.2f} more than the cheapest route")
                
            if tradeoff_parts:
                tradeoff = " ".join(tradeoff_parts) + ", but saves money/transfers overall."
            else:
                tradeoff = "No significant tradeoffs: it offers optimal performance across all travel factors."
                
            recommendations.append({
                "category": "Best Overall",
                "explanation": explanation,
                "tradeoff": tradeoff,
                "total_time": balanced["total_duration"],
                "total_cost": balanced["total_cost"],
                "transfers": balanced["transfers"],
                "route": balanced
            })
            
        return recommendations
