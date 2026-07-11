"""
ai_parser.py
Parses natural language travel queries into structured constraints.

Features:
  - Date understanding  (today, tomorrow, next Monday, this weekend …)
  - Time understanding  (before 6 pm, around 8, between 5 and 7, morning, ASAP …)
  - Budget extraction   (below 200, under ₹300, cheap, budget friendly …)
  - Transport prefs     (metro only, avoid buses, fastest, fewest transfers …)
  - Manglish support    (tvm, ekm, clt, tsr, aluva ninn kaloor, train venam …)
  - Partial + fuzzy loc matching (alu → Aluva, kalo → Kaloor, thrisur → Thrissur)
  - Incomplete query handling (returns missing + suggestion instead of crashing)
  - Typo handling       (kochin, trivandrom, thrisur → resolved correctly)
"""

import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
from database.db import get_db_connection


# ---------------------------------------------------------------------------
# MANGLISH / SHORTHAND NORMALISATION DICTIONARY
# ---------------------------------------------------------------------------

MANGLISH_EXPANSIONS: Dict[str, str] = {
    # City abbreviations
    "tvm":  "Thiruvananthapuram",
    "tvpm": "Thiruvananthapuram",
    "ekm":  "Ernakulam",
    "clt":  "Kozhikode",
    "tsr":  "Thrissur",
    "tcr":  "Thrissur",
    "pkd":  "Palakkad",
    "aluva": "Aluva",

    # Common place shortforms / colloquial names
    "kochi":   "Kochi",
    "cochin":  "Kochi",
    "kochin":  "Kochi",
    "ernakulam": "Ernakulam",
    "erna":    "Ernakulam",
    "trissur": "Thrissur",
    "thrisur": "Thrissur",
    "thrissure": "Thrissur",
    "trivandrum": "Thiruvananthapuram",
    "trivandrom": "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "trivendrum": "Thiruvananthapuram",
    "tripu":   "Tripunithura",
    "tripunithura": "Tripunithura",
    "thiru":   "Thiruvananthapuram",
    "kalor":   "Kaloor",
    "kaloor":  "Kaloor",
    "aluvaa":  "Aluva",
    "angamali": "Angamaly",
    "angamaly": "Angamaly",
    "guruvayoor": "Guruvayur",
    "guruvayur": "Guruvayur",
    "kozhikode": "Kozhikode",
    "calicut": "Kozhikode",
    "kannur":  "Kannur",
    "cannanore": "Kannur",
    "kottayam": "Kottayam",
    "kollam":  "Kollam",
    "quilon":  "Kollam",
    "palakkad": "Palakkad",
    "palghat": "Palakkad",
    "vytila":  "Vytila",
    "edappally": "Edappally",
    "kalamassery": "Kalamassery",

    # Manglish preposition phrases
    "ninn":  "from",   # "aluva ninn" → "from aluva"
    "ninnu": "from",
    "ninnum": "from",
    "ile":   "from",
    "pokanam": "to go",   # "thrissur pokanam" → "to go thrissur"
    "povam": "to go",
    "pokam": "to go",
    "venam": "needed",   # "train venam" → "train needed"
    "venda": "not needed",  # "walk venda" → "walk not needed"
    "mathi": "enough",   # "bus mathi" → "bus enough" / only bus
    "aanu":  "is",

    # Transport shorthands
    "metro":  "metro",
    "train":  "train",
    "bus":    "bus",
    "walk":   "walk",
    "auto":   "auto",
    "cab":    "taxi",

    # Station / hub suffixes (normalise so location matching sees core names)
    "railway station": "",
    "metro station":   "",
    "bus stand":       "",
    "bus stop":        "",
    "jn":   "Junction",
    "jn.":  "Junction",
}

# Manglish transport-intent keywords
MANGLISH_ONLY_TRANSPORT = {
    "bus mathi":   ("only", "bus"),
    "metro mathi": ("only", "metro"),
    "train mathi": ("only", "train"),
    "train venam": ("prefer", "train"),
    "metro venam": ("prefer", "metro"),
    "bus venam":   ("prefer", "bus"),
    "walk venda":  ("avoid", "walk"),
    "bus venda":   ("avoid", "bus"),
    "metro venda": ("avoid", "metro"),
}

# ---------------------------------------------------------------------------
# KNOWN LOCATIONS (static fallback + used for fuzzy matching)
# ---------------------------------------------------------------------------

KNOWN_LOCATIONS: List[str] = [
    "Aluva", "Kalamassery", "Edappally", "Kaloor", "Ernakulam",
    "Vytila", "Tripunithura", "Kochi", "Thrissur", "Palakkad",
    "Kozhikode", "Kannur", "Kottayam", "Kollam", "Thiruvananthapuram",
    "Angamaly", "Guruvayur",
]


# ---------------------------------------------------------------------------
# LIGHTWEIGHT FUZZY HELPERS  (no heavy deps — pure stdlib)
# ---------------------------------------------------------------------------

def _edit_distance(a: str, b: str) -> int:
    """Classic Wagner-Fischer O(m*n) edit distance."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _best_fuzzy_match(
    word: str,
    candidates: List[str],
    max_distance: int = 3
) -> Optional[str]:
    """
    Returns the best fuzzy match for `word` among `candidates`.
    Priority: exact > case-insensitive > prefix > edit-distance.
    Returns None when no candidate is within `max_distance` edits.
    """
    w = word.lower()

    # 1. Exact (case-insensitive)
    for c in candidates:
        if c.lower() == w:
            return c

    # 2. Prefix
    prefix_matches = [c for c in candidates if c.lower().startswith(w)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        # Return the shortest (most specific) prefix match
        return min(prefix_matches, key=len)

    # 3. Edit distance
    scored = [(c, _edit_distance(w, c.lower())) for c in candidates]
    scored.sort(key=lambda x: x[1])
    if scored and scored[0][1] <= max_distance:
        return scored[0][0]

    return None


# ---------------------------------------------------------------------------
# TIME-OF-DAY HELPERS
# ---------------------------------------------------------------------------

_TIME_OF_DAY: Dict[str, Tuple[str, str]] = {
    "morning":   ("06:00", "11:59"),
    "afternoon": ("12:00", "17:59"),
    "evening":   ("17:00", "20:59"),
    "night":     ("20:00", "23:59"),
    "tonight":   ("20:00", "23:59"),
    "midnight":  ("00:00", "01:00"),
}


# ---------------------------------------------------------------------------
# DATE HELPERS
# ---------------------------------------------------------------------------

_WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _parse_date_phrase(text: str) -> Optional[datetime.date]:
    """
    Recognises relative date phrases and returns a datetime.date.
    Returns None if nothing matched.
    """
    t = text.lower()
    today = datetime.date.today()
    weekday_today = today.weekday()  # 0=Mon … 6=Sun

    # IMPORTANT: check the most specific phrases FIRST (day after tomorrow before tomorrow)
    if re.search(r'\bday after tomorrow\b', t):
        return today + datetime.timedelta(days=2)
    if re.search(r'\btoday\b', t):
        return today
    if re.search(r'\btomorrow\b', t):
        return today + datetime.timedelta(days=1)

    # "this weekend" → coming Saturday
    if re.search(r'\bthis weekend\b', t):
        days_until_sat = (5 - weekday_today) % 7 or 7
        return today + datetime.timedelta(days=days_until_sat)

    # "next Monday" / "next Friday" etc.
    for i, day in enumerate(_WEEKDAY_NAMES):
        if re.search(r'\bnext\s+' + day + r'\b', t):
            days_ahead = (i - weekday_today) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + datetime.timedelta(days=days_ahead)

    # bare weekday name like "Monday morning" / "Friday evening"
    for i, day in enumerate(_WEEKDAY_NAMES):
        if re.search(r'\b' + day + r'\b', t):
            days_ahead = (i - weekday_today) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + datetime.timedelta(days=days_ahead)

    return None


# ---------------------------------------------------------------------------
# MAIN PARSER CLASS
# ---------------------------------------------------------------------------

class AIQueryParser:
    def __init__(self):
        self.location_names = self._load_location_names()

    # ------------------------------------------------------------------
    # Location loading
    # ------------------------------------------------------------------

    def _load_location_names(self) -> List[str]:
        """Loads and formats location names from the database for matching."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM locations")
            full_names = [r["name"] for r in cursor.fetchall()]
            conn.close()

            core_names: set = set()
            for name in full_names:
                core = re.split(
                    r'\s+(?:Metro|Railway|Bus|Junction|Hub|Stand|Stop|Town|Hall|South|Central|Station)\b',
                    name, flags=re.IGNORECASE
                )[0]
                core_names.add(core.strip())
            # Also seed with KNOWN_LOCATIONS so fallback list is always available
            core_names.update(KNOWN_LOCATIONS)
            return sorted(list(core_names), key=len, reverse=True)
        except Exception:
            return sorted(KNOWN_LOCATIONS, key=len, reverse=True)

    # ------------------------------------------------------------------
    # Manglish pre-processing
    # ------------------------------------------------------------------

    def _normalize_manglish(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Applies the Manglish / shorthand dictionary to normalise the query.
        Also extracts Manglish transport intent signals.
        Returns (normalised_query, manglish_hints_dict).
        """
        hints: Dict[str, Any] = {}
        q = query.strip()

        # Detect and record Manglish transport phrases BEFORE expansion
        q_low = q.lower()
        for phrase, (intent, mode) in MANGLISH_ONLY_TRANSPORT.items():
            if phrase in q_low:
                hints.setdefault("transport_intents", []).append((intent, mode))

        # Protect multi-word English idioms from being broken by single-word
        # Manglish expansions (e.g. "day after tomorrow" contains "after").
        # We shield them with a placeholder, expand, then restore.
        PROTECTED_PHRASES = {
            "__DAT__": "day after tomorrow",
            "__LESS_THAN__": "less than",
            "__NO_LATER__": "no later than",
        }
        q_protected = q
        for placeholder, phrase in PROTECTED_PHRASES.items():
            q_protected = re.sub(re.escape(phrase), placeholder, q_protected, flags=re.IGNORECASE)

        # Special regex for postpositions like "ninn" (from)
        # e.g. "aluva ninn" -> "from aluva"
        q_protected = re.sub(r'\b([a-zA-Z]+)\s+(ninn|ninnu|ninnum|ile)\b', r'from \1', q_protected, flags=re.IGNORECASE)

        # Replace multi-word Manglish phrases first, then single words
        for src, tgt in sorted(MANGLISH_EXPANSIONS.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(r'\b' + re.escape(src) + r'\b', re.IGNORECASE)
            q_protected = pattern.sub(tgt, q_protected)

        # Restore protected phrases
        for placeholder, phrase in PROTECTED_PHRASES.items():
            q_protected = q_protected.replace(placeholder, phrase)

        # Clean up extra whitespace
        q_protected = re.sub(r'\s+', ' ', q_protected).strip()
        return q_protected, hints

    # ------------------------------------------------------------------
    # Location matching
    # ------------------------------------------------------------------

    def _match_locations_in_query(self, q_lower: str) -> List[Tuple[str, int]]:
        """
        Finds known locations mentioned in the query.
        Tries: exact whole-word → prefix → fuzzy on each token.
        Returns list of (location_name, position_in_query) tuples,
        ordered by position.
        """
        matched: List[Tuple[str, int]] = []  # (name, position)
        matched_names: List[str] = []

        # --- Pass 1: whole-word match against known locations ---
        for loc in self.location_names:
            pattern = r'\b' + re.escape(loc.lower()) + r'\b'
            m = re.search(pattern, q_lower)
            if m:
                matched.append((loc, m.start()))
                matched_names.append(loc)

        # --- Pass 2: token-level partial / fuzzy matching for unmatched tokens ---
        covered = set()
        for loc in matched_names:
            for word in loc.lower().split():
                covered.add(word)

        tokens = list(re.finditer(r'[a-zA-Z]+', q_lower))
        # Exclude common English stop-words and Manglish connector words
        stop_words = {
            "i", "to", "from", "the", "a", "an", "and", "or", "in", "at",
            "is", "are", "was", "be", "for", "of", "on", "with", "this",
            "my", "me", "by", "need", "want", "go", "get", "reach", "trip",
            "travel", "route", "way", "can", "how", "do", "please", "help",
            "you", "any", "all", "some", "no", "not", "just", "only", "via",
            # Manglish connectors that were expanded
            "ninn", "ninnu", "pokanam", "venam", "venda", "mathi", "ile",
            # Time-related words that shouldn't become location matches
            "before", "after", "by", "around", "between", "morning",
            "evening", "night", "afternoon", "tonight", "today", "tomorrow",
            "asap", "now", "am", "pm", "hour", "minute",
            # Budget-related
            "under", "below", "maximum", "max", "budget", "cheap", "less",
            "than", "rupees", "fare",
            # Transport adjectives
            "fastest", "cheapest", "direct", "fewest", "transfers",
            "comfortable", "walking", "avoid", "preferred", "train",
            "metro", "bus", "walk",
        }

        for token_match in tokens:
            token = token_match.group()
            # Allow tokens as short as 3 chars (e.g. "alu", "kal", "ekm")
            if token in stop_words or token in covered or len(token) < 2:
                continue
            best = _best_fuzzy_match(token, self.location_names, max_distance=2)
            if best and best not in matched_names:
                matched.append((best, token_match.start()))
                matched_names.append(best)
                for w in best.lower().split():
                    covered.add(w)

        # --- Deduplication: prefer longer match when one is a substring of another ---
        filtered: List[Tuple[str, int]] = []
        for (loc, pos) in matched:
            if not any(
                loc != other and loc.lower() in other.lower()
                for (other, _) in matched
            ):
                filtered.append((loc, pos))

        # Sort by position
        filtered.sort(key=lambda x: x[1])
        return filtered

    def _assign_source_destination(
        self,
        matched_locations: List[Tuple[str, int]],
        q_lower: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Uses preposition heuristics and order-of-appearance to assign
        source and destination from the matched location list.
        matched_locations is a list of (name, position_in_query) tuples.
        """
        source = None
        destination = None

        loc_names = [loc for (loc, _) in matched_locations]

        if len(matched_locations) >= 2:
            from_to = re.search(r'from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)', q_lower)
            to_from = re.search(r'to\s+([a-zA-Z\s]+?)\s+from\s+([a-zA-Z\s]+)', q_lower)

            if from_to:
                s_cand = from_to.group(1).strip()
                d_cand = from_to.group(2).strip()
                for (loc, pos) in matched_locations:
                    # Match by name-in-candidate OR by position within the candidate span
                    if loc.lower() in s_cand or (
                        from_to.start(1) <= pos <= from_to.end(1)
                    ):
                        if source is None:
                            source = loc
                    if loc.lower() in d_cand or (
                        from_to.start(2) <= pos <= from_to.end(2)
                    ):
                        if destination is None:
                            destination = loc
            elif to_from:
                d_cand = to_from.group(1).strip()
                s_cand = to_from.group(2).strip()
                for (loc, pos) in matched_locations:
                    if loc.lower() in s_cand or (
                        to_from.start(2) <= pos <= to_from.end(2)
                    ):
                        if source is None:
                            source = loc
                    if loc.lower() in d_cand or (
                        to_from.start(1) <= pos <= to_from.end(1)
                    ):
                        if destination is None:
                            destination = loc

            # Fallback: order of appearance (positions already sorted)
            if not source or not destination:
                if not source and not destination:
                    source = matched_locations[0][0]
                    destination = matched_locations[1][0]
                elif not source:
                    destination = destination  # already set
                    source = next(
                        (l for (l, _) in matched_locations if l != destination), None
                    )
                elif not destination:
                    source = source  # already set
                    destination = next(
                        (l for (l, _) in matched_locations if l != source), None
                    )

        elif len(matched_locations) == 1:
            loc, pos = matched_locations[0]
            if re.search(r'\bfrom\s+' + re.escape(loc.lower()), q_lower):
                source = loc
            elif re.search(r'\bto\s+' + re.escape(loc.lower()), q_lower):
                destination = loc
            elif re.search(r'\breach\s+' + re.escape(loc.lower()), q_lower):
                destination = loc
            else:
                # Check position-based heuristic: is the loc after 'from' or 'to'?
                from_match = re.search(r'\bfrom\b', q_lower)
                to_match = re.search(r'\bto\b', q_lower)
                if from_match and pos > from_match.start():
                    source = loc
                elif to_match and pos > to_match.start():
                    destination = loc
                else:
                    destination = loc  # Default single location as destination

        return source, destination

    # ------------------------------------------------------------------
    # Time parsing
    # ------------------------------------------------------------------

    def _parse_time_constraints(
        self,
        q_lower: str,
        travel_date: Optional[datetime.date] = None
    ) -> Dict[str, Any]:
        """
        Extracts departure_time, arrival_deadline, and travel_date
        from a lower-cased query string.
        """
        now = datetime.datetime.now()
        departure_time: Optional[str] = None
        arrival_deadline: Optional[str] = None

        # ASAP
        if re.search(r'\basap\b|\bright now\b|\bimmediately\b', q_lower):
            departure_time = now.strftime("%H:%M")
            return {
                "departure_time": departure_time,
                "arrival_deadline": None,
                "travel_date": travel_date or datetime.date.today(),
            }

        # Time-of-day phrases  (morning / evening / tonight etc.)
        for phrase, (start, end) in _TIME_OF_DAY.items():
            if re.search(r'\b' + phrase + r'\b', q_lower):
                # Context clue: if phrase is near "before" → arrival; otherwise departure
                phrase_idx = q_lower.find(phrase)
                prefix = q_lower[max(0, phrase_idx - 20): phrase_idx]
                if any(w in prefix for w in ["before", "by", "reach", "arrive"]):
                    arrival_deadline = end   # deadline is end of that period
                    departure_time = departure_time or now.strftime("%H:%M")
                else:
                    departure_time = start
                break

        # Numeric times  (handles 6, 6 pm, 6:30, 6:30 am, 18:00, etc.)
        time_pattern = r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b'
        time_matches = list(re.finditer(time_pattern, q_lower))

        parsed_times = []
        for match in time_matches:
            hour = int(match.group(1))
            if hour > 24:
                continue  # Likely a budget/distance number

            minute = int(match.group(2)) if match.group(2) else 0
            ampm = match.group(3)

            # Look at prefix window for context
            start_idx = match.start()
            prefix_window = q_lower[max(0, start_idx - 30): start_idx]
            is_arrival = any(w in prefix_window for w in [
                "before", "by", "reach", "arrive", "arrival", "deadline", "no later"
            ])
            is_departure = any(w in prefix_window for w in [
                "after", "leave", "depart", "departure", "start", "from", "earliest"
            ])

            if ampm:
                ampm = ampm.lower()
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
            elif hour < 6 and not ampm:
                # Ambiguous low number (1-5) without am/pm — assume pm if context is arrival
                if is_arrival:
                    hour += 12

            time_str = f"{hour:02d}:{minute:02d}"
            parsed_times.append({
                "time_str": time_str,
                "is_arrival": is_arrival,
                "is_departure": is_departure,
            })

        # "between X and Y" → departure at X, arrival deadline at Y
        between_match = re.search(
            r'\bbetween\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+and\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
            q_lower
        )
        if between_match:
            def _parse_h(h_str, m_str, ap_str):
                h = int(h_str)
                m = int(m_str) if m_str else 0
                if ap_str:
                    ap_str = ap_str.lower()
                    if ap_str == "pm" and h < 12:
                        h += 12
                    elif ap_str == "am" and h == 12:
                        h = 0
                return f"{h:02d}:{m:02d}"

            departure_time = _parse_h(
                between_match.group(1), between_match.group(2), between_match.group(3)
            )
            arrival_deadline = _parse_h(
                between_match.group(4), between_match.group(5), between_match.group(6)
            )
            return {
                "departure_time": departure_time,
                "arrival_deadline": arrival_deadline,
                "travel_date": travel_date or datetime.date.today(),
            }

        # Assign from parsed_times list
        if not departure_time and not arrival_deadline:
            if len(parsed_times) == 1:
                t = parsed_times[0]
                if t["is_arrival"]:
                    arrival_deadline = t["time_str"]
                    # Backward-compat: also set departure_time = arrival time so
                    # the caller (app.py) can detect the "single arrival" case and
                    # substitute the real current time as the search departure.
                    departure_time = t["time_str"]
                else:
                    departure_time = t["time_str"]
            elif len(parsed_times) >= 2:
                deps = [t for t in parsed_times if t["is_departure"]]
                arrs = [t for t in parsed_times if t["is_arrival"]]
                departure_time = deps[0]["time_str"] if deps else parsed_times[0]["time_str"]
                arrival_deadline = arrs[0]["time_str"] if arrs else parsed_times[1]["time_str"]
        elif departure_time and not arrival_deadline and parsed_times:
            # A numeric time was found alongside a phrase-based departure — treat it as arrival
            t = parsed_times[0]
            if t["is_arrival"]:
                arrival_deadline = t["time_str"]
        elif arrival_deadline and not departure_time and parsed_times:
            t = parsed_times[0]
            if t["is_departure"]:
                departure_time = t["time_str"]

        if not departure_time:
            departure_time = now.strftime("%H:%M")

        return {
            "departure_time": departure_time,
            "arrival_deadline": arrival_deadline,
            "travel_date": travel_date or datetime.date.today(),
        }

    # ------------------------------------------------------------------
    # Budget parsing
    # ------------------------------------------------------------------

    def _parse_budget(self, q_lower: str) -> Optional[float]:
        """
        Extracts a numeric budget limit from the query.
        Handles: below/under/max/less than ₹X, cheap, budget friendly, lowest fare.
        """
        # Explicit number
        budget_match = re.search(
            r'(?:under|below|budget|cost|max|maximum|limit|price|₹|inr|less\s+than|at\s+most|upto?|up\s+to)\s*'
            r'(?:rs\.?|rupees|₹)?\s*(\d+(?:\.\d+)?)',
            q_lower
        )
        if budget_match:
            return float(budget_match.group(1))

        # Also handle "₹300" or "Rs 300" without a preceding keyword
        rupee_match = re.search(r'(?:₹|rs\.?\s*)(\d+(?:\.\d+)?)', q_lower)
        if rupee_match:
            return float(rupee_match.group(1))

        # Vague cheapness terms → no numeric limit, but signals preference
        # (Return None here; preference is handled separately)
        return None

    # ------------------------------------------------------------------
    # Transport preference parsing
    # ------------------------------------------------------------------

    def _parse_transport_preferences(
        self,
        q_lower: str,
        manglish_hints: Dict[str, Any]
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Returns (optimization_preference, transfer_preference, additional_constraints).
        """
        additional_constraints: Dict[str, Any] = {}
        excluded_modes: List[str] = []
        preferred_modes: List[str] = []

        # --- Manglish transport intent hints ---
        for intent, mode in manglish_hints.get("transport_intents", []):
            if intent == "only":
                # Include only this mode — exclude everything else
                all_modes = ["metro", "bus", "train", "walk"]
                excluded_modes.extend([m for m in all_modes if m != mode])
            elif intent == "prefer":
                preferred_modes.append(mode)
            elif intent == "avoid":
                excluded_modes.append(mode)

        # --- Explicit text exclusions ---
        if any(p in q_lower for p in ["no metro", "exclude metro", "avoid metro"]):
            excluded_modes.append("metro")
        if any(p in q_lower for p in ["no bus", "exclude bus", "avoid bus", "avoid buses"]):
            excluded_modes.append("bus")
        if any(p in q_lower for p in ["no train", "exclude train", "avoid train"]):
            excluded_modes.append("train")
        if any(p in q_lower for p in ["no walk", "avoid walk", "avoid walking", "walking is not"]):
            excluded_modes.append("walk")

        # --- Explicit text inclusions / preferences ---
        if re.search(r'\bmetro\s+only\b|\bonly\s+metro\b', q_lower):
            excluded_modes.extend([m for m in ["bus", "train"] if m not in excluded_modes])
        if re.search(r'\btrain\s+(?:only|preferred|prefer)\b|\bonly\s+train\b', q_lower):
            preferred_modes.append("train")
        if re.search(r'\bbus\s+only\b|\bonly\s+bus\b', q_lower):
            excluded_modes.extend([m for m in ["metro", "train"] if m not in excluded_modes])
        if re.search(r'\bwalking\s+is\s+okay\b|\bwalk\s+ok\b|\bokay\s+to\s+walk\b', q_lower):
            # Walking is explicitly fine — nothing to exclude
            pass

        if excluded_modes:
            additional_constraints["excluded_modes"] = list(set(excluded_modes))
        if preferred_modes:
            additional_constraints["preferred_modes"] = list(set(preferred_modes))

        # --- Optimization preference ---
        optimization_preference = "fastest"  # default

        cheapness_words = [
            "cheap", "cheapest", "budget", "low cost", "economical",
            "lowest fare", "budget friendly", "budget-friendly", "minimum cost",
            "affordable",
        ]
        speed_words = [
            "fast", "fastest", "quick", "quickest", "speed", "soonest",
            "duration", "earliest",
        ]
        transfer_words = [
            "transfer", "change", "direct", "fewest", "minimum transfer",
            "min transfer", "fewest transfers", "no change",
        ]
        comfort_words = [
            "comfortable", "comfort", "balanced", "best", "optimal",
            "score", "recommended",
        ]

        # "under ₹X" or "below X" implies cheapest preference
        if re.search(
            r'(?:under|below|less\s+than|max|maximum|up\s+to)\s*(?:₹|rs\.?)?\s*\d+',
            q_lower
        ):
            optimization_preference = "cheapest"
        elif any(w in q_lower for w in cheapness_words):
            optimization_preference = "cheapest"
        elif any(w in q_lower for w in transfer_words):
            optimization_preference = "fewest_transfers"
        elif any(w in q_lower for w in comfort_words):
            optimization_preference = "balanced"
        elif any(w in q_lower for w in speed_words):
            optimization_preference = "fastest"

        # --- Transfer preference ---
        transfer_preference = "any"
        if any(p in q_lower for p in ["direct", "no transfer", "zero transfer", "non-stop", "nonstop"]):
            transfer_preference = "direct"
        elif any(p in q_lower for p in ["min transfer", "fewest transfer", "minimum transfer", "fewest transfers"]):
            transfer_preference = "minimum"

        return optimization_preference, transfer_preference, additional_constraints

    # ------------------------------------------------------------------
    # Incomplete query detection
    # ------------------------------------------------------------------

    def _build_incomplete_response(
        self,
        source: Optional[str],
        destination: Optional[str],
        original_query: str,
        base_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        When source or destination is missing, return a structured response
        with 'missing' list and 'suggestion' string rather than crashing.
        """
        missing = []
        if not source:
            missing.append("source")
        if not destination:
            missing.append("destination")

        if missing == ["source"]:
            suggestion = "Where are you travelling from?"
        elif missing == ["destination"]:
            suggestion = "Where do you want to go?"
        else:
            suggestion = "Tell me your starting point and destination."

        return {
            **base_result,
            "incomplete": True,
            "missing": missing,
            "suggestion": suggestion,
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parses travel requests into a structured constraint object.

        Returns dict with keys:
            source, destination, departure_time, arrival_deadline,
            budget_limit, optimization_preference, transfer_preference,
            additional_constraints, travel_date,
            incomplete (bool), missing (list), suggestion (str),
            budget, preference, ai_parsed, original_query
        """
        # ------------------------------------------------------------------
        # Step 0: Manglish / shorthand normalisation
        # ------------------------------------------------------------------
        normalized_query, manglish_hints = self._normalize_manglish(query)
        q_lower = normalized_query.lower()

        # ------------------------------------------------------------------
        # Step 1: Date understanding
        # ------------------------------------------------------------------
        travel_date = _parse_date_phrase(q_lower)

        # ------------------------------------------------------------------
        # Step 2: Location matching  (with partial + fuzzy support)
        # ------------------------------------------------------------------
        matched_locations = self._match_locations_in_query(q_lower)
        source, destination = self._assign_source_destination(matched_locations, q_lower)

        # ------------------------------------------------------------------
        # Step 3: Time constraints
        # ------------------------------------------------------------------
        time_result = self._parse_time_constraints(q_lower, travel_date)
        departure_time = time_result["departure_time"]
        arrival_deadline = time_result["arrival_deadline"]
        travel_date = time_result["travel_date"]

        # ------------------------------------------------------------------
        # Step 4: Budget
        # ------------------------------------------------------------------
        budget_limit = self._parse_budget(q_lower)

        # ------------------------------------------------------------------
        # Step 5: Transport preferences
        # ------------------------------------------------------------------
        optimization_preference, transfer_preference, additional_constraints = \
            self._parse_transport_preferences(q_lower, manglish_hints)

        # ------------------------------------------------------------------
        # Step 6: Build result
        # ------------------------------------------------------------------
        base_result: Dict[str, Any] = {
            "source": source,
            "destination": destination,
            "departure_time": departure_time,
            "arrival_deadline": arrival_deadline,
            "budget_limit": budget_limit,
            "optimization_preference": optimization_preference,
            "transfer_preference": transfer_preference,
            "additional_constraints": additional_constraints,
            "travel_date": travel_date.isoformat() if travel_date else None,

            # Backward-compatible fields
            "budget": budget_limit,
            "preference": optimization_preference,
            "ai_parsed": True,
            "original_query": query,

            # Incomplete query fields (default: complete)
            "incomplete": False,
            "missing": [],
            "suggestion": "",
        }

        # ------------------------------------------------------------------
        # Step 7: Detect incomplete queries
        # ------------------------------------------------------------------
        if not source or not destination:
            return self._build_incomplete_response(source, destination, query, base_result)

        return base_result
