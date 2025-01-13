from .base import BaseFilter
from typing import List, Dict
from firebase_admin import db
import logging

logger = logging.getLogger(__name__)

class SeasonFilter(BaseFilter):
    """Filtre les matchs par saison."""
    
    def __init__(self, season: int):
        self.season = season

    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            seasons_data = matches_ref.get(etag=False)
            if not seasons_data:
                return matches
            
            # Parcourir toutes les saisons
            for _, season_data in seasons_data.items():
                # Parcourir les leagues dans chaque saison
                for league_key, league_data in season_data.items():
                    if not isinstance(league_data, dict):
                        continue

                    # Vérifier l'année dans metadata_season
                    season_metadata = league_data.get('metadata_season', {})
                    if season_metadata.get('year') != self.season:
                        continue

                    # Si l'année correspond, ajouter les matchs
                    if 'fixtures' in league_data:
                        matches.extend(league_data['fixtures'].values())
                        logger.debug(f"Ajout des matchs de {league_key} pour la saison {self.season}")

            logger.info(f"SeasonFilter: {len(matches)} matchs trouvés pour la saison {self.season}")
            return matches
            
        except Exception as e:
            logger.error(f"Erreur lors du filtrage par saison: {e}")
            return matches