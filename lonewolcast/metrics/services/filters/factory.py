from typing import List
from .base import BaseFilter, CompositeFilter, NoFilter
from .league import LeagueFilter
from .season import SeasonFilter
from .temporal import YearFilter, MonthFilter
from .match_sequence import LastMatchesFilter, FirstMatchesFilter
from .team import TeamFilter, TeamLocation
from .game_time import GameTimeFilter
from .weekday import WeekdayFilter
import logging

logger = logging.getLogger(__name__)

class FilterFactory:
    """Factory pour créer et combiner des filtres."""

    @staticmethod
    def create_league_scope(**params) -> BaseFilter:
        """
        Crée un filtre pour une ligue et une saison spécifiques.
        
        Args:
            **params: Paramètres optionnels pour le filtrage (league_id, season, etc.)
        
        Returns:
            BaseFilter: Filtre composite basé sur les paramètres.
        """
        filters = []
        try:
            # Ajouter un filtre de ligue si league_id est spécifié
            if params.get('league_id'):
                filters.append(LeagueFilter(params['league_id']))

            # Ajouter un filtre de saison si season est spécifié
            if params.get('season'):
                filters.append(SeasonFilter(params['season']))

            # Ajouter un filtre d'année ou de mois si spécifiés
            if params.get('year'):
                if params.get('month'):
                    filters.append(MonthFilter(params['year'], params['month']))
                else:
                    filters.append(YearFilter(params['year']))

            # Ajouter des filtres spécifiques pour limiter les matchs
            if params.get('last_matches'):
                filters.append(LastMatchesFilter(params['last_matches']))
            elif params.get('first_matches'):
                filters.append(FirstMatchesFilter(params['first_matches']))

            # Ajouter un filtre de plage horaire si spécifié
            if params.get('game_time'):
                filters.append(GameTimeFilter(params['game_time']))

            # Ajouter un filtre par jour de la semaine si spécifié
            if params.get('weekday'):
                filters.append(WeekdayFilter(params['weekday']))

            # Retourner un filtre composite si des filtres existent
            return CompositeFilter(filters) if filters else NoFilter()

        except Exception as e:
            logger.error(f"Erreur lors de la création des filtres de ligue: {e}")
            return NoFilter()

    @staticmethod
    def create_team_scope(team_id: int, location: TeamLocation = TeamLocation.ALL, **params) -> BaseFilter:
        """
        Crée un filtre pour une équipe spécifique avec des paramètres supplémentaires.

        Args:
            team_id (int): ID de l'équipe à filtrer.
            location (TeamLocation): Position (HOME, AWAY ou ALL).
            **params: Autres paramètres de filtrage.
        
        Returns:
            BaseFilter: Filtre composite basé sur les paramètres.
        """
        try:
            filters = []

            # Ajouter le filtre d'équipe en premier
            filters.append(TeamFilter(team_id, location))

            # Ajouter les filtres supplémentaires
            other_filters = FilterFactory.create_league_scope(**params)
            if not isinstance(other_filters, NoFilter):
                filters.append(other_filters)

            # Retourner un filtre composite priorisant l'équipe
            return CompositeFilter(filters)

        except Exception as e:
            logger.error(f"Erreur lors de la création des filtres d'équipe: {e}")
            return CompositeFilter([TeamFilter(team_id, location)])
