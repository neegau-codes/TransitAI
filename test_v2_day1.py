"""
test_v2_day1.py
Tests Day-1 V2 model and API contract updates for Member 2.
"""
import unittest
import datetime
from models.transport import JourneyLeg, Journey, Segment, RouteOption, VALID_STATUSES, VALID_SOURCES
from ai_parser import AIQueryParser
from nlp_parser import NLPParser
from recommendation_engine import RecommendationEngine
from app import app

class TestV2Day1(unittest.TestCase):
    def test_journey_leg_status_source(self):
        """Verify JourneyLeg stores status and source values correctly."""
        leg_metro = JourneyLeg(
            mode="metro",
            provider="KMRL",
            source_name="Aluva",
            destination_name="Ernakulam South",
            duration=33,
            cost=40.0,
            status="LIVE",
            source="KMRL"
        )
        self.assertEqual(leg_metro.status, "LIVE")
        self.assertEqual(leg_metro.source, "KMRL")
        
        v2_dict = leg_metro.to_v2_dict()
        self.assertEqual(v2_dict["mode"], "METRO")
        self.assertEqual(v2_dict["from"], "Aluva")
        self.assertEqual(v2_dict["to"], "Ernakulam South")
        self.assertEqual(v2_dict["status"], "LIVE")
        self.assertEqual(v2_dict["source"], "KMRL")
        self.assertEqual(v2_dict["fare"]["amount"], 40.0)

        # Test walking leg defaults
        leg_walk = JourneyLeg(
            mode="walk",
            provider="ESTIMATED",
            source_name="Stop A",
            destination_name="Stop B",
            duration=5,
            cost=0.0
        )
        self.assertEqual(leg_walk.status, "ESTIMATED")
        self.assertEqual(leg_walk.source, "ESTIMATED")

    def test_journey_v2_route_metadata(self):
        """Verify Journey/RouteOption exports V2 route structure."""
        leg = JourneyLeg(
            mode="metro",
            provider="KMRL",
            source_name="Aluva",
            destination_name="Ernakulam South",
            duration=33,
            cost=40.0,
            status="SCHEDULED",
            source="KMRL"
        )
        journey = Journey(
            legs=[leg],
            total_duration=33,
            total_cost=40.0,
            transfers=0,
            type="BEST",
            label="BEST",
            route_id="ta_001"
        )
        v2_route = journey.to_v2_dict()
        self.assertEqual(v2_route["route_id"], "ta_001")
        self.assertEqual(v2_route["label"], "BEST")
        self.assertEqual(v2_route["duration_minutes"], 33)
        self.assertEqual(v2_route["fare"]["amount"], 40.0)
        self.assertEqual(v2_route["fare"]["status"], "SCHEDULED")
        self.assertEqual(len(v2_route["legs"]), 1)

    def test_nlp_to_v2_intent(self):
        """Verify NLP parser exposes the V2 intent contract correctly."""
        parser = NLPParser()
        intent = parser.to_v2_intent(query="naale 5 manikku munpe aluva ninn thrissur ethande")
        self.assertEqual(intent["origin"], "Aluva")
        self.assertEqual(intent["destination"], "Thrissur")
        self.assertIsNotNone(intent["date"])
        self.assertIn("arrive_before", intent)
        self.assertIn("depart_after", intent)
        self.assertIn("budget", intent)
        self.assertIn("preferred_modes", intent)

    def test_recommendation_v2_four_labels(self):
        """Verify recommendation engine produces V2 four-label recommendations."""
        rec = RecommendationEngine()
        raw_routes = [
            {
                "segments": [
                    Segment(mode="metro", source_name="Aluva", destination_name="Kaloor", duration=25, cost=30.0, provider="KMRL")
                ],
                "duration": 25,
                "cost": 30.0,
                "transfers": 0
            }
        ]
        routes_payload = {"raw_routes": raw_routes}
        v2_recs = rec.generate_v2_recommendations(routes_payload)
        labels = [r["label"] for r in v2_recs]
        self.assertTrue(any(l in ["BEST", "FASTEST", "CHEAPEST", "LEAST WALKING"] for l in labels))

    def test_v2_flask_api_endpoints(self):
        """Verify POST /api/search V2 and GET /api/routes endpoints work."""
        client = app.test_client()
        
        # Test V2 POST /api/search with query
        res = client.post('/api/search', json={
            "query": "naale 5 manikku munpe aluva ninn thrissur ethande"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "OK")
        self.assertIn("intent", data)
        self.assertEqual(data["intent"]["origin"], "Aluva")
        self.assertEqual(data["intent"]["destination"], "Thrissur")
        self.assertIn("routes", data)

        # Test GET /api/routes
        res_get = client.get('/api/routes?from=Aluva&to=Thrissur&date=2026-09-20')
        self.assertEqual(res_get.status_code, 200)
        get_data = res_get.get_json()
        self.assertEqual(get_data["request"]["origin"], "Aluva")
        self.assertEqual(get_data["request"]["destination"], "Thrissur")
        self.assertIn("routes", get_data)
        self.assertIn("generated_at", get_data)

if __name__ == '__main__':
    unittest.main()
