from .base import BaseFilter
from typing import List, Dict, Any

class LeagueFilter(BaseFilter):
    """Filtre les matchs par league."""
    
    def __init__(self, league_id: int):
        self.league_id = league_id

    def apply(self, matches: List[Dict]) -> List[Dict]:
        return [
            match for match in matches
            if match.get('league', {}).get('id') == self.league_id
        ]