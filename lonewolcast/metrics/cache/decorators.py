from functools import wraps
from typing import Callable, Dict, Any, Optional
from .managers import MetricsCacheManager
from datetime import timedelta

def cache_metrics(endpoint: str, ttl: Optional[timedelta] = None):
    """Décorateur pour mettre en cache les résultats des métriques."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = MetricsCacheManager()
            
            # Extraire les paramètres pertinents pour le cache
            if hasattr(args[0], 'request'):  # Pour les vues Django
                params = args[0].request.query_params.dict()
            else:
                params = kwargs
            
            # Vérifier le cache
            cached_result = cache_manager.get_cached_result(endpoint, params)
            if cached_result is not None:
                return cached_result
            
            # Exécuter la fonction si pas de cache
            result = func(*args, **kwargs)
            
            # Mettre en cache le résultat
            cache_manager.cache_result(endpoint, params, result, ttl)
            
            return result
        return wrapper
    return decorator