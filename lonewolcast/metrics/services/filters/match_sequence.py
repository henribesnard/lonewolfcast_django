from datetime import datetime
from typing import List, Dict, Any
from .base import BaseFilter
from firebase_admin import db
import logging

logger = logging.getLogger(__name__)

class LastMatchesFilter(BaseFilter):
    """Filtre pour obtenir les X derniers matchs."""
    
    def __init__(self, count: int):
        self.count = count

    def apply(self, ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            # Récupérer tous les matches
            seasons_data = ref.get(etag=False)
            if not seasons_data:
                return matches

            # Collecter tous les matches avec leur date
            matches_with_dates = []
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
                            matches_with_dates.append((match_date, fixture))
                        except Exception as e:
                            logger.error(f"Erreur lors du parsing de la date: {e}")
                            continue

            # Trier par date décroissante et prendre les N derniers
            sorted_matches = sorted(matches_with_dates, key=lambda x: x[0], reverse=True)
            matches = [match for _, match in sorted_matches[:self.count]]

            logger.info(f"LastMatchesFilter: Retourne {len(matches)} matchs sur {len(matches_with_dates)} disponibles")
            return matches

        except Exception as e:
            logger.error(f"Erreur lors du filtrage des derniers matchs: {e}")
            return matches

class FirstMatchesFilter(BaseFilter):
    """Filtre pour obtenir les X premiers matchs."""
    
    def __init__(self, count: int):
        self.count = count

    def apply(self, ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            # Récupérer tous les matches
            seasons_data = ref.get(etag=False)
            if not seasons_data:
                return matches

            # Collecter tous les matches avec leur date
            matches_with_dates = []
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
                            matches_with_dates.append((match_date, fixture))
                        except Exception as e:
                            logger.error(f"Erreur lors du parsing de la date: {e}")
                            continue

            # Trier par date croissante et prendre les N premiers
            sorted_matches = sorted(matches_with_dates, key=lambda x: x[0])
            matches = [match for _, match in sorted_matches[:self.count]]

            logger.info(f"FirstMatchesFilter: Retourne {len(matches)} matchs sur {len(matches_with_dates)} disponibles")
            return matches

        except Exception as e:
            logger.error(f"Erreur lors du filtrage des premiers matchs: {e}")
            return matches