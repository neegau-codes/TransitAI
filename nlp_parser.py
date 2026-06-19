"""
nlp_parser.py
A backward-compatible wrapper around ai_parser.py.
"""

from typing import Dict, Any
from ai_parser import AIQueryParser

class NLPParser:
    def __init__(self):
        self.parser = AIQueryParser()
        # Expose location_names for backward compatibility
        self.location_names = self.parser.location_names

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Delegates natural language parsing to the main AIQueryParser.
        """
        return self.parser.parse_query(query)
