from typing import Dict, Any, List
from .filters.factory import FilterFactory
from .metrics.results import ResultMetrics
from .metrics.base import BaseMetric
from .filters.team import TeamFilter, TeamLocation
from datetime import datetime
import logging
from firebase_admin import db

logger = logging.getLogger(__name__)

class ResultsService:
    def __init__(self):
        self.metrics = {
            'home_wins': ResultMetrics.HomeWinsMetric(),
            'away_wins': ResultMetrics.AwayWinsMetric(),
            'draws': ResultMetrics.DrawsMetric()
        }
        self.matches_ref = db.reference('matches')

    def get_league_info(self, league_id: int) -> Dict[str, Any]:
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

    def sort_matches_by_date(self, matches: List[Dict], reverse: bool = True) -> List[Dict]:
        try:
            return sorted(
                matches,
                key=lambda m: datetime.fromisoformat(
                    m.get('metadata', {}).get('date', '').replace("Z", "+00:00")
                ),
                reverse=reverse
            )
        except Exception as e:
            logger.error(f"Erreur lors du tri des matchs: {e}")
            return matches

    def filter_finished_matches(self, matches: List[Dict]) -> List[Dict]:
        return [
            match for match in matches
            if match.get('metadata', {}).get('status') in BaseMetric.FINISHED_STATUSES
        ]

    def _get_period_info(self, matches: List[Dict]) -> Dict[str, Any]:
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

    def get_results(self, **params) -> Dict[str, Any]:
        try:
            logger.info(f"Calcul des métriques avec paramètres: {params}")

            if not params.get('league_id') and not params.get('team_id'):
                raise ValueError("Au moins league_id ou team_id doit être spécifié")

            matches = []

            # Étape 1: Filtres principaux (league_id et season)
            main_params = {
                k: v for k, v in params.items() 
                if k in ['league_id', 'season']
            }
            if main_params:
                league_filter = FilterFactory.create_league_scope(**main_params)
                matches = league_filter.apply(self.matches_ref)
                logger.info(f"Matches après filtres principaux: {len(matches)}")

            # Étape 2: Filtre d'équipe
            if params.get('team_id'):
                location = params.get('location', TeamLocation.ALL)
                team_filter = TeamFilter(params['team_id'], location)
                
                if matches:
                    filtered_matches = [
                        match for match in matches if team_filter._check_team_position(match)
                    ]
                    matches = filtered_matches
                else:
                    matches = team_filter.apply(self.matches_ref)
                
                logger.info(f"Matches après filtre équipe: {len(matches)}")

            # Étape 3: Filtres temporels
            if params.get('year'):
                year = int(params['year'])
                filtered_matches = []
                for match in matches:
                    try:
                        date_str = match.get('metadata', {}).get('date', '')
                        if date_str:
                            match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if match_date.year == year:
                                if params.get('month') and match_date.month == int(params['month']):
                                    filtered_matches.append(match)
                                elif not params.get('month'):
                                    filtered_matches.append(match)
                    except Exception as e:
                        logger.error(f"Erreur lors du filtrage temporel d'un match: {e}")
                        continue

                matches = filtered_matches
                logger.info(f"Matches après filtres temporels: {len(matches)}")

            # Étape 4: Autres filtres
            other_params = {
                k: v for k, v in params.items() 
                if k in ['game_time', 'weekday']
            }
            if other_params:
                other_filter = FilterFactory.create_league_scope(**other_params)
                other_matches = other_filter.apply(self.matches_ref)
                matches = [m for m in matches if any(
                    om['metadata']['fixture_id'] == m['metadata']['fixture_id']
                    for om in other_matches
                )]
                logger.info(f"Matches après autres filtres: {len(matches)}")

            # Étape 5: Filtres de séquence
            if params.get('last_matches'):
                matches = self.sort_matches_by_date(matches, reverse=True)[:params['last_matches']]
                logger.info(f"Matches après last_matches: {len(matches)}")
            elif params.get('first_matches'):
                matches = self.sort_matches_by_date(matches, reverse=False)[:params['first_matches']]
                logger.info(f"Matches après first_matches: {len(matches)}")

            # Étape 6: Filtrage des matchs terminés
            finished_matches = self.filter_finished_matches(matches)
            logger.info(f"Matches terminés: {len(finished_matches)}")

            # Étape 7: Calcul des métriques
            results = {}
            for name, metric in self.metrics.items():
                results[name] = metric.calculate(finished_matches)
                logger.info(f"Métrique {name}: {results[name]}")

            response = {
                **results,
                'metadata': {
                    'total_matches': len(finished_matches),
                    'filters': {
                        'applied': list(params.keys()),
                        'values': {k: str(v) for k, v in params.items()}
                    },
                    'period': self._get_period_info(finished_matches)
                }
            }

            if params.get('league_id'):
                response['metadata']['league'] = self.get_league_info(params['league_id'])

            return response

        except ValueError as e:
            logger.error(f"Erreur de validation: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {str(e)}", exc_info=True)
            raise
