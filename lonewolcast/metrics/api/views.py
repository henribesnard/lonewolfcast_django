from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..services.results_service import ResultsService
from ..services.goals_service import GoalsService
from ..services.filters.team import TeamLocation
from ..services.filters.game_time import GameTimeSlot
from ..services.filters.weekday import Weekday
from ..services.filters.h2h import H2HLocation
from ..services.filters.factory import FilterFactory
from ..cache.decorators import cache_metrics
from datetime import timedelta
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaseMetricsView(APIView):
    """Classe de base pour les vues de métriques."""
    
    permission_classes = [AllowAny]

    def _convert_params(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Convertit les paramètres bruts de la requête."""
        logger.debug(f"Conversion des paramètres bruts: {params}")
        converted = {}

        try:
            # 1. Conversion des paramètres numériques
            self._convert_numeric_params(params, converted)

            # 2. Gestion des paramètres d'équipe(s)
            self._handle_team_params(params, converted)

            # 3. Conversion des enums
            self._convert_enums(params, converted)

            logger.info(f"Paramètres finaux après conversion: {converted}")
            return converted

        except ValueError as e:
            raise ValueError(f"Erreur de conversion des paramètres: {str(e)}")

    def _convert_numeric_params(self, params: Dict[str, str], converted: Dict[str, Any]) -> None:
        """Convertit les paramètres numériques."""
        numeric_params = {
            'team1_id': "ID de l'équipe 1",
            'team2_id': "ID de l'équipe 2",
            'team_id': "ID de l'équipe",
            'league_id': 'ID de la ligue',
            'season': 'Année de la saison',
            'year': 'Année civile',
            'month': 'Mois (1-12)',
            'last_matches': 'Nombre de derniers matchs',
            'first_matches': 'Nombre de premiers matchs'
        }

        for param_name, description in numeric_params.items():
            if params.get(param_name):
                try:
                    value = int(params[param_name])
                    if param_name == 'month' and not 1 <= value <= 12:
                        raise ValueError("Le mois doit être entre 1 et 12")
                    converted[param_name] = value
                except ValueError:
                    raise ValueError(f"Valeur invalide pour {description}")

    def _handle_team_params(self, params: Dict[str, str], converted: Dict[str, Any]) -> None:
        """Gère la conversion des paramètres d'équipe et de position."""
        # Gestion H2H
        if converted.get('team1_id') and converted.get('team2_id'):
            try:
                h2h_location = params.get('h2h_location', 'ANY').upper()
                converted['h2h_location'] = H2HLocation[h2h_location]
            except KeyError:
                valid_locations = [loc.name for loc in H2HLocation]
                raise ValueError(
                    f"Location H2H invalide: {h2h_location}. "
                    f"Valeurs possibles: {', '.join(valid_locations)}"
                )

        # Gestion équipe unique
        elif converted.get('team_id'):
            try:
                location = params.get('location', 'ALL').upper()
                converted['location'] = TeamLocation[location]
            except KeyError:
                valid_locations = [loc.name for loc in TeamLocation]
                raise ValueError(
                    f"Location invalide: {location}. "
                    f"Valeurs possibles: {', '.join(valid_locations)}"
                )

    def _convert_enums(self, params: Dict[str, str], converted: Dict[str, Any]) -> None:
        """Convertit les paramètres enum."""
        # GameTimeSlot
        if params.get('game_time'):
            try:
                converted['game_time'] = GameTimeSlot[params['game_time'].upper()]
            except KeyError:
                valid_slots = [slot.name for slot in GameTimeSlot]
                raise ValueError(
                    f"Créneau horaire invalide. "
                    f"Valeurs possibles: {', '.join(valid_slots)}"
                )

        # Weekday
        if params.get('weekday'):
            try:
                converted['weekday'] = Weekday[params['weekday'].upper()]
            except KeyError:
                valid_days = [day.name for day in Weekday]
                raise ValueError(
                    f"Jour invalide. "
                    f"Valeurs possibles: {', '.join(valid_days)}"
                )

    def _validate_params(self, params: Dict[str, Any]) -> None:
        """Valide les paramètres convertis."""
        # Validation des paramètres obligatoires
        if not any([params.get('league_id'), params.get('team_id'),
                   (params.get('team1_id') and params.get('team2_id'))]):
            raise ValueError(
                "Au moins league_id, team_id ou team1_id/team2_id doit être spécifié"
            )

        # Validation des équipes H2H
        if params.get('team1_id') and params.get('team2_id'):
            if params.get('team_id'):
                raise ValueError("Impossible de combiner team_id avec team1_id/team2_id")
            if params.get('team1_id') == params.get('team2_id'):
                raise ValueError("team1_id et team2_id doivent être différents")

        # Validation temporelle
        if params.get('month') and not params.get('year'):
            raise ValueError("Le paramètre month nécessite year")

        # Validation des séquences
        if params.get('last_matches') and params.get('first_matches'):
            raise ValueError("Impossible de combiner last_matches et first_matches")

class ResultsMetricsView(BaseMetricsView):
    @cache_metrics(endpoint="results")
    def get(self, request):
        try:
            # Conversion et validation des paramètres
            params = self._convert_params(request.query_params.dict())
            self._validate_params(params)

            # Calcul des métriques
            service = ResultsService()
            results = service.get_results(**params)
            
            return Response(results)

        except ValueError as e:
            logger.warning(f"Erreur de validation: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Erreur serveur interne'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GoalsMetricsView(BaseMetricsView):
    @cache_metrics(endpoint="goals", ttl=timedelta(minutes=30))
    def get(self, request):
        try:
            # Conversion et validation des paramètres
            params = self._convert_params(request.query_params.dict())
            self._validate_params(params)

            # Calcul des métriques
            service = GoalsService()
            results = service.get_results(**params)
            
            return Response(results)

        except ValueError as e:
            logger.warning(f"Erreur de validation: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Erreur serveur interne'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )