# metrics/api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from firebase_admin import db
from ..services.results_service import ResultsService
import logging

logger = logging.getLogger(__name__)

class ResultsMetricsView(APIView):
    def get_matches_from_firebase(self):
        """Récupère les matchs de Firebase de manière structurée."""
        matches = []
        matches_ref = db.reference('matches')
        added_matches = set()  
        
        # Récupérer les données
        all_data = matches_ref.get()
        if not all_data:
            return matches

        # Parcourir la structure hiérarchique
        for season_key, season_data in all_data.items():
            if not isinstance(season_data, dict):
                continue

            for league_key, league_data in season_data.items():
                if not isinstance(league_data, dict):
                    continue

                for fixture_key, fixture_data in league_data.items():
                    if not isinstance(fixture_data, dict):
                        continue

                    # Vérifier si c'est bien un match (contient fixture_id)
                    fixture_id = fixture_data.get('metadata', {}).get('fixture_id')
                    if fixture_id and fixture_id not in added_matches:
                        matches.append(fixture_data)
                        added_matches.add(fixture_id)

        logger.info(f"Total des matchs uniques récupérés: {len(matches)}")
        for season in [2022, 2023, 2024]:
            season_matches = [m for m in matches if m.get('league', {}).get('season') == season]
            logger.info(f"Matchs pour la saison {season}: {len(season_matches)}")

        return matches

    def get(self, request):
        try:
            # Récupération des paramètres
            params = {
                'team_id': request.query_params.get('team_id'),
                'location': request.query_params.get('location'),
                'league_id': request.query_params.get('league'),
                'season': request.query_params.get('season'),
                'year': request.query_params.get('year'),
                'month': request.query_params.get('month'),
                'game_time': request.query_params.get('game_time'),
                'weekday': request.query_params.get('weekday'),
                'last_matches': request.query_params.get('last_matches'),
                'first_matches': request.query_params.get('first_matches')
            }

            # Conversion des paramètres numériques
            for key in ['team_id', 'league_id', 'season', 'year', 'month', 'last_matches', 'first_matches']:
                if params[key]:
                    params[key] = int(params[key])

            # Récupération des matchs
            matches = self.get_matches_from_firebase()

            # Calcul des métriques
            service = ResultsService()
            results = service.get_results(matches, **params)

            return Response(results)

        except ValueError as e:
            return Response(
                {'error': 'Paramètres invalides'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erreur: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Erreur serveur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )