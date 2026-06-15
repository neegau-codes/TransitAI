import re
import datetime
from typing import Dict, Any, Optional
from database.db import get_db_connection

class NLPParser:
    def __init__(self):
        # Cache locations from DB to perform keyword matching
        self.location_names = self._load_location_names()

    def _load_location_names(self) -> list:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # We want general area names, e.g. "Aluva", "Kaloor", "Tripunithura"
            # Get unique prefix names before "Metro", "Railway", "Bus"
            cursor.execute("SELECT name FROM locations")
            full_names = [r["name"] for r in cursor.fetchall()]
            conn.close()
            
            # Extract core names (e.g. "Aluva Railway Station" -> "Aluva")
            core_names = set()
            for name in full_names:
                # Split by common qualifiers
                core = re.split(r'\s+(?:Metro|Railway|Bus|Junction|Hub|Stand|Stop|Town|Hall|South)\b', name, flags=re.IGNORECASE)[0]
                core_names.add(core.strip())
            return sorted(list(core_names), key=len, reverse=True)
        except Exception as e:
            # Fallback if DB not ready
            return ["Aluva", "Kalamassery", "Edappally", "Kaloor", "Ernakulam", "Vytila", "Tripunithura"]

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parses natural language queries into route search parameters.
        Example: "I need to reach Kaloor from Aluva before 11 AM under Rs. 100"
        
        Returns:
            dict: {
                "source": str or None,
                "destination": str or None,
                "departure_time": str ("HH:MM"),
                "preference": str ("fastest", "cheapest", "fewest_transfers"),
                "budget": float or None,
                "ai_parsed": bool
            }
        """
        # Lowercase the query for easier matching
        q_lower = query.lower()
        
        # 1. Parse Source and Destination
        source = None
        destination = None
        
        # Look for matching locations in query
        matched_locations = []
        for loc in self.location_names:
            if re.search(r'\b' + re.escape(loc.lower()) + r'\b', q_lower):
                matched_locations.append(loc)
                
        # Heuristics for source/destination identification
        if len(matched_locations) >= 2:
            # Check "from X to Y" pattern
            from_to_match = re.search(r'from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)', q_lower)
            to_from_match = re.search(r'to\s+([a-zA-Z\s]+?)\s+from\s+([a-zA-Z\s]+)', q_lower)
            
            if from_to_match:
                s_cand = from_to_match.group(1).strip()
                d_cand = from_to_match.group(2).strip()
                for loc in matched_locations:
                    if loc.lower() in s_cand:
                        source = loc
                    if loc.lower() in d_cand:
                        destination = loc
            elif to_from_match:
                d_cand = to_from_match.group(1).strip()
                s_cand = to_from_match.group(2).strip()
                for loc in matched_locations:
                    if loc.lower() in s_cand:
                        source = loc
                    if loc.lower() in d_cand:
                        destination = loc
            
            # If from/to patterns failed, check order of appearance
            if not source or not destination:
                # Sort matched locations by their appearance index in query
                matches_with_idx = [(loc, q_lower.find(loc.lower())) for loc in matched_locations]
                matches_with_idx.sort(key=lambda x: x[1])
                # Filter out overlapping substrings
                unique_matches = []
                for loc, idx in matches_with_idx:
                    if not any(loc != other and idx >= other_idx and idx < other_idx + len(other) for other, other_idx in unique_matches):
                        unique_matches.append((loc, idx))
                
                if len(unique_matches) >= 2:
                    source = unique_matches[0][0]
                    destination = unique_matches[1][0]
                elif len(unique_matches) == 1:
                    destination = unique_matches[0][0]
        elif len(matched_locations) == 1:
            destination = matched_locations[0]
            # Try to see if there is an explicit "from" or "to"
            if "from " in q_lower:
                source = matched_locations[0]
                destination = None

        # 2. Parse Budget (e.g. "under ₹100", "below Rs 50", "budget 80")
        budget = None
        budget_match = re.search(
            r'(?:under|below|budget|cost|max|maximum|limit|₹|inr)\s*(?:rs\.?|rupees|₹)?\s*(\d+)', 
            q_lower
        )
        if budget_match:
            budget = float(budget_match.group(1))

        # 3. Parse Time constraints (e.g. "before 11 AM", "by 10:30 PM", "before 15:00")
        # Format default to current time
        now = datetime.datetime.now()
        departure_time = now.strftime("%H:%M")
        
        time_match = re.search(
            r'\b(?:before|by|at|around|before\s+at)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', 
            q_lower
        )
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            
            if ampm:
                ampm = ampm.lower()
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
            
            departure_time = f"{hour:02d}:{minute:02d}"

        # 4. Parse Preferences (e.g. "fastest route", "cheapest way", "fewest transfers")
        preference = "fastest" # Default
        if any(w in q_lower for w in ["cheap", "budget", "low cost", "under"]):
            preference = "cheapest"
        elif any(w in q_lower for w in ["transfer", "change", "direct", "fewest"]):
            preference = "fewest_transfers"
        elif any(w in q_lower for w in ["fast", "quick", "speed", "soonest"]):
            preference = "fastest"

        return {
            "source": source,
            "destination": destination,
            "departure_time": departure_time,
            "preference": preference,
            "budget": budget,
            "ai_parsed": True,
            "original_query": query
        }

    # =========================================================================
    # FUTURE GEMINI / OPENAI INTEGRATION ARCHITECTURE READY
    # =========================================================================
    # To replace the rule-based engine above with a LLM, you would:
    # 1. Install Google GenAI SDK: `.venv/Scripts/pip install google-genai`
    # 2. Configure GEMINI_API_KEY environment variable.
    # 3. Update the method as shown below.
    #
    # def parse_query_with_gemini(self, query: str) -> Dict[str, Any]:
    #     import os
    #     from google import genai
    #     from google.genai import types
    #     from pydantic import BaseModel, Field
    #
    #     # Define schema for structured JSON output
    #     class TransitQuerySchema(BaseModel):
    #         source: Optional[str] = Field(None, description="The starting city/neighborhood name")
    #         destination: Optional[str] = Field(None, description="The ending city/neighborhood name")
    #         departure_time: Optional[str] = Field(None, description="Time formatted as HH:MM, e.g. 11:00 or 15:30")
    #         preference: Optional[str] = Field("fastest", description="One of: fastest, cheapest, fewest_transfers")
    #         budget: Optional[float] = Field(None, description="Numeric budget limit if specified, in INR")
    #
    #     api_key = os.environ.get("GEMINI_API_KEY")
    #     if not api_key:
    #         return self.parse_query(query) # Fallback to offline rule-based parser
    #
    #     client = genai.Client(api_key=api_key)
    #     
    #     prompt = f"""
    #     You are an AI assistant for TransitAI, a travel planner.
    #     Parse the user's travel request and extract the parameters:
    #     User query: "{query}"
    #     Current local time: {datetime.datetime.now().strftime("%I:%M %p")}
    #     Available stations/areas: {self.location_names}
    #     """
    #
    #     response = client.models.generate_content(
    #         model='gemini-2.5-flash',
    #         contents=prompt,
    #         config=types.GenerateContentConfig(
    #             response_mime_type="application/json",
    #             response_schema=TransitQuerySchema,
    #             temperature=0.0
    #         )
    #     )
    #
    #     import json
    #     try:
    #         data = json.loads(response.text)
    #         # Default departure time if not detected
    #         if not data.get("departure_time"):
    #             data["departure_time"] = datetime.datetime.now().strftime("%H:%M")
    #         data["ai_parsed"] = True
    #         data["original_query"] = query
    #         return data
    #     except Exception:
    #         return self.parse_query(query) # Fallback
