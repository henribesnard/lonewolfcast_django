from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..services.results_service import ResultsService
from ..services.filters.team import TeamLocation
from ..services.filters.game_time import GameTimeSlot
from ..services.filters.weekday import Weekday
from ..services.goals_service import GoalsService
import logging
from typing import Dict, Any
from ..cache.decorators import cache_metrics
from datetime import timedelta

logger = logging.getLogger(__name__)

class ResultsMetricsView(APIView):
    """Vue API pour les métriques de résultats des matchs."""
    
    permission_classes = [AllowAny]

    def _convert_params(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Convertit les paramètres bruts de la requête en types appropriés."""
        logger.debug(f"Conversion des paramètres bruts: {params}")
        converted = {}
        
        # Conversion des paramètres numériques
        numeric_params = {
            'team_id': 'ID de l\'équipe',
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
                    # Validation supplémentaire pour month
                    if param_name == 'month' and not 1 <= value <= 12:
                        raise ValueError("Le mois doit être entre 1 et 12")
                    converted[param_name] = value
                    logger.debug(f"Paramètre converti - {description}: {value}")
                except ValueError as e:
                    raise ValueError(f"Valeur invalide pour {description}")
        
        # Gestion spécifique de location pour le filtrage par équipe
        if converted.get('team_id'):
            self._handle_team_location(params, converted)
        
        # Conversion des autres paramètres enum
        self._convert_game_time(params, converted)
        self._convert_weekday(params, converted)

        logger.info(f"Paramètres finaux après conversion: {converted}")
        return converted

    def _handle_team_location(self, params: Dict[str, str], converted: Dict[str, Any]) -> None:
        """Gère la conversion du paramètre location pour le filtrage par équipe."""
        try:
            location_str = params.get('location', 'ALL').upper()
            converted['location'] = TeamLocation[location_str]
            logger.debug(f"Location définie à {location_str} pour l'équipe {converted['team_id']}")
        except KeyError:
            valid_locations = [loc.name for loc in TeamLocation]
            raise ValueError(
                f"Location invalide: {params.get('location')}. "
                f"Valeurs possibles: {', '.join(valid_locations)}"
            )

    def _convert_game_time(self, params: Dict[str, str], converted: Dict[str, Any]) -> None:
        """Convertit le paramètre game_time."""
        if params.get('game_time'):
            try:
                converted['game_time'] = GameTimeSlot[params['game_time'].upper()]
                logger.debug(f"Créneau horaire défini: {converted['game_time']}")
            except KeyError:
                valid_slots = [slot.name for slot in GameTimeSlot]
                raise ValueError(
                    f"Créneau horaire invalide: {params['game_time']}. "
                    f"Valeurs possibles: {', '.join(valid_slots)}"
                )

    def _convert_weekday(self, params: Dict[str, str], converted: Dict[str, Any]) -> None:
        """Convertit le paramètre weekday."""
        if params.get('weekday'):
            try:
                converted['weekday'] = Weekday[params['weekday'].upper()]
                logger.debug(f"Jour de semaine défini: {converted['weekday']}")
            except KeyError:
                valid_days = [day.name for day in Weekday]
                raise ValueError(
                    f"Jour invalide: {params['weekday']}. "
                    f"Valeurs possibles: {', '.join(valid_days)}"
                )
    @cache_metrics(endpoint="results")
    def get(self, request):
        try:
            # Log des paramètres reçus
            logger.info(f"Requête reçue - Paramètres: {request.query_params}")
            
            # Conversion des paramètres
            params = self._convert_params(request.query_params.dict())
            
            # Validation des paramètres obligatoires
            if not (params.get('league_id') or params.get('team_id')):
                return Response(
                    {'error': 'Au moins league_id ou team_id doit être spécifié'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validation de month avec year
            if params.get('month') and not params.get('year'):
                return Response(
                    {'error': 'Le paramètre month nécessite year'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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

class GoalsMetricsView(APIView):
    permission_classes = [AllowAny]

    def _convert_params(self, params: Dict[str, str]) -> Dict[str, Any]:
        converted = {}
        
        # Paramètres numériques
        int_params = [
            'team_id', 'league_id', 'season', 'year', 
            'month', 'last_matches', 'first_matches'
        ]
        
        for param in int_params:
            if params.get(param):
                try:
                    converted[param] = int(params[param])
                except ValueError:
                    raise ValueError(f"Le paramètre {param} doit être un nombre")
        
        # Si team_id est présent, ajouter location par défaut si non spécifié
        if converted.get('team_id'):
            try:
                location_str = params.get('location', 'ALL').upper()
                converted['location'] = TeamLocation[location_str]
                logger.debug(f"Location définie à {location_str} pour l'équipe {converted['team_id']}")
            except KeyError:
                raise ValueError(f"Valeur invalide pour location: {params.get('location')}")
        
        # Conversion des autres enums seulement s'ils sont présents
        if params.get('game_time'):
            try:
                converted['game_time'] = GameTimeSlot[params['game_time'].upper()]
            except KeyError:
                raise ValueError(f"Valeur invalide pour game_time: {params['game_time']}")
                
        if params.get('weekday'):
            try:
                converted['weekday'] = Weekday[params['weekday'].upper()]
            except KeyError:
                raise ValueError(f"Valeur invalide pour weekday: {params['weekday']}")

        logger.info(f"Paramètres convertis: {converted}")
        return converted
    
    @cache_metrics(endpoint="goals", ttl=timedelta(minutes=30))
    def get(self, request):
        try:
            params = self._convert_params(request.query_params.dict())
            
            if not (params.get('league_id') or params.get('team_id')):
                return Response(
                    {'error': 'Au moins league_id ou team_id doit être spécifié'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = GoalsService()
            results = service.get_results(**params)
            
            return Response(results)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Erreur serveur interne'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )