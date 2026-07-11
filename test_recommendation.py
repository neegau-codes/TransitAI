"""
test_recommendation.py
Tests the new weighted recommendation engine in TransitAI.
"""
import unittest
from recommendation_engine import RecommendationEngine

class TestRecommendationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RecommendationEngine()
        
        # Create some dummy raw routes
        self.raw_routes = [
            {
                "segments": [
                    type("Segment", (), {"mode": "walk", "duration": 10, "cost": 0, "route_name": "Walk", "to_dict": lambda self: {}})(),
                    type("Segment", (), {"mode": "bus", "duration": 50, "cost": 20, "route_name": "Bus A (Dep: 08:10, Arr: 08:50)", "to_dict": lambda self: {}})(),
                    type("Segment", (), {"mode": "walk", "duration": 5, "cost": 0, "route_name": "Walk", "to_dict": lambda self: {}})()
                ],
                "duration": 65,
                "cost": 20,
                "transfers": 0
            },
            {
                "segments": [
                    type("Segment", (), {"mode": "metro", "duration": 25, "cost": 60, "route_name": "Metro (Dep: 08:05, Arr: 08:25)", "to_dict": lambda self: {}})(),
                    type("Segment", (), {"mode": "walk", "duration": 2, "cost": 0, "route_name": "Walk", "to_dict": lambda self: {}})()
                ],
                "duration": 27,
                "cost": 60,
                "transfers": 0
            },
            {
                "segments": [
                    type("Segment", (), {"mode": "walk", "duration": 2, "cost": 0, "route_name": "Walk", "to_dict": lambda self: {}})(),
                    type("Segment", (), {"mode": "train", "duration": 30, "cost": 30, "route_name": "Train (Dep: 08:10, Arr: 08:35)", "to_dict": lambda self: {}})(),
                    type("Segment", (), {"mode": "metro", "duration": 15, "cost": 20, "route_name": "Metro (Dep: 08:45, Arr: 08:55)", "to_dict": lambda self: {}})()
                ],
                "duration": 55, # wait for train=8, ride train=25, wait for metro=10, ride metro=10. Total 53+2=55
                "cost": 50,
                "transfers": 1
            }
        ]
        
    def test_extract_metrics(self):
        metrics = self.engine._extract_metrics(self.raw_routes[0])
        self.assertEqual(metrics["duration"], 65)
        self.assertEqual(metrics["cost"], 20)
        self.assertEqual(metrics["transfers"], 0)
        self.assertEqual(metrics["walking"], 15)
        self.assertEqual(metrics["waiting_time"], 10) # 50 duration - 40 ride = 10 wait
        self.assertEqual(metrics["mode_changes"], 2) # walk->bus->walk
        
    def test_generate_recommendations(self):
        # We need to simulate the routes payload coming from route_engine.py
        # Provide raw_routes
        routes_payload = {
            "raw_routes": self.raw_routes,
            "fastest": {"type": "Fastest Route"},
            "cheapest": {"type": "Cheapest Route"}
        }
        
        recs = self.engine.generate_recommendations(routes_payload)
        
        categories = [r["category"] for r in recs]
        self.assertIn("Best Overall", categories)
        self.assertIn("Fastest", categories)
        self.assertIn("Cheapest", categories)
        self.assertIn("Least Walking", categories)
        
        # Test deterministic sorting/tie-breaking by generating again
        recs2 = self.engine.generate_recommendations(routes_payload)
        self.assertEqual([r["route"] for r in recs], [r["route"] for r in recs2])
        
    def test_missing_raw_routes_fallback(self):
        # Without raw_routes, it should gracefully return empty or fallback
        recs = self.engine.generate_recommendations({"fastest": {"total_duration": 10, "total_cost": 20, "transfers": 0}})
        self.assertEqual(len(recs), 0)

if __name__ == '__main__':
    unittest.main()
