from typing import Dict, Any, Optional
import redis
import json
import hashlib
import logging
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)

class MetricsCacheManager:
    """Gestionnaire de cache pour les métriques de football."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        # TTL par défaut de 1 heure pour les résultats
        self.default_ttl = timedelta(hours=1)
        # TTL plus long pour les données moins volatiles
        self.league_ttl = timedelta(days=1)
        
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Génère une clé de cache unique basée sur l'endpoint et les paramètres."""
        # Trier les paramètres pour assurer la cohérence des clés
        sorted_params = dict(sorted(params.items()))
        # Créer une chaîne représentant les paramètres
        params_str = json.dumps(sorted_params, sort_keys=True)
        # Générer un hash unique
        key_hash = hashlib.sha256(f"{endpoint}:{params_str}".encode()).hexdigest()
        return f"metrics:{endpoint}:{key_hash}"
    
    def get_cached_result(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Récupère un résultat du cache s'il existe."""
        try:
            cache_key = self._generate_cache_key(endpoint, params)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit pour {cache_key}")
                return json.loads(cached_data)
            
            logger.info(f"Cache miss pour {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {e}")
            return None
    
    def cache_result(self, endpoint: str, params: Dict[str, Any], 
                    result: Dict, ttl: Optional[timedelta] = None) -> None:
        """Met en cache un résultat avec TTL configurable."""
        try:
            cache_key = self._generate_cache_key(endpoint, params)
            ttl = ttl or self.default_ttl
            
            self.redis_client.setex(
                cache_key,
                int(ttl.total_seconds()),
                json.dumps(result)
            )
            logger.info(f"Résultat mis en cache pour {cache_key}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {e}")
    
    def invalidate_cache(self, pattern: str = "metrics:*") -> None:
        """Invalide le cache selon un pattern."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"{len(keys)} clés supprimées avec le pattern {pattern}")
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation du cache: {e}")
