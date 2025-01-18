from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from firebase_admin import db
from .filters.factory import FilterFactory
from .h2h_service import H2HService

logger = logging.getLogger(__name__)

class ResultsService:
    """Service pour le calcul des métriques de résultats des matchs."""

    FINISHED_STATUSES = {'FT', 'AET', 'PEN'}

    def __init__(self):
        self.matches_ref = db.reference('matches')
        self.h2h_service = H2HService()

    def get_results(self, **params) -> Dict[str, Any]:
        """
        Calcule les métriques de résultats selon les paramètres fournis.
        """
        try:
            logger.info(f"Calcul des métriques de résultats avec paramètres: {params}")

            # Si H2H demandé, déléguer au H2HService
            if params.get('team1_id') and params.get('team2_id'):
                return self.h2h_service.get_results_stats(**params)

            # Récupération et filtrage initial des matchs
            filter_instance = FilterFactory.create_filter(**params)
            matches = filter_instance.apply(self.matches_ref)
            filtered_matches = self._filter_finished_matches(matches)

            # Si on a un team_id, on filtre d'abord par équipe
            team_id = params.get('team_id')
            if team_id:
                team_id = int(team_id)
                filtered_matches = [m for m in filtered_matches 
                                 if team_id in [m['teams']['home']['id'],
                                              m['teams']['away']['id']]]

            # Ensuite on applique le filtre de séquence
            final_matches = self._apply_sequence_filter(filtered_matches, params)
            logger.info(f"Matches après filtrage complet: {len(final_matches)}")

            if not final_matches:
                return self._build_empty_response(params)

            # Construction de la réponse selon le type
            if team_id:
                results = self._build_team_response(final_matches, team_id)
            else:
                results = self._build_league_response(final_matches)

            results['metadata'] = self._build_metadata(final_matches, params)
            return results

        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {str(e)}", exc_info=True)
            raise

    def _apply_sequence_filter(self, matches: List[Dict], params: Dict[str, Any]) -> List[Dict]:
        """
        Applique les filtres de séquence (last_matches/first_matches).
        Les matchs sont d'abord triés chronologiquement.
        """
        # Tri chronologique
        sorted_matches = sorted(
            matches,
            key=lambda m: datetime.fromisoformat(
                m.get('metadata', {}).get('date', '').replace("Z", "+00:00")
            )
        )

        # Application des limites
        if params.get('last_matches'):
            limit = int(params['last_matches'])
            return sorted_matches[-limit:]  # Prendre les N derniers
        elif params.get('first_matches'):
            limit = int(params['first_matches'])
            return sorted_matches[:limit]  # Prendre les N premiers

        return sorted_matches

    def _filter_finished_matches(self, matches: List[Dict]) -> List[Dict]:
        """Filtre pour ne garder que les matchs terminés."""
        return [
            match for match in matches
            if match.get('metadata', {}).get('status') in self.FINISHED_STATUSES
        ]

    def _build_team_response(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
        """Construit les statistiques pour une équipe."""
        home_matches = [m for m in matches if m['teams']['home']['id'] == team_id]
        away_matches = [m for m in matches if m['teams']['away']['id'] == team_id]

        return {
            "total": self._calculate_aggregate_stats(home_matches + away_matches, team_id),
            "home": self._calculate_position_stats(home_matches, True),
            "away": self._calculate_position_stats(away_matches, False)
        }

    def _build_league_response(self, matches: List[Dict]) -> Dict[str, Any]:
        """Construit les statistiques globales pour une ligue."""
        total_matches = len(matches)
        if total_matches == 0:
            return {"total_matches": 0}

        home_wins = sum(1 for m in matches 
                       if m['score']['fulltime']['home'] > m['score']['fulltime']['away'])
        away_wins = sum(1 for m in matches 
                       if m['score']['fulltime']['home'] < m['score']['fulltime']['away'])
        draws = sum(1 for m in matches 
                   if m['score']['fulltime']['home'] == m['score']['fulltime']['away'])

        return {
            "total_matches": total_matches,
            "results": {
                "home_wins": {
                    "count": home_wins,
                    "percentage": round(home_wins / total_matches * 100, 2)
                },
                "away_wins": {
                    "count": away_wins,
                    "percentage": round(away_wins / total_matches * 100, 2)
                },
                "draws": {
                    "count": draws,
                    "percentage": round(draws / total_matches * 100, 2)
                }
            }
        }

    def _calculate_aggregate_stats(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
        """Calcule les statistiques agrégées pour une équipe."""
        total_matches = len(matches)
        if total_matches == 0:
            return self._get_empty_position_stats()

        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0

        for match in matches:
            is_home = match['teams']['home']['id'] == team_id
            team_score = match['score']['fulltime']['home' if is_home else 'away']
            opp_score = match['score']['fulltime']['away' if is_home else 'home']

            goals_for += team_score
            goals_against += opp_score

            if team_score > opp_score:
                wins += 1
            elif team_score == opp_score:
                draws += 1
            else:
                losses += 1

        points = (wins * 3) + draws

        return {
            "matches": total_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "points": points,
            "win_percentage": round(wins / total_matches * 100, 2),
            "points_per_game": round(points / total_matches, 2)
        }

    def _calculate_position_stats(self, matches: List[Dict], is_home: bool) -> Dict[str, Any]:
        """Calcule les statistiques pour une position spécifique."""
        total_matches = len(matches)
        if total_matches == 0:
            return self._get_empty_position_stats()

        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0

        for match in matches:
            team_score = match['score']['fulltime']['home' if is_home else 'away']
            opp_score = match['score']['fulltime']['away' if is_home else 'home']

            goals_for += team_score
            goals_against += opp_score

            if team_score > opp_score:
                wins += 1
            elif team_score == opp_score:
                draws += 1
            else:
                losses += 1

        points = (wins * 3) + draws

        return {
            "matches": total_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "points": points,
            "win_percentage": round(wins / total_matches * 100, 2) if total_matches > 0 else 0,
            "points_per_game": round(points / total_matches, 2) if total_matches > 0 else 0
        }

    def _build_metadata(self, matches: List[Dict], params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit les métadonnées de la réponse."""
        total_matches = len(matches)

        metadata = {
            'total_matches': total_matches,
            'filters': {
                'applied': list(params.keys()),
                'values': {k: str(v) for k, v in params.items()},
                'description': FilterFactory.get_filter_description(**params)
            },
            'period': self._get_period_info(matches)
        }

        if params.get('league_id'):
            metadata['league'] = self._get_league_info(params['league_id'])

        return metadata

    def _get_league_info(self, league_id: int) -> Dict[str, Any]:
        """Récupère les informations d'une ligue."""
        try:
            seasons = self.matches_ref.get(etag=False)
            if not seasons:
                return {}

            for season_data in seasons.values():
                league_key = f'league_{league_id}'
                if league_key in season_data and 'metadata_league' in season_data[league_key]:
                    league_data = season_data[league_key]['metadata_league']
                    return {
                        'id': league_data.get('id'),
                        'name': league_data.get('name'),
                        'country': league_data.get('country'),
                        'type': league_data.get('type')
                    }
            return {}

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos de la ligue: {e}")
            return {}

    def _get_period_info(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calcule les informations de période pour les matchs."""
        if not matches:
            return {
                "start": None,
                "end": None,
                "start_formatted": None,
                "end_formatted": None
            }

        try:
            timestamps = []
            for match in matches:
                date_str = match.get('metadata', {}).get('date')
                if date_str:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    timestamps.append(dt.timestamp())

            if not timestamps:
                return {
                    "start": None,
                    "end": None,
                    "start_formatted": None,
                    "end_formatted": None
                }

            min_ts = min(timestamps)
            max_ts = max(timestamps)

            return {
                "start": min_ts,
                "end": max_ts,
                "start_formatted": datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d'),
                "end_formatted": datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d')
            }

        except Exception as e:
            logger.error(f"Erreur lors du calcul de la période: {e}")
            return {
                "start": None,
                "end": None,
                "start_formatted": None,
                "end_formatted": None
            }

    def _get_empty_position_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques vides pour une position."""
        return {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
            "win_percentage": 0,
            "points_per_game": 0
        }

    def _build_empty_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit une réponse vide."""
        if params.get('team_id'):
            response = {
                "total": self._get_empty_position_stats(),
                "home": self._get_empty_position_stats(),
                "away": self._get_empty_position_stats()
            }
        else:
            response = {
                "total_matches": 0,
                "results": {
                    "home_wins": {"count": 0, "percentage": 0},
                    "away_wins": {"count": 0, "percentage": 0},
                    "draws": {"count": 0, "percentage": 0}
                }
            }

        response['metadata'] = self._build_metadata([], params)
        return response