"""
test_parser.py
Comprehensive parser tests covering all 10 feature areas:
  1. Manglish support
  2. Partial location names
  3. Missing source
  4. Missing destination
  5. Date understanding
  6. Time understanding
  7. Budget extraction
  8. Transport preferences
  9. Typo handling
  10. Backward-compatibility with existing tests
"""

import datetime
import unittest

from ai_parser import AIQueryParser, _edit_distance, _best_fuzzy_match, _parse_date_phrase


class TestFuzzyHelpers(unittest.TestCase):
    """Unit tests for the standalone fuzzy-match helpers."""

    def test_edit_distance_identical(self):
        self.assertEqual(_edit_distance("aluva", "aluva"), 0)

    def test_edit_distance_single_typo(self):
        self.assertEqual(_edit_distance("kochin", "kochi"), 1)

    def test_edit_distance_two_typos(self):
        self.assertLessEqual(_edit_distance("thrisur", "thrissur"), 2)

    def test_best_fuzzy_exact(self):
        candidates = ["Aluva", "Kaloor", "Thrissur"]
        self.assertEqual(_best_fuzzy_match("aluva", candidates), "Aluva")

    def test_best_fuzzy_prefix(self):
        candidates = ["Aluva", "Kaloor", "Thrissur"]
        self.assertEqual(_best_fuzzy_match("kal", candidates), "Kaloor")

    def test_best_fuzzy_typo(self):
        candidates = ["Thrissur", "Kochi", "Ernakulam"]
        result = _best_fuzzy_match("thrisur", candidates)
        self.assertEqual(result, "Thrissur")

    def test_best_fuzzy_no_match(self):
        candidates = ["Aluva", "Kaloor"]
        # "zxqwerty" is way too far from any candidate
        result = _best_fuzzy_match("zxqwerty", candidates, max_distance=2)
        self.assertIsNone(result)


class TestDateParsing(unittest.TestCase):
    """Tests for relative date phrase understanding."""

    def setUp(self):
        self.today = datetime.date.today()

    def test_today(self):
        result = _parse_date_phrase("I want to travel today")
        self.assertEqual(result, self.today)

    def test_tomorrow(self):
        result = _parse_date_phrase("Book me a trip tomorrow")
        self.assertEqual(result, self.today + datetime.timedelta(days=1))

    def test_day_after_tomorrow(self):
        result = _parse_date_phrase("Travel day after tomorrow")
        self.assertEqual(result, self.today + datetime.timedelta(days=2))

    def test_this_weekend(self):
        result = _parse_date_phrase("This weekend trip")
        self.assertIsNotNone(result)
        # Must be a Saturday (weekday == 5)
        self.assertEqual(result.weekday(), 5)

    def test_next_monday(self):
        result = _parse_date_phrase("Next Monday morning")
        self.assertIsNotNone(result)
        self.assertEqual(result.weekday(), 0)
        # Must be in the future
        self.assertGreater(result, self.today)

    def test_friday_evening(self):
        result = _parse_date_phrase("Friday evening train")
        self.assertIsNotNone(result)
        self.assertEqual(result.weekday(), 4)

    def test_no_date_returns_none(self):
        result = _parse_date_phrase("Just a regular query with no date")
        self.assertIsNone(result)


class TestParserManglish(unittest.TestCase):
    """Tests for Manglish / Kerala shorthand queries."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_tvm_expansion(self):
        result = self.parser.parse_query("From Aluva to tvm")
        self.assertEqual(result["source"], "Aluva")
        self.assertEqual(result["destination"], "Thiruvananthapuram")

    def test_ekm_expansion(self):
        result = self.parser.parse_query("ekm to tvm")
        self.assertEqual(result["source"], "Ernakulam")
        self.assertEqual(result["destination"], "Thiruvananthapuram")

    def test_clt_expansion(self):
        result = self.parser.parse_query("Kannur to clt")
        self.assertEqual(result["source"], "Kannur")
        self.assertEqual(result["destination"], "Kozhikode")

    def test_tsr_expansion(self):
        result = self.parser.parse_query("From Ernakulam to tsr")
        self.assertEqual(result["source"], "Ernakulam")
        self.assertEqual(result["destination"], "Thrissur")

    def test_aluva_ninn_kaloor(self):
        """'aluva ninn kaloor' → from Aluva to Kaloor"""
        result = self.parser.parse_query("aluva ninn kaloor")
        self.assertEqual(result["source"], "Aluva")
        self.assertEqual(result["destination"], "Kaloor")

    def test_thrissur_pokanam(self):
        """'thrissur pokanam' → destination Thrissur"""
        result = self.parser.parse_query("ernakulam ninn thrissur pokanam")
        self.assertEqual(result["destination"], "Thrissur")

    def test_train_venam(self):
        """'train venam' → prefers train"""
        result = self.parser.parse_query("aluva to kaloor train venam")
        prefs = result.get("additional_constraints", {}).get("preferred_modes", [])
        self.assertIn("train", prefs)

    def test_bus_mathi(self):
        """'bus mathi' → only bus (metro/train excluded)"""
        result = self.parser.parse_query("aluva to kaloor bus mathi")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertIn("metro", excluded)

    def test_metro_mathi(self):
        """'metro mathi' → only metro"""
        result = self.parser.parse_query("aluva to kaloor metro mathi")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertIn("bus", excluded)

    def test_walk_venda(self):
        """'walk venda' → avoid walking"""
        result = self.parser.parse_query("aluva to kaloor walk venda")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertIn("walk", excluded)

    def test_kochi_metro_query(self):
        result = self.parser.parse_query("kochi metro to thrissur")
        self.assertIsNotNone(result["source"])
        self.assertEqual(result["destination"], "Thrissur")

    def test_ernakulam_railway_station(self):
        result = self.parser.parse_query("from ernakulam railway station to thrissur")
        self.assertEqual(result["source"], "Ernakulam")
        self.assertEqual(result["destination"], "Thrissur")


class TestPartialLocationMatching(unittest.TestCase):
    """Tests for prefix and fuzzy partial location name matching."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_alu_matches_aluva(self):
        result = self.parser.parse_query("from alu to kaloor")
        self.assertEqual(result["source"], "Aluva")

    def test_kalo_matches_kaloor(self):
        result = self.parser.parse_query("from aluva to kalo")
        self.assertEqual(result["destination"], "Kaloor")

    def test_erna_matches_ernakulam(self):
        result = self.parser.parse_query("from erna to thrissur")
        self.assertEqual(result["source"], "Ernakulam")

    def test_koch_matches_kochi(self):
        result = self.parser.parse_query("from koch to thrissur")
        self.assertIsNotNone(result["source"])

    def test_tripu_matches_tripunithura(self):
        result = self.parser.parse_query("from edappally to tripu")
        self.assertEqual(result["destination"], "Tripunithura")

    def test_thiru_matches_thiruvananthapuram(self):
        result = self.parser.parse_query("from kollam to thiru")
        self.assertIn("Thiruvananthapuram", result["destination"])


class TestTypoHandling(unittest.TestCase):
    """Tests that common misspellings are corrected before parsing."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_thrisur_corrected(self):
        result = self.parser.parse_query("from ernakulam to thrisur")
        self.assertEqual(result["destination"], "Thrissur")

    def test_thrissure_corrected(self):
        result = self.parser.parse_query("from ernakulam to thrissure")
        self.assertEqual(result["destination"], "Thrissur")

    def test_kochin_corrected(self):
        result = self.parser.parse_query("from kochin to thrissur")
        self.assertEqual(result["source"], "Kochi")

    def test_trivandrom_corrected(self):
        result = self.parser.parse_query("trivandrom to ernakulam")
        self.assertEqual(result["source"], "Thiruvananthapuram")

    def test_kalor_corrected(self):
        result = self.parser.parse_query("aluva to kalor")
        self.assertEqual(result["destination"], "Kaloor")

    def test_aluvaa_corrected(self):
        result = self.parser.parse_query("aluvaa to kaloor")
        self.assertEqual(result["source"], "Aluva")


class TestMissingSource(unittest.TestCase):
    """Tests that queries missing a source return structured incomplete hints."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_missing_source_has_flag(self):
        result = self.parser.parse_query("Need to reach Thrissur")
        self.assertTrue(result.get("incomplete"))
        self.assertIn("source", result.get("missing", []))

    def test_missing_source_suggestion(self):
        result = self.parser.parse_query("Need to reach Thrissur")
        self.assertIn("suggestion", result)
        self.assertTrue(len(result["suggestion"]) > 0)

    def test_missing_source_destination_still_set(self):
        result = self.parser.parse_query("Need to reach Thrissur")
        self.assertEqual(result["destination"], "Thrissur")

    def test_missing_source_does_not_crash(self):
        """Parser must never raise an exception on a partial query."""
        try:
            self.parser.parse_query("Cheapest route to Kaloor")
        except Exception as e:
            self.fail(f"Parser raised an exception: {e}")


class TestMissingDestination(unittest.TestCase):
    """Tests that queries missing a destination return structured incomplete hints."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_missing_destination_flag(self):
        result = self.parser.parse_query("From Aluva")
        self.assertTrue(result.get("incomplete"))
        self.assertIn("destination", result.get("missing", []))

    def test_missing_destination_suggestion(self):
        result = self.parser.parse_query("From Aluva")
        self.assertIn("suggestion", result)
        self.assertGreater(len(result["suggestion"]), 0)

    def test_missing_destination_source_still_set(self):
        result = self.parser.parse_query("From Aluva")
        self.assertEqual(result["source"], "Aluva")

    def test_missing_both_locations(self):
        result = self.parser.parse_query("Need cheapest route")
        self.assertTrue(result.get("incomplete"))
        missing = result.get("missing", [])
        self.assertIn("source", missing)
        self.assertIn("destination", missing)
        self.assertIn("Tell me", result.get("suggestion", ""))


class TestTimeUnderstanding(unittest.TestCase):
    """Tests for various natural time expressions."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_before_6pm(self):
        result = self.parser.parse_query("Reach Thrissur from Ernakulam before 6 pm")
        self.assertEqual(result["arrival_deadline"], "18:00")

    def test_before_6_no_am_pm(self):
        result = self.parser.parse_query("Reach Kaloor from Aluva before 6")
        # Ambiguous '6' in arrival context should become 18:00
        self.assertIn(result["arrival_deadline"], ["06:00", "18:00"])

    def test_after_4(self):
        result = self.parser.parse_query("Leave Aluva after 4 PM to Kaloor")
        self.assertEqual(result["departure_time"], "16:00")

    def test_around_8(self):
        """'around 8' should set departure_time."""
        result = self.parser.parse_query("Travel around 8 from Aluva to Kaloor")
        self.assertEqual(result["departure_time"], "08:00")

    def test_between_5_and_7(self):
        result = self.parser.parse_query("I want to travel between 5 and 7 from Aluva to Kaloor")
        self.assertEqual(result["departure_time"], "05:00")
        self.assertEqual(result["arrival_deadline"], "07:00")

    def test_morning(self):
        result = self.parser.parse_query("Morning trip from Aluva to Kaloor")
        self.assertEqual(result["departure_time"], "06:00")

    def test_evening(self):
        result = self.parser.parse_query("Evening journey from Aluva to Kaloor")
        self.assertEqual(result["departure_time"], "17:00")

    def test_asap(self):
        result = self.parser.parse_query("ASAP from Aluva to Kaloor")
        now_str = datetime.datetime.now().strftime("%H:%M")
        # Should be within 1 minute of now
        self.assertIsNotNone(result["departure_time"])

    def test_full_time_with_minutes(self):
        result = self.parser.parse_query("I need to reach Kaloor from Aluva before 10:30 AM under ₹150")
        self.assertEqual(result["departure_time"], "10:30")
        self.assertEqual(result["arrival_deadline"], "10:30")


class TestBudgetExtraction(unittest.TestCase):
    """Tests for budget constraint extraction."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_under_rupee_symbol(self):
        result = self.parser.parse_query("From Aluva to Kaloor under ₹300")
        self.assertEqual(result["budget_limit"], 300.0)
        self.assertEqual(result["budget"], 300.0)

    def test_below_numeric(self):
        result = self.parser.parse_query("Aluva to Kaloor below 200")
        self.assertEqual(result["budget_limit"], 200.0)

    def test_less_than(self):
        result = self.parser.parse_query("From Ernakulam to Thrissur less than 500")
        self.assertEqual(result["budget_limit"], 500.0)

    def test_maximum(self):
        result = self.parser.parse_query("From Aluva to Thrissur maximum 450")
        self.assertEqual(result["budget_limit"], 450.0)

    def test_cheap_keyword_sets_preference(self):
        result = self.parser.parse_query("cheap route from Aluva to Kaloor")
        self.assertEqual(result["optimization_preference"], "cheapest")
        self.assertEqual(result["preference"], "cheapest")

    def test_lowest_fare_sets_preference(self):
        result = self.parser.parse_query("lowest fare from Aluva to Thrissur")
        self.assertEqual(result["optimization_preference"], "cheapest")

    def test_budget_friendly_sets_preference(self):
        result = self.parser.parse_query("budget friendly route from Ernakulam to Kollam")
        self.assertEqual(result["optimization_preference"], "cheapest")

    def test_no_budget_is_none(self):
        result = self.parser.parse_query("fastest route from Aluva to Kaloor")
        self.assertIsNone(result["budget_limit"])


class TestTransportPreferences(unittest.TestCase):
    """Tests for transport mode and preference parsing."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_metro_only(self):
        result = self.parser.parse_query("metro only from Aluva to Kaloor")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertIn("bus", excluded)
        self.assertIn("train", excluded)

    def test_avoid_buses(self):
        result = self.parser.parse_query("From Aluva to Kaloor avoid buses")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertIn("bus", excluded)

    def test_train_preferred(self):
        result = self.parser.parse_query("From Ernakulam to Thrissur train preferred")
        prefs = result.get("additional_constraints", {}).get("preferred_modes", [])
        self.assertIn("train", prefs)

    def test_fastest_preference(self):
        result = self.parser.parse_query("fastest way to Thrissur from Ernakulam")
        self.assertEqual(result["optimization_preference"], "fastest")

    def test_cheapest_preference(self):
        result = self.parser.parse_query("cheapest route from Ernakulam to Thrissur")
        self.assertEqual(result["optimization_preference"], "cheapest")

    def test_fewest_transfers(self):
        result = self.parser.parse_query("fewest transfers from Aluva to Kaloor")
        self.assertEqual(result["optimization_preference"], "fewest_transfers")

    def test_comfortable_journey(self):
        result = self.parser.parse_query("comfortable journey from Aluva to Kaloor")
        self.assertEqual(result["optimization_preference"], "balanced")

    def test_walking_is_okay(self):
        """walking is okay → walk should NOT be in excluded_modes"""
        result = self.parser.parse_query("walking is okay from Aluva to Kaloor")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertNotIn("walk", excluded)

    def test_avoid_walking(self):
        result = self.parser.parse_query("From Aluva to Kaloor avoid walking")
        excluded = result.get("additional_constraints", {}).get("excluded_modes", [])
        self.assertIn("walk", excluded)


class TestDateInQuery(unittest.TestCase):
    """Tests that dates in queries are captured in travel_date."""

    def setUp(self):
        self.parser = AIQueryParser()
        self.today = datetime.date.today()

    def test_today_in_query(self):
        result = self.parser.parse_query("Book for today from Aluva to Kaloor")
        self.assertEqual(result["travel_date"], self.today.isoformat())

    def test_tomorrow_in_query(self):
        result = self.parser.parse_query("I need to travel tomorrow from Ernakulam to Thrissur")
        expected = (self.today + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(result["travel_date"], expected)

    def test_this_weekend(self):
        result = self.parser.parse_query("This weekend from Kochi to Thrissur")
        self.assertIsNotNone(result["travel_date"])
        travel_date = datetime.date.fromisoformat(result["travel_date"])
        self.assertEqual(travel_date.weekday(), 5)  # Saturday


class TestBackwardCompatibility(unittest.TestCase):
    """Ensure existing test expectations still pass."""

    def setUp(self):
        self.parser = AIQueryParser()

    def test_complex_query_original(self):
        """Original test: complex query with source, destination, time, budget."""
        query = "I need to reach Kaloor from Aluva before 10:30 AM under ₹150"
        parsed = self.parser.parse_query(query)

        self.assertEqual(parsed["source"], "Aluva")
        self.assertEqual(parsed["destination"], "Kaloor")
        self.assertEqual(parsed["departure_time"], "10:30")
        self.assertEqual(parsed["budget"], 150.0)
        self.assertEqual(parsed["preference"], "cheapest")

    def test_simple_speed_query(self):
        """Original test: fastest way query."""
        query = "fastest way to Tripunithura from Edappally"
        parsed = self.parser.parse_query(query)

        self.assertEqual(parsed["source"], "Edappally")
        self.assertEqual(parsed["destination"], "Tripunithura")
        self.assertEqual(parsed["preference"], "fastest")

    def test_reach_before_time(self):
        """Original example: Reach Thrissur before 6 PM under ₹300"""
        query = "From Ernakulam reach Thrissur before 6 PM under ₹300"
        parsed = self.parser.parse_query(query)

        self.assertEqual(parsed["source"], "Ernakulam")
        self.assertEqual(parsed["destination"], "Thrissur")
        self.assertEqual(parsed["arrival_deadline"], "18:00")
        self.assertEqual(parsed["budget_limit"], 300.0)
        self.assertEqual(parsed["preference"], "cheapest")

    def test_ai_parsed_flag(self):
        result = self.parser.parse_query("Aluva to Kaloor")
        self.assertTrue(result["ai_parsed"])

    def test_original_query_preserved(self):
        q = "Aluva to Kaloor"
        result = self.parser.parse_query(q)
        self.assertEqual(result["original_query"], q)

    def test_additional_constraints_key_always_present(self):
        result = self.parser.parse_query("Aluva to Kaloor")
        self.assertIn("additional_constraints", result)

    def test_no_budget_returns_none(self):
        result = self.parser.parse_query("Aluva to Kaloor")
        self.assertIsNone(result["budget"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
