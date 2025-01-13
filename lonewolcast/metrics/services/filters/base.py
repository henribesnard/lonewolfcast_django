from abc import ABC, abstractmethod
from typing import List, Dict
from firebase_admin import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseFilter(ABC):
    """Classe de base abstraite pour tous les filtres."""
    
    FINISHED_STATUSES = {'FT', 'AET', 'PEN'}  # Statuts des matchs terminés
    
    @abstractmethod
    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        """
        Applique le filtre sur une référence Firebase.
        Args:
            matches_ref: Référence Firebase vers le nœud 'matches'.
        Returns:
            Liste des matchs filtrés.
        """
        pass

    def filter_finished_matches(self, matches: List[Dict]) -> List[Dict]:
        """Filtre pour ne garder que les matchs terminés."""
        return [
            match for match in matches
            if match.get('metadata', {}).get('status') in self.FINISHED_STATUSES
        ]

    def __and__(self, other: 'BaseFilter') -> 'CompositeFilter':
        """Permet la composition de filtres avec l'opérateur &."""
        return CompositeFilter([self, other])

class NoFilter(BaseFilter):
    """Filtre qui retourne tous les matchs terminés sans autre filtrage."""
    
    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            seasons_data = matches_ref.get(etag=False)
            if not seasons_data:
                return matches

            for season_data in seasons_data.values():
                for league_data in season_data.values():
                    if isinstance(league_data, dict) and 'fixtures' in league_data:
                        matches.extend(league_data['fixtures'].values())

            return self.filter_finished_matches(matches)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des matchs: {e}")
            return matches

class CompositeFilter(BaseFilter):
    """Permet de combiner plusieurs filtres."""
    
    def __init__(self, filters: List[BaseFilter]):
        self.filters = filters

    def apply(self, matches_ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            season_filter = next((f for f in self.filters if f.__class__.__name__ == 'SeasonFilter'), None)
            league_filter = next((f for f in self.filters if f.__class__.__name__ == 'LeagueFilter'), None)
            other_filters = [f for f in self.filters if f not in (season_filter, league_filter)]

            seasons_data = matches_ref.get(etag=False) or {}

            for season_id, season_data in seasons_data.items():
                if season_filter:
                    season_num = int(season_id.split('_')[1])
                    if season_num != season_filter.season:
                        continue

                for league_key, league_data in season_data.items():
                    if league_filter:
                        if league_key != f'league_{league_filter.league_id}':
                            continue

                    if 'fixtures' in league_data:
                        matches.extend(league_data['fixtures'].values())

            matches = self.filter_finished_matches(matches)

            for filter_instance in other_filters:
                matches = [m for m in matches if self._match_passes_filter(m, filter_instance)]

            logger.debug(f"Nombre de matchs terminés après filtrage: {len(matches)}")
            return matches
        except Exception as e:
            logger.error(f"Erreur lors de l'application des filtres composites: {e}")
            return []

    def _match_passes_filter(self, match: Dict, filter_instance: BaseFilter) -> bool:
        try:
            filter_name = filter_instance.__class__.__name__

            match_date_str = match.get('metadata', {}).get('date')
            if not match_date_str:
                return False

            # Conversion de la date ISO 8601 en objet datetime
            match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))

            if filter_name == 'YearFilter':
                return match_date.year == filter_instance.year

            if filter_name == 'MonthFilter':
                return match_date.year == filter_instance.year and match_date.month == filter_instance.month

            if filter_name == 'WeekdayFilter':
                return match_date.weekday() == filter_instance.weekday.value

            if filter_name == 'GameTimeFilter':
                match_time = match_date.time()
                start_time, end_time = filter_instance.get_time_range(filter_instance.time_slot)
                return start_time <= match_time <= end_time

            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du filtre {filter_instance.__class__.__name__}: {e}")
            return False
