from typing import List, Dict, Any, Optional
from .base import BaseFilter, CompositeFilter, NoFilter
from .league import LeagueFilter
from .season import SeasonFilter
from .temporal import YearFilter, MonthFilter
from .match_sequence import LastMatchesFilter, FirstMatchesFilter
from .team import TeamFilter, TeamLocation
from .game_time import GameTimeFilter, GameTimeSlot
from .weekday import WeekdayFilter, Weekday

class FilterFactory:
    """Factory pour créer des combinaisons de filtres."""
    
    @staticmethod
    def create_league_scope(
        league_id: Optional[int] = None,
        season: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        last_matches: Optional[int] = None,
        first_matches: Optional[int] = None,
        game_time: Optional[GameTimeSlot] = None,
        weekday: Optional[Weekday] = None
    ) -> BaseFilter:
        """Crée une combinaison de filtres pour le scope ligue."""
        filters = []

        if league_id:
            filters.append(LeagueFilter(league_id))
        if season:
            filters.append(SeasonFilter(season))
        if year:
            filters.append(YearFilter(year))
        if month and year:
            filters.append(MonthFilter(year, month))
        if last_matches:
            filters.append(LastMatchesFilter(last_matches))
        if first_matches:
            filters.append(FirstMatchesFilter(first_matches))
        if game_time:
            filters.append(GameTimeFilter(game_time))
        if weekday:
            filters.append(WeekdayFilter(weekday))

        if not filters:
            return NoFilter()
            
        return CompositeFilter(filters)

    @staticmethod
    def create_team_scope(
        team_id: int,
        location: TeamLocation = TeamLocation.ALL,
        league_id: Optional[int] = None,
        season: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        last_matches: Optional[int] = None,
        first_matches: Optional[int] = None,
        game_time: Optional[GameTimeSlot] = None,
        weekday: Optional[Weekday] = None
    ) -> BaseFilter:
        """Crée une combinaison de filtres pour le scope équipe."""
        base_filter = FilterFactory.create_league_scope(
            league_id, season, year, month, last_matches, 
            first_matches, game_time, weekday
        )
        team_filter = TeamFilter(team_id, location)
        
        return CompositeFilter([base_filter, team_filter])