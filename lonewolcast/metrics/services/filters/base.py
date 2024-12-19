from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseFilter(ABC):
    """Classe de base abstraite pour tous les filtres."""
    
    @abstractmethod
    def apply(self, matches: List[Dict]) -> List[Dict]:
        """Applique le filtre sur une liste de matchs."""
        pass

    def __and__(self, other: 'BaseFilter') -> 'CompositeFilter':
        """Permet la composition de filtres avec l'opérateur &."""
        return CompositeFilter([self, other])
    
class NoFilter(BaseFilter):
    """Filtre qui retourne tous les matchs sans filtrage."""
    
    def apply(self, matches: List[Dict]) -> List[Dict]:
        return matches

class CompositeFilter(BaseFilter):
    """Permet de combiner plusieurs filtres."""
    
    def __init__(self, filters: List[BaseFilter]):
        self.filters = filters

    def apply(self, matches: List[Dict]) -> List[Dict]:
        filtered_matches = matches
        for filter_instance in self.filters:
            filtered_matches = filter_instance.apply(filtered_matches)
        return filtered_matches