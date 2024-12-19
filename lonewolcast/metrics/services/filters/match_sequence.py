from operator import itemgetter
from .base import BaseFilter
from typing import List, Dict, Any

class LastMatchesFilter(BaseFilter):
    """Filtre pour obtenir les X derniers matchs."""
    
    def __init__(self, count: int):
        self.count = count

    def apply(self, matches: List[Dict]) -> List[Dict]:
        sorted_matches = sorted(
            matches,
            key=lambda x: x['fixture']['timestamp'],
            reverse=True
        )
        return sorted_matches[:self.count]

class FirstMatchesFilter(BaseFilter):
    """Filtre pour obtenir les X premiers matchs."""
    
    def __init__(self, count: int):
        self.count = count

    def apply(self, matches: List[Dict]) -> List[Dict]:
        sorted_matches = sorted(
            matches,
            key=lambda x: x['fixture']['timestamp']
        )
        return sorted_matches[:self.count]