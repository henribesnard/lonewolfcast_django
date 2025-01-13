from datetime import datetime
from typing import List, Dict, Any
from .base import BaseFilter
from firebase_admin import db
import logging

logger = logging.getLogger(__name__)

class YearFilter(BaseFilter):
    """Filtre les matchs par année civile."""
    
    def __init__(self, year: int):
        self.year = year

    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            seasons_data = matches_ref.get(etag=False)
            if not seasons_data:
                return matches

            for season_data in seasons_data.values():
                for league_data in season_data.values():
                    if not isinstance(league_data, dict) or 'fixtures' not in league_data:
                        continue

                    for fixture in league_data['fixtures'].values():
                        try:
                            metadata = fixture.get('metadata', {})
                            date_str = metadata.get('date')
                            if not date_str:
                                continue

                            match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if match_date.year == self.year:
                                matches.append(fixture)
                        except Exception as e:
                            logger.error(f"Erreur lors du traitement d'un match: {e}")
                            continue

            logger.info(f"YearFilter: {len(matches)} matchs trouvés pour l'année {self.year}")
            return matches

        except Exception as e:
            logger.error(f"Erreur lors du filtrage par année: {e}")
            return matches

class MonthFilter(BaseFilter):
    """Filtre les matchs par mois d'une année."""
    
    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month

    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            seasons_data = matches_ref.get(etag=False)
            if not seasons_data:
                return matches

            for season_data in seasons_data.values():
                for league_data in season_data.values():
                    if not isinstance(league_data, dict) or 'fixtures' not in league_data:
                        continue

                    for fixture in league_data['fixtures'].values():
                        try:
                            metadata = fixture.get('metadata', {})
                            date_str = metadata.get('date')
                            if not date_str:
                                continue

                            match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if match_date.year == self.year and match_date.month == self.month:
                                matches.append(fixture)
                        except Exception as e:
                            logger.error(f"Erreur lors du traitement d'un match: {e}")
                            continue

            logger.info(f"MonthFilter: {len(matches)} matchs trouvés pour {self.month}/{self.year}")
            return matches

        except Exception as e:
            logger.error(f"Erreur lors du filtrage par mois: {e}")
            return matches
