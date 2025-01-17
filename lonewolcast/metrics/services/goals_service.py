from typing import Dict, Any, List, Optional
from .results_service import ResultsService
from .h2h_service import H2HService
from datetime import datetime
import logging
from firebase_admin import db
from .filters.factory import FilterFactory

logger = logging.getLogger(__name__)

class GoalsService(ResultsService):
    """Service pour le calcul des métriques de buts."""

    def __init__(self):
        super().__init__()
        self.h2h_service = H2HService()
        self.metrics_thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]

    def get_results(self, **params) -> Dict[str, Any]:
        """
        Calcule les métriques de buts selon les paramètres fournis.
        
        Args:
            **params: Paramètres de filtrage (league_id, team_id, team1_id, team2_id, etc.)
        """
        try:
            logger.info(f"Calcul des métriques de buts avec paramètres: {params}")

            # Si H2H demandé (team1_id et team2_id présents), déléguer au H2HService
            if params.get('team1_id') and params.get('team2_id'):
                return self.h2h_service.get_goals_stats(**params)

            # Récupération et filtrage des matchs
            filter_instance = FilterFactory.create_filter(**params)
            matches = filter_instance.apply(self.matches_ref)
            filtered_matches = self._filter_finished_matches(matches)
            logger.info(f"Matches terminés: {len(filtered_matches)}")

            if not filtered_matches:
                return self._build_empty_response(params)

            # Construction de la réponse selon le type
            if params.get('team_id'):
                results = self._build_team_response(filtered_matches, int(params['team_id']))
            else:
                results = self._build_league_response(filtered_matches)

            results['metadata'] = self._build_metadata(filtered_matches, params)
            return results

        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {str(e)}", exc_info=True)
            raise

    def _build_team_response(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
        """Construit les statistiques de buts pour une équipe."""
        home_matches = [m for m in matches if m['teams']['home']['id'] == team_id]
        away_matches = [m for m in matches if m['teams']['away']['id'] == team_id]

        return {
            "total": self._calculate_team_stats(home_matches + away_matches),
            "home": self._calculate_position_stats(home_matches, True),
            "away": self._calculate_position_stats(away_matches, False),
            "thresholds": self._calculate_thresholds(home_matches + away_matches)
        }

    def _build_league_response(self, matches: List[Dict]) -> Dict[str, Any]:
        """Construit les statistiques de buts pour une ligue."""
        total_matches = len(matches)
        if total_matches == 0:
            return {"total_matches": 0}

        total_goals = sum(m['score']['fulltime']['home'] + m['score']['fulltime']['away'] 
                         for m in matches)
        btts_matches = sum(1 for m in matches 
                          if m['score']['fulltime']['home'] > 0 
                          and m['score']['fulltime']['away'] > 0)
        clean_sheets = sum(1 for m in matches 
                          if m['score']['fulltime']['home'] == 0 
                          or m['score']['fulltime']['away'] == 0)

        return {
            "goals": {
                "total": total_goals,
                "average": round(total_goals / total_matches, 2)
            },
            "btts": {
                "matches": btts_matches,
                "percentage": round(btts_matches / total_matches * 100, 2)
            },
            "clean_sheets": {
                "matches": clean_sheets,
                "percentage": round(clean_sheets / total_matches * 100, 2)
            },
            "thresholds": self._calculate_thresholds(matches)
        }

    def _calculate_team_stats(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calcule les statistiques globales de buts pour une équipe."""
        total_matches = len(matches)
        if total_matches == 0:
            return self._get_empty_team_stats()

        goals_scored = sum(match['score']['fulltime']['home'] for match in matches)
        goals_conceded = sum(match['score']['fulltime']['away'] for match in matches)
        clean_sheets = sum(1 for m in matches if m['score']['fulltime']['away'] == 0)
        failed_to_score = sum(1 for m in matches if m['score']['fulltime']['home'] == 0)
        btts = sum(1 for m in matches 
                  if m['score']['fulltime']['home'] > 0 
                  and m['score']['fulltime']['away'] > 0)

        return {
            "matches": total_matches,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "goals_per_game": round(goals_scored / total_matches, 2),
            "clean_sheets": clean_sheets,
            "clean_sheets_percentage": round(clean_sheets / total_matches * 100, 2),
            "failed_to_score": failed_to_score,
            "failed_to_score_percentage": round(failed_to_score / total_matches * 100, 2),
            "btts": btts,
            "btts_percentage": round(btts / total_matches * 100, 2)
        }

    def _calculate_position_stats(self, matches: List[Dict], is_home: bool) -> Dict[str, Any]:
        """Calcule les statistiques de buts pour une position spécifique."""
        total_matches = len(matches)
        if total_matches == 0:
            return self._get_empty_position_stats()

        goals_scored = sum(m['score']['fulltime']['home' if is_home else 'away'] 
                          for m in matches)
        goals_conceded = sum(m['score']['fulltime']['away' if is_home else 'home'] 
                            for m in matches)
        clean_sheets = sum(1 for m in matches 
                          if m['score']['fulltime']['away' if is_home else 'home'] == 0)
        failed_to_score = sum(1 for m in matches 
                            if m['score']['fulltime']['home' if is_home else 'away'] == 0)
        btts = sum(1 for m in matches 
                  if m['score']['fulltime']['home'] > 0 
                  and m['score']['fulltime']['away'] > 0)

        return {
            "matches": total_matches,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "goals_per_game": round(goals_scored / total_matches, 2),
            "clean_sheets": clean_sheets,
            "clean_sheets_percentage": round(clean_sheets / total_matches * 100, 2),
            "failed_to_score": failed_to_score,
            "failed_to_score_percentage": round(failed_to_score / total_matches * 100, 2),
            "btts": btts,
            "btts_percentage": round(btts / total_matches * 100, 2)
        }

    def _calculate_thresholds(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calcule les statistiques de seuils de buts."""
        total_matches = len(matches)
        if total_matches == 0:
            return {}

        thresholds = {}
        for threshold in self.metrics_thresholds:
            over_matches = sum(
                1 for m in matches
                if m['score']['fulltime']['home'] + m['score']['fulltime']['away'] > threshold
            )

            threshold_key = f"over_{str(threshold).replace('.', '_')}"
            under_key = f"under_{str(threshold).replace('.', '_')}"
            
            thresholds[threshold_key] = {
                "matches": over_matches,
                "percentage": round(over_matches / total_matches * 100, 2)
            }
            thresholds[under_key] = {
                "matches": total_matches - over_matches,
                "percentage": round((total_matches - over_matches) / total_matches * 100, 2)
            }

        return thresholds

    def _get_empty_team_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques vides pour une équipe."""
        return {
            "matches": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "goals_per_game": 0,
            "clean_sheets": 0,
            "clean_sheets_percentage": 0,
            "failed_to_score": 0,
            "failed_to_score_percentage": 0,
            "btts": 0,
            "btts_percentage": 0
        }

    def _get_empty_position_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques vides pour une position."""
        return self._get_empty_team_stats()

    def _build_empty_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit une réponse vide."""
        response = {
            "total": self._get_empty_team_stats(),
            "home": self._get_empty_position_stats(),
            "away": self._get_empty_position_stats(),
            "thresholds": {}
        }
        response['metadata'] = self._build_metadata([], params)
        return response