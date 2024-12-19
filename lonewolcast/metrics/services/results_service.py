from typing import List, Dict, Any, Optional
from .filters.factory import FilterFactory
from .metrics.results import ResultMetrics
from .metrics.base import BaseMetric
import logging

logger = logging.getLogger(__name__)

class ResultsService:
    """Service pour calculer les métriques de résultats avec filtres."""

    def __init__(self):
        self.metrics = {
            'home_wins': ResultMetrics.HomeWinsMetric(),
            'away_wins': ResultMetrics.AwayWinsMetric(),
            'draws': ResultMetrics.DrawsMetric()
        }

    def debug_matches_info(self, matches: List[Dict], stage: str = ""):
        """Log les informations de debug sur les matchs."""
        logger.info(f"{stage} - Nombre de matchs: {len(matches)}")
        if matches:
            example = matches[0]
            logger.info(f"  League ID: {example.get('league', {}).get('id')}")
            logger.info(f"  Status: {example.get('fixture', {}).get('status', {}).get('short')}")
            logger.info(f"  Score: {example.get('score', {}).get('fulltime', {})}")

    def get_finished_matches(self, matches: List[Dict]) -> List[Dict]:
        """Ne garde que les matchs terminés."""
        return [
            match for match in matches
            if match.get('fixture', {}).get('status', {}).get('short') in BaseMetric.FINISHED_STATUSES
        ]

    def get_results(
        self,
        matches: List[Dict],
        team_id: Optional[int] = None,
        location: Optional[str] = None,
        league_id: Optional[int] = None,
        season: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        game_time: Optional[str] = None,
        weekday: Optional[str] = None,
        last_matches: Optional[int] = None,
        first_matches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calcule les métriques de résultats sur les matchs filtrés.
        L'ordre d'application des filtres est important :
        1. Filtres de base (league, season, etc.)
        2. Filtre des matchs terminés
        3. Filtres de séquence (last_matches, first_matches)
        """
        # Log initial
        self.debug_matches_info(matches, "INITIAL")

        # Création du filtre sans les filtres de séquence
        params_without_sequence = {
            'team_id': team_id,
            'location': location,
            'league_id': league_id,
            'season': season,
            'year': year,
            'month': month,
            'game_time': game_time,
            'weekday': weekday
        }
        
        # Retirer les paramètres None
        params_without_sequence = {k: v for k, v in params_without_sequence.items() if v is not None}

        # Application des filtres de base
        if team_id:
            filter_instance = FilterFactory.create_team_scope(**params_without_sequence)
        else:
            filter_instance = FilterFactory.create_league_scope(**params_without_sequence)

        filtered_matches = filter_instance.apply(matches)
        self.debug_matches_info(filtered_matches, "APRÈS FILTRES DE BASE")

        # Filtrer les matchs terminés
        finished_matches = self.get_finished_matches(filtered_matches)
        self.debug_matches_info(finished_matches, "APRÈS FILTRE MATCHS TERMINÉS")

        # Application des filtres de séquence si nécessaire
        sequence_filtered_matches = finished_matches
        if last_matches:
            sequence_filtered_matches = sorted(
                finished_matches,
                key=lambda x: x['fixture']['timestamp'],
                reverse=True
            )[:last_matches]
        elif first_matches:
            sequence_filtered_matches = sorted(
                finished_matches,
                key=lambda x: x['fixture']['timestamp']
            )[:first_matches]

        self.debug_matches_info(sequence_filtered_matches, "APRÈS FILTRES DE SÉQUENCE")

        # Calcul des métriques
        results = {}
        for name, metric in self.metrics.items():
            results[name] = metric.calculate(sequence_filtered_matches)
            logger.info(f"Métrique {name}: {results[name]}")

        # Ajout du nombre total de matchs
        results['total_matches'] = len(sequence_filtered_matches)

        return results