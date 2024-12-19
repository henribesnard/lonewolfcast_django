from .base import BaseFilter
from typing import List, Dict

class SeasonFilter(BaseFilter):
    """Filtre les matchs par saison."""
    
    def __init__(self, season: int):
        self.season = season

    def apply(self, matches: List[Dict]) -> List[Dict]:
        return [
            match for match in matches
            if match.get('league', {}).get('season') == self.season
        ]