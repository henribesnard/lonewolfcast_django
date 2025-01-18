from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from firebase_admin import db
from .filters.h2h import H2HLocation

logger = logging.getLogger(__name__)

class H2HService:
    """Service pour l'analyse des confrontations directes entre équipes."""

    FINISHED_STATUSES = {'FT', 'AET', 'PEN'}

    def __init__(self):
        self.matches_ref = db.reference('matches')

    def get_results_stats(self, **params) -> Dict[str, Any]:
        """Récupère les statistiques complètes de résultats H2H."""
        try:
            logger.info(f"Calcul des statistiques H2H (résultats) avec paramètres: {params}")
            matches = self._get_h2h_matches(params)
            
            if not matches:
                return self._build_empty_response('results', params)

            return self._build_results_response(matches, params)

        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques H2H (résultats): {str(e)}", exc_info=True)
            raise

    def get_goals_stats(self, **params) -> Dict[str, Any]:
        """Récupère les statistiques complètes de buts H2H."""
        try:
            logger.info(f"Calcul des statistiques H2H (buts) avec paramètres: {params}")
            matches = self._get_h2h_matches(params)
            
            if not matches:
                return self._build_empty_response('goals', params)

            return self._build_goals_response(matches, params)

        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques H2H (buts): {str(e)}", exc_info=True)
            raise

    def _get_h2h_matches(self, params: Dict[str, Any]) -> List[Dict]:
        """Récupère les matchs H2H filtrés."""
        try:
            team1_id = int(params['team1_id'])
            team2_id = int(params['team2_id'])
            h2h_location = params.get('h2h_location')

            # Convertir la chaîne en enum si nécessaire
            if isinstance(h2h_location, str):
                try:
                    location = H2HLocation[h2h_location]
                except KeyError:
                    location = H2HLocation.ANY
            elif h2h_location is None:
                location = H2HLocation.ANY
            else:
                location = h2h_location

            logger.info(f"Récupération des matchs H2H entre {team1_id} et {team2_id} avec location: {location.value}")

            # Récupérer tous les matchs
            matches = []
            seasons_data = self.matches_ref.get(etag=False) or {}
            
            for season_data in seasons_data.values():
                for league_data in season_data.values():
                    if not isinstance(league_data, dict) or 'fixtures' not in league_data:
                        continue

                    for match in league_data['fixtures'].values():
                        if match.get('metadata', {}).get('status') not in self.FINISHED_STATUSES:
                            continue

                        home_id = match['teams']['home']['id']
                        away_id = match['teams']['away']['id']

                        # Vérifier la configuration selon l'enum
                        if location == H2HLocation.TEAM1_HOME:
                            if not (home_id == team1_id and away_id == team2_id):
                                continue
                        elif location == H2HLocation.TEAM1_AWAY:
                            if not (home_id == team2_id and away_id == team1_id):
                                continue
                        else:  # H2HLocation.ANY
                            if not ((home_id == team1_id and away_id == team2_id) or
                                   (home_id == team2_id and away_id == team1_id)):
                                continue

                        matches.append(match)

            matches_count = len(matches)
            logger.info(f"Matchs H2H trouvés pour {location.value}: {matches_count}")
            
            # Tri chronologique
            return sorted(matches, key=lambda m: m['metadata']['date'])

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des matchs H2H: {e}")
            return []

    def _build_results_response(self, matches: List[Dict], params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit la réponse pour les statistiques de résultats H2H."""
        team1_id = int(params['team1_id'])
        team2_id = int(params['team2_id'])
        total_matches = len(matches)

        team1_stats = self._calculate_team_stats(matches, team1_id)
        team2_stats = self._calculate_team_stats(matches, team2_id)

        return {
            "head_to_head": {
                "total_matches": total_matches,
                "team1_stats": team1_stats,
                "team2_stats": team2_stats
            },
            "metadata": self._build_metadata(matches, params)
        }

    def _build_goals_response(self, matches: List[Dict], params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit la réponse pour les statistiques de buts H2H."""
        team1_id = int(params['team1_id'])
        team2_id = int(params['team2_id'])
        total_matches = len(matches)

        team1_stats = self._calculate_team_goals_stats(matches, team1_id)
        team2_stats = self._calculate_team_goals_stats(matches, team2_id)

        btts_matches = sum(1 for m in matches 
                          if m['score']['fulltime']['home'] > 0 
                          and m['score']['fulltime']['away'] > 0)
        
        return {
            "head_to_head": {
                "total_matches": total_matches,
                "team1_stats": team1_stats,
                "team2_stats": team2_stats,
                "overall": {
                    "btts": {
                        "matches": btts_matches,
                        "percentage": round(btts_matches / total_matches * 100, 2) if total_matches > 0 else 0
                    },
                    "thresholds": self._calculate_thresholds(matches)
                }
            },
            "metadata": self._build_metadata(matches, params)
        }

    def _calculate_team_stats(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
        """Calcule les statistiques de résultats pour une équipe."""
        total_matches = len(matches)
        if total_matches == 0:
            return self._get_empty_team_stats()

        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        home_wins = 0
        away_wins = 0

        for match in matches:
            is_home = match['teams']['home']['id'] == team_id
            team_score = match['score']['fulltime']['home' if is_home else 'away']
            opp_score = match['score']['fulltime']['away' if is_home else 'home']

            goals_for += team_score
            goals_against += opp_score

            if team_score > opp_score:
                wins += 1
                if is_home:
                    home_wins += 1
                else:
                    away_wins += 1
            elif team_score == opp_score:
                draws += 1
            else:
                losses += 1

        return {
            "total": {
                "matches": total_matches,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "win_percentage": round(wins / total_matches * 100, 2) if total_matches > 0 else 0,
                "home_wins": home_wins,
                "away_wins": away_wins
            },
            "goals": {
                "for": goals_for,
                "against": goals_against,
                "average_for": round(goals_for / total_matches, 2) if total_matches > 0 else 0,
                "average_against": round(goals_against / total_matches, 2) if total_matches > 0 else 0
            }
        }

    def _calculate_team_goals_stats(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
        """Calcule les statistiques de buts pour une équipe."""
        total_matches = len(matches)
        if total_matches == 0:
            return self._get_empty_goals_stats()

        goals_scored = 0
        goals_conceded = 0
        clean_sheets = 0
        failed_to_score = 0

        for match in matches:
            is_home = match['teams']['home']['id'] == team_id
            team_score = match['score']['fulltime']['home' if is_home else 'away']
            opp_score = match['score']['fulltime']['away' if is_home else 'home']

            goals_scored += team_score
            goals_conceded += opp_score

            if opp_score == 0:
                clean_sheets += 1
            if team_score == 0:
                failed_to_score += 1

        return {
            "total": {
                "matches": total_matches,
                "goals_scored": goals_scored,
                "goals_conceded": goals_conceded,
                "clean_sheets": clean_sheets,
                "failed_to_score": failed_to_score,
                "average_scored": round(goals_scored / total_matches, 2),
                "average_conceded": round(goals_conceded / total_matches, 2),
                "clean_sheet_percentage": round(clean_sheets / total_matches * 100, 2),
                "failed_to_score_percentage": round(failed_to_score / total_matches * 100, 2)
            }
        }

    def _calculate_thresholds(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calcule les statistiques de seuils de buts."""
        thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
        total_matches = len(matches)
        
        if total_matches == 0:
            return {}

        results = {}
        for threshold in thresholds:
            over_count = sum(
                1 for m in matches
                if m['score']['fulltime']['home'] + m['score']['fulltime']['away'] > threshold
            )

            results[f"over_{str(threshold).replace('.', '_')}"] = {
                "matches": over_count,
                "percentage": round(over_count / total_matches * 100, 2)
            }
            results[f"under_{str(threshold).replace('.', '_')}"] = {
                "matches": total_matches - over_count,
                "percentage": round((total_matches - over_count) / total_matches * 100, 2)
            }

        return results

    def _build_metadata(self, matches: List[Dict], params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit les métadonnées."""
        # Traiter l'enum H2HLocation correctement
        h2h_location = params.get('h2h_location')
        if h2h_location:
            location_str = h2h_location.value if hasattr(h2h_location, 'value') else str(h2h_location)
        else:
            location_str = 'any'

        return {
            'total_matches': len(matches),
            'filters': {
                'applied': list(params.keys()),
                'values': {k: str(v) for k, v in params.items()},
                'description': f"Matchs H2H entre équipes {params['team1_id']} et {params['team2_id']} ({location_str.lower()})"
            },
            'period': self._get_period_info(matches)
        }

    def _get_period_info(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calcule les informations de période."""
        if not matches:
            return {
                "start": None,
                "end": None,
                "start_formatted": None,
                "end_formatted": None
            }

        try:
            timestamps = [
                datetime.fromisoformat(m.get('metadata', {}).get('date', '').replace("Z", "+00:00")).timestamp()
                for m in matches
                if m.get('metadata', {}).get('date')
            ]

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

    def _get_empty_team_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques vides pour une équipe."""
        return {
            "total": {
                "matches": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "win_percentage": 0,
                "home_wins": 0,
                "away_wins": 0
            },
            "goals": {
                "for": 0,
                "against": 0,
                "average_for": 0,
                "average_against": 0
            }
        }

    def _get_empty_goals_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de buts vides."""
        return {
            "total": {
                "matches": 0,
                "goals_scored": 0,
                "goals_conceded": 0,
                "clean_sheets": 0,
                "failed_to_score": 0,
                "average_scored": 0,
                "average_conceded": 0,
                "clean_sheet_percentage": 0,
                "failed_to_score_percentage": 0
            }
        }

    def _build_empty_response(self, stats_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Construit une réponse vide selon le type de statistiques."""
        if stats_type == 'goals':
            empty_stats = self._get_empty_goals_stats()
        else:
            empty_stats = self._get_empty_team_stats()

        return {
            "head_to_head": {
                "total_matches": 0,
                "team1_stats": empty_stats,
                "team2_stats": empty_stats,
                "overall": {
                    "btts": {"matches": 0, "percentage": 0},
                    "thresholds": {}
                } if stats_type == 'goals' else {}
            },
            "metadata": self._build_metadata([], params)
        }