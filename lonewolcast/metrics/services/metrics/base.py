from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseMetric(ABC):
    """Classe de base pour toutes les métriques."""
    
    # Statuts des matchs terminés
    FINISHED_STATUSES = {'FT', 'AET', 'PEN'}

    def filter_finished_matches(self, matches: List[Dict]) -> List[Dict]:
        """Ne garde que les matchs terminés."""
        return [
            match for match in matches
            if match.get('fixture', {}).get('status', {}).get('short') in self.FINISHED_STATUSES
        ]

    @abstractmethod
    def calculate(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calcule la métrique sur les matchs terminés uniquement."""
        matches = self.filter_finished_matches(matches)
        pass


