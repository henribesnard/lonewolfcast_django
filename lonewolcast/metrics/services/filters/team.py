from .base import BaseFilter
from typing import List, Dict, Any
from enum import Enum

class TeamLocation(Enum):
    HOME = 'home'
    AWAY = 'away'
    ALL = 'all'

class TeamFilter(BaseFilter):
    """Filtre les matchs par équipe et position (domicile/extérieur)."""
    
    def __init__(self, team_id: int, location: TeamLocation = TeamLocation.ALL):
        self.team_id = team_id
        self.location = location

    def apply(self, matches: List[Dict]) -> List[Dict]:
        if self.location == TeamLocation.ALL:
            return [
                match for match in matches
                if (match.get('teams', {}).get('home', {}).get('id') == self.team_id or
                    match.get('teams', {}).get('away', {}).get('id') == self.team_id)
            ]
        elif self.location == TeamLocation.HOME:
            return [
                match for match in matches
                if match.get('teams', {}).get('home', {}).get('id') == self.team_id
            ]
        else:  # AWAY
            return [
                match for match in matches
                if match.get('teams', {}).get('away', {}).get('id') == self.team_id
            ]
