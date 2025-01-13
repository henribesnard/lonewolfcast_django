from .base import BaseFilter
from typing import List, Dict, Any
from enum import Enum
from firebase_admin import db
import logging

logger = logging.getLogger(__name__)

class TeamLocation(Enum):
    HOME = 'home'
    AWAY = 'away'
    ALL = 'all'

class TeamFilter(BaseFilter):
    def __init__(self, team_id: int, location: TeamLocation = TeamLocation.ALL):
        """
        Initialise le filtre d'équipe avec l'ID et la position.
        
        Args:
            team_id: ID de l'équipe à filtrer
            location: Position souhaitée (HOME/AWAY/ALL)
        """
        self.team_id = int(team_id)  # Conversion explicite en int
        self.location = location
        logger.info(f"TeamFilter initialisé - team_id: {team_id}, location: {location.value}")

    def apply(self, ref: db.Reference) -> List[Dict]:
        """
        Applique le filtre sur les données Firebase.
        
        Args:
            ref: Référence Firebase vers le nœud des matchs
            
        Returns:
            Liste des matchs filtrés selon les critères
        """
        filtered_matches = []
        try:
            seasons_data = ref.get(etag=False)
            if not seasons_data:
                return filtered_matches

            total_matches = 0
            # Parcours des saisons et ligues
            for season_data in seasons_data.values():
                for league_data in season_data.values():
                    if not isinstance(league_data, dict) or 'fixtures' not in league_data:
                        continue

                    # Pour chaque match, vérifier la condition de position
                    for match in league_data['fixtures'].values():
                        total_matches += 1
                        if self._check_team_position(match):
                            filtered_matches.append(match)

            logger.info(
                f"TeamFilter: {len(filtered_matches)}/{total_matches} matchs pour "
                f"équipe {self.team_id} en {self.location.value}"
            )
            return filtered_matches

        except Exception as e:
            logger.error(f"Erreur dans TeamFilter.apply: {str(e)}")
            return filtered_matches

    def _check_team_position(self, match: Dict) -> bool:
        """
        Vérifie si un match correspond aux critères de position de l'équipe.
        """
        try:
            teams = match.get('teams', {})
            if not teams:
                return False

            # Extraire les IDs des équipes
            home_id = int(teams.get('home', {}).get('id', 0))
            away_id = int(teams.get('away', {}).get('id', 0))

            # Vérifier selon la location demandée
            if self.location == TeamLocation.HOME:
                matches = home_id == self.team_id
            elif self.location == TeamLocation.AWAY:
                matches = away_id == self.team_id
            else:  # ALL
                matches = home_id == self.team_id or away_id == self.team_id

            logger.debug(
                f"Match {match.get('metadata', {}).get('fixture_id')} - "
                f"home: {home_id}, away: {away_id}, matches: {matches}"
            )
            return matches

        except Exception as e:
            logger.error(f"Erreur dans check_team_position: {str(e)}")
            return False