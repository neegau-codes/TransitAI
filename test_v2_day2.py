"""
test_v2_day2.py
Tests Day-2 V2 requirements: Multimodal Aluva->Thrissur, Manglish parsing, strict 4 labels with transfer count, empty route arrays for no-route, and missing provider fallbacks.
"""
import unittest
from models.transport import JourneyLeg
from nlp_parser import NLPParser
from route_engine import RouteEngine
from app import app

class TestV2Day2(unittest.TestCase):
    def setUp(self):
        self.route_engine = RouteEngine()
        self.nlp_parser = NLPParser()
        self.client = app.test_client()

    def test_multimodal_aluva_to_thrissur(self):
        """Verify routing engine traverses Aluva to Thrissur utilizing combinations of modes."""
        results = self.route_engine.find_routes("Aluva", "Thrissur", "08:00")
        self.assertNotIn("error", results)
        self.assertIn("raw_routes", results)
        
        # Verify multiple route alternatives exist
        self.assertGreater(len(results["raw_routes"]), 0)
        
        # Take the fastest and verify nodes
        fastest = results["fastest"]
        self.assertGreater(len(fastest["segments"]), 0)
        self.assertTrue(any("Aluva" in s["source_name"] for s in fastest["segments"]))
        self.assertTrue(any("Thrissur" in s["destination_name"] for s in fastest["segments"]))

    def test_manglish_intent_v2(self):
        """Validate complex Manglish maps to V2 intent seamlessly."""
        # e.g., 'aluva ninn thrissur pokanam train venam'
        query = "aluva ninn thrissur pokanam train venam"
        intent = self.nlp_parser.to_v2_intent(query=query)
        self.assertEqual(intent["origin"], "Aluva")
        self.assertEqual(intent["destination"], "Thrissur")
        self.assertIn("train", intent.get("preferred_modes", []))

    def test_strict_v2_four_labels_and_transfers(self):
        """Ensure recommendations strictly return BEST, FASTEST, CHEAPEST, LEAST WALKING with transfer counts."""
        res = self.client.post('/api/search', json={"query": "aluva ninn thrissur"})
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["status"], "OK")
        
        routes = data["routes"]
        self.assertGreater(len(routes), 0)
        
        valid_labels = {"BEST", "FASTEST", "CHEAPEST", "LEAST WALKING"}
        for r in routes:
            self.assertIn(r["label"], valid_labels, f"Label {r['label']} is not a valid V2 label")
            self.assertIsInstance(r["transfers"], int)

    def test_no_route_graceful_handling(self):
        """Assert unreachable locations return empty array instead of 400 error in V2 search."""
        res = self.client.post('/api/search', json={"query": "from Aluva to NewYorkCity"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["routes"], [])

    def test_missing_provider_fallback(self):
        """Assert empty/missing provider data safely defaults to ESTIMATED status/source."""
        leg = JourneyLeg(
            mode="bus",
            provider=None,
            source_name="Stop A",
            destination_name="Stop B",
            duration=15,
            cost=10.0
        )
        self.assertEqual(leg.source, "ESTIMATED")
        self.assertEqual(leg.status, "ESTIMATED")
        self.assertEqual(leg.provider, "ESTIMATED")

if __name__ == '__main__':
    unittest.main()
