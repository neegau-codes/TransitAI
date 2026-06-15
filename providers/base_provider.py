from abc import ABC, abstractmethod
from typing import List
from models.transport import Segment

class TransportProvider(ABC):
    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the unique name of the transit provider."""
        pass

    @abstractmethod
    def get_all_segments(self, db_connection) -> List[Segment]:
        """
        Fetches all travel segments managed by this provider from the datasource.
        In the future, this can be swapped to pull from external REST APIs (e.g. NTES, Metro APIs).
        """
        pass
