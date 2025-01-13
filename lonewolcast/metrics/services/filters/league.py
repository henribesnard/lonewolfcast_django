from .base import BaseFilter
from typing import List, Dict, Any
from firebase_admin import db

class LeagueFilter(BaseFilter):
    """Filtre les matchs par league."""
    
    def __init__(self, league_id: int):
        self.league_id = league_id

    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            seasons_data = matches_ref.get(etag=False)
            if not seasons_data:
                return matches
                
            for season_data in seasons_data.values():
                league_key = f'league_{self.league_id}'
                if league_key in season_data:
                    league_data = season_data[league_key]
                    if isinstance(league_data, dict) and 'fixtures' in league_data:
                        matches.extend(league_data['fixtures'].values())
            return matches
        except Exception as e:
            print(f"Erreur lors du filtrage par league: {e}")
            return matches
