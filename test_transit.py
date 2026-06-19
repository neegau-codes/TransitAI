import unittest
import sqlite3
import os
from database.db import DATABASE_PATH
from route_engine import RouteEngine
from nlp_parser import NLPParser

class TestTransitAI(unittest.TestCase):
    def setUp(self):
        self.route_engine = RouteEngine()
        self.nlp_parser = NLPParser()

    def test_database_exists(self):
        """Verify SQLite database file was generated and schema seeded."""
        self.assertTrue(os.path.exists(DATABASE_PATH), "Database file does not exist.")
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Verify locations table has data
        cursor.execute("SELECT count(*) FROM locations")
        loc_count = cursor.fetchone()[0]
        self.assertGreater(loc_count, 0, "No locations found in database.")
        
        # Verify routes table has data
        cursor.execute("SELECT count(*) FROM routes")
        routes_count = cursor.fetchone()[0]
        self.assertGreater(routes_count, 0, "No routes found in database.")

        # Verify schedules table has data
        cursor.execute("SELECT count(*) FROM schedules")
        schedules_count = cursor.fetchone()[0]
        self.assertGreater(schedules_count, 0, "No schedules found in database.")

        # Verify providers table has data
        cursor.execute("SELECT count(*) FROM providers")
        providers_count = cursor.fetchone()[0]
        self.assertGreater(providers_count, 0, "No providers found in database.")
        
        conn.close()

    def test_routing_engine(self):
        """Verify the routing engine successfully calculates multi-modal routes."""
        # Search from Aluva (Railway or Metro) to Kaloor (Metro or Bus)
        results = self.route_engine.find_routes("Aluva", "Kaloor", "08:30")
        
        # Validate results structure
        self.assertIn("fastest", results)
        self.assertIn("cheapest", results)
        self.assertIn("fewest_transfers", results)
        
        # Validate fastest route details
        fastest = results["fastest"]
        self.assertGreater(len(fastest["segments"]), 0)
        self.assertGreater(fastest["total_duration"], 0)
        self.assertGreater(fastest["total_cost"], 0)
        
        # Validate node connectivity
        first_seg = fastest["segments"][0]
        last_seg = fastest["segments"][-1]
        self.assertTrue("Aluva" in first_seg["source_name"])
        self.assertTrue("Kaloor" in last_seg["destination_name"])

    def test_kerala_routing_cases(self):
        """Verify routing works for Thrissur->Ernakulam, Kottayam->Kollam, Kozhikode->Kannur"""
        # Test Case 1: Thrissur to Ernakulam Town
        res1 = self.route_engine.find_routes("Thrissur", "Ernakulam", "17:00")
        self.assertNotIn("error", res1)
        self.assertGreater(len(res1["fastest"]["segments"]), 0)
        self.assertTrue(any("Thrissur" in s["source_name"] for s in res1["fastest"]["segments"]))
        self.assertTrue(any("Ernakulam" in s["destination_name"] for s in res1["fastest"]["segments"]))

        # Test Case 2: Kottayam to Kollam
        res2 = self.route_engine.find_routes("Kottayam", "Kollam", "19:00")
        self.assertNotIn("error", res2)
        self.assertGreater(len(res2["fastest"]["segments"]), 0)
        self.assertTrue(any("Kottayam" in s["source_name"] for s in res2["fastest"]["segments"]))
        self.assertTrue(any("Kollam" in s["destination_name"] for s in res2["fastest"]["segments"]))

        # Test Case 3: Kozhikode to Kannur
        res3 = self.route_engine.find_routes("Kozhikode", "Kannur", "05:00")
        self.assertNotIn("error", res3)
        self.assertGreater(len(res3["fastest"]["segments"]), 0)
        self.assertTrue(any("Kozhikode" in s["source_name"] for s in res3["fastest"]["segments"]))
        self.assertTrue(any("Kannur" in s["destination_name"] for s in res3["fastest"]["segments"]))

    def test_nlp_parser(self):
        """Verify the natural language query parser extracts constraints correctly."""
        # Test Case 1: Complex search query
        query = "I need to reach Kaloor from Aluva before 10:30 AM under ₹150"
        parsed = self.nlp_parser.parse_query(query)
        
        self.assertEqual(parsed["source"], "Aluva")
        self.assertEqual(parsed["destination"], "Kaloor")
        self.assertEqual(parsed["departure_time"], "10:30")
        self.assertEqual(parsed["budget"], 150.0)
        self.assertEqual(parsed["preference"], "cheapest")  # "under" triggers cheapest preference

        # Test Case 2: Simple direction and speed
        query_2 = "fastest way to Tripunithura from Edappally"
        parsed_2 = self.nlp_parser.parse_query(query_2)
        
        self.assertEqual(parsed_2["source"], "Edappally")
        self.assertEqual(parsed_2["destination"], "Tripunithura")
        self.assertEqual(parsed_2["preference"], "fastest")

    def test_flask_endpoints(self):
        """Verify the Flask REST API endpoints respond correctly."""
        from app import app
        client = app.test_client()
        
        # Test locations endpoint
        res = client.get('/api/locations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(len(data), 0)
        
        # Test search endpoint: Aluva to Kaloor
        res = client.post('/api/search', json={
            "source": "Aluva",
            "destination": "Kaloor",
            "departure_time": "08:30"
        })
        self.assertEqual(res.status_code, 200)
        routes = res.get_json()
        self.assertIn("fastest", routes)
        self.assertGreater(routes["fastest"]["total_duration"], 0)

if __name__ == "__main__":
    unittest.main()
