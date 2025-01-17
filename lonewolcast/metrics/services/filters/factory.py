from typing import List, Optional
from .base import BaseFilter, CompositeFilter, NoFilter
from .league import LeagueFilter
from .season import SeasonFilter
from .temporal import YearFilter, MonthFilter
from .match_sequence import LastMatchesFilter, FirstMatchesFilter
from .team import TeamFilter, TeamLocation
from .game_time import GameTimeFilter, GameTimeSlot
from .weekday import WeekdayFilter, Weekday
from .h2h import H2HFilter, H2HLocation
import logging

logger = logging.getLogger(__name__)

class FilterFactory:
    """Factory pour créer et combiner des filtres de manière flexible."""

    @staticmethod
    def create_filter(**params) -> BaseFilter:
        """
        Crée une combinaison de filtres basée sur les paramètres fournis.
        
        Args:
            **params: Paramètres de filtrage incluant:
                - team1_id (int): ID de la première équipe (optionnel)
                - team2_id (int): ID de la deuxième équipe (optionnel)
                - team_id (int): ID d'une équipe unique (optionnel)
                - location (TeamLocation/H2HLocation): Position pour team ou H2H
                - league_id (int): ID de la ligue
                - season (int): Année de la saison
                - year (int): Année civile
                - month (int): Mois (1-12)
                - last_matches (int): N derniers matchs
                - first_matches (int): N premiers matchs
                - game_time (GameTimeSlot): Créneau horaire
                - weekday (Weekday): Jour de la semaine
        
        Returns:
            BaseFilter: Filtre composite combinant tous les critères spécifiés
        """
        filters = []
        try:
            # 1. Gestion des filtres d'équipe(s)
            if params.get('team1_id') and params.get('team2_id'):
                # Filtre H2H
                filters.append(H2HFilter(
                    team1_id=params['team1_id'],
                    team2_id=params['team2_id'],
                    location=params.get('h2h_location', H2HLocation.ANY)
                ))
            elif params.get('team_id'):
                # Filtre équipe unique
                filters.append(TeamFilter(
                    team_id=params['team_id'],
                    location=params.get('location', TeamLocation.ALL)
                ))

            # 2. Filtre de ligue
            if params.get('league_id'):
                filters.append(LeagueFilter(params['league_id']))

            # 3. Filtre de saison
            if params.get('season'):
                filters.append(SeasonFilter(params['season']))

            # 4. Filtres temporels
            if params.get('year'):
                if params.get('month'):
                    filters.append(MonthFilter(params['year'], params['month']))
                else:
                    filters.append(YearFilter(params['year']))

            # 5. Filtres de séquence
            if params.get('last_matches'):
                filters.append(LastMatchesFilter(params['last_matches']))
            elif params.get('first_matches'):
                filters.append(FirstMatchesFilter(params['first_matches']))

            # 6. Filtre de plage horaire
            if params.get('game_time'):
                filters.append(GameTimeFilter(params['game_time']))

            # 7. Filtre de jour de la semaine
            if params.get('weekday'):
                filters.append(WeekdayFilter(params['weekday']))

            return CompositeFilter(filters) if filters else NoFilter()

        except Exception as e:
            logger.error(f"Erreur lors de la création des filtres: {e}")
            return NoFilter()

    @staticmethod
    def validate_params(**params) -> List[str]:
        """
        Valide les paramètres de filtrage et retourne les erreurs éventuelles.
        
        Returns:
            List[str]: Liste des messages d'erreur (vide si tout est valide)
        """
        errors = []

        # Validation de la cohérence des filtres d'équipe
        if params.get('team1_id') and params.get('team2_id'):
            if params.get('team_id'):
                errors.append("Impossible de combiner team_id avec team1_id/team2_id")
            if params.get('team1_id') == params.get('team2_id'):
                errors.append("team1_id et team2_id doivent être différents")

        # Validation des paramètres temporels
        if params.get('month') and not params.get('year'):
            errors.append("Le paramètre month nécessite year")

        # Validation des paramètres de séquence
        if params.get('last_matches') and params.get('first_matches'):
            errors.append("Impossible de combiner last_matches et first_matches")

        return errors

    @staticmethod
    def get_filter_description(**params) -> str:
        """
        Génère une description textuelle des filtres appliqués.
        
        Returns:
            str: Description des filtres actifs
        """
        descriptions = []

        if params.get('team1_id') and params.get('team2_id'):
            h2h_loc = params.get('h2h_location', H2HLocation.ANY)
            descriptions.append(f"Matchs H2H entre équipes {params['team1_id']} et {params['team2_id']} ({h2h_loc.value})")
        elif params.get('team_id'):
            loc = params.get('location', TeamLocation.ALL)
            descriptions.append(f"Matchs de l'équipe {params['team_id']} ({loc.value})")

        if params.get('league_id'):
            descriptions.append(f"Ligue {params['league_id']}")

        if params.get('season'):
            descriptions.append(f"Saison {params['season']}")

        if params.get('year'):
            if params.get('month'):
                descriptions.append(f"Période: {params['month']}/{params['year']}")
            else:
                descriptions.append(f"Année: {params['year']}")

        if params.get('last_matches'):
            descriptions.append(f"{params['last_matches']} derniers matchs")
        elif params.get('first_matches'):
            descriptions.append(f"{params['first_matches']} premiers matchs")

        if not descriptions:
            return "Aucun filtre appliqué"

        return " | ".join(descriptions)