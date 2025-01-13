from .metrics.goals import GoalsMetrics
from .results_service import ResultsService
from .filters.factory import FilterFactory
from .filters.team import TeamFilter, TeamLocation
from datetime import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GoalsService(ResultsService):
   def __init__(self):
       super().__init__()
       self.metrics = {
           'clean_sheets': GoalsMetrics.CleanSheetsMetric(),
           'btts': GoalsMetrics.BTTSMetric(),
           'total_goals': GoalsMetrics.TotalGoalsMetric()
       }
       self.thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
       for threshold in self.thresholds:
           key = f'goals_{threshold}'.replace('.', '_')
           self.metrics[key] = GoalsMetrics.GoalsThresholdMetric(threshold)

   def get_results(self, **params) -> Dict[str, Any]:
       try:
           logger.info(f"Calcul des métriques de buts avec paramètres: {params}")

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
           team_id = params.get('team_id')
           if team_id:
               team_filter = TeamFilter(team_id, params.get('location', TeamLocation.ALL))
               if matches:
                   matches = [m for m in matches if team_filter._check_team_position(m)]
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
                       logger.error(f"Erreur lors du filtrage temporel: {e}")
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

           # Calcul des métriques
           results = {}
           for name, metric in self.metrics.items():
               results[name] = metric.calculate(finished_matches, team_id)
               logger.info(f"Métrique {name} calculée")

           # Construction de la réponse
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

           # Ajout des informations de la ligue si nécessaire
           if params.get('league_id'):
               response['metadata']['league'] = self.get_league_info(params['league_id'])

           return response

       except ValueError as e:
           logger.error(f"Erreur de validation: {str(e)}")
           return {"error": str(e)}
       except Exception as e:
           logger.error(f"Erreur lors du calcul des métriques: {str(e)}", exc_info=True)
           raise