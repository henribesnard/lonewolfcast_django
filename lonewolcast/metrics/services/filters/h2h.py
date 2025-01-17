# filters/h2h.py
from enum import Enum
from typing import List, Dict, Optional
from firebase_admin import db
from .base import BaseFilter
import logging

logger = logging.getLogger(__name__)

class H2HLocation(Enum):
    """Position des équipes pour les confrontations directes."""
    ANY = 'any'  # N'importe quelle configuration
    TEAM1_HOME = 'team1_home'  # Équipe 1 à domicile uniquement
    TEAM1_AWAY = 'team1_away'  # Équipe 1 à l'extérieur uniquement

class H2HFilter(BaseFilter):
    """Filtre pour les confrontations directes entre deux équipes."""
    
    def __init__(self, team1_id: int, team2_id: int, location: H2HLocation = H2HLocation.ANY):
        """
        Initialise le filtre H2H.
        
        Args:
            team1_id: ID de la première équipe
            team2_id: ID de la deuxième équipe
            location: Configuration de domicile/extérieur souhaitée
        """
        self.team1_id = int(team1_id)
        self.team2_id = int(team2_id)
        self.location = location
        
        if self.team1_id == self.team2_id:
            raise ValueError("Les deux équipes doivent être différentes pour le H2H")

    def apply(self, ref: db.Reference) -> List[Dict]:
        """
        Applique le filtre H2H sur les données.
        
        Args:
            ref: Référence Firebase vers le nœud des matchs
            
        Returns:
            Liste des matchs entre les deux équipes spécifiées
        """
        filtered_matches = []
        try:
            seasons_data = ref.get(etag=False)
            if not seasons_data:
                return filtered_matches

            for season_data in seasons_data.values():
                for league_data in season_data.values():
                    if not isinstance(league_data, dict) or 'fixtures' not in league_data:
                        continue

                    for match in league_data['fixtures'].values():
                        if self._is_h2h_match(match):
                            filtered_matches.append(match)

            logger.info(
                f"H2HFilter: {len(filtered_matches)} matchs trouvés entre équipes "
                f"{self.team1_id} et {self.team2_id} ({self.location.value})"
            )
            return filtered_matches

        except Exception as e:
            logger.error(f"Erreur dans H2HFilter.apply: {str(e)}")
            return filtered_matches

    def _is_h2h_match(self, match: Dict) -> bool:
        """
        Vérifie si un match correspond aux critères H2H.
        
        Args:
            match: Données du match à vérifier
            
        Returns:
            True si le match correspond aux critères, False sinon
        """
        try:
            teams = match.get('teams', {})
            if not teams:
                return False

            home_id = int(teams.get('home', {}).get('id', 0))
            away_id = int(teams.get('away', {}).get('id', 0))

            # Vérifier d'abord si les deux équipes sont impliquées
            teams_match = (
                (home_id == self.team1_id and away_id == self.team2_id) or
                (home_id == self.team2_id and away_id == self.team1_id)
            )

            if not teams_match:
                return False

            # Appliquer les filtres de location si nécessaire
            if self.location == H2HLocation.TEAM1_HOME:
                return home_id == self.team1_id
            elif self.location == H2HLocation.TEAM1_AWAY:
                return away_id == self.team1_id
            else:  # H2HLocation.ANY
                return True

        except Exception as e:
            logger.error(f"Erreur dans _is_h2h_match: {str(e)}")
            return False