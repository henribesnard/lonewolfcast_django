from datetime import datetime
from typing import List, Dict, Any
from .base import BaseFilter
import logging

logger = logging.getLogger(__name__)

class YearFilter(BaseFilter):
    """Filtre les matchs par année civile."""
    
    def __init__(self, year: int):
        self.year = year

    def apply(self, matches: List[Dict]) -> List[Dict]:
        unique_matches = {}  
        
        for match in matches:
            try:
                fixture_id = match['fixture']['id']
                timestamp = match['fixture']['timestamp']
                match_date = datetime.fromtimestamp(timestamp)
                
                if match_date.year == self.year:
                    # On garde le match uniquement s'il n'existe pas déjà
                    if fixture_id not in unique_matches:
                        unique_matches[fixture_id] = match
                    else:
                        logger.warning(f"Match dupliqué ignoré - ID: {fixture_id}, Date: {match_date}")
                        
            except KeyError as e:
                logger.error(f"Structure de match invalide: {e}")
            except Exception as e:
                logger.error(f"Erreur lors du filtrage: {e}")

        filtered_matches = list(unique_matches.values())
        logger.info(f"YearFilter: {len(matches)} matchs -> {len(filtered_matches)} matchs uniques pour {self.year}")
        return filtered_matches


class MonthFilter(BaseFilter):
    """Filtre les matchs par mois d'une année."""
    
    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month

    def apply(self, matches: List[Dict]) -> List[Dict]:
        unique_matches = {}  # Utilisation d'un dict pour éviter les doublons
        
        for match in matches:
            try:
                fixture_id = match['fixture']['id']
                timestamp = match['fixture']['timestamp']
                match_date = datetime.fromtimestamp(timestamp)
                
                if (match_date.year == self.year and match_date.month == self.month):
                    # On garde le match uniquement s'il n'existe pas déjà
                    if fixture_id not in unique_matches:
                        unique_matches[fixture_id] = match
                    else:
                        logger.warning(f"Match dupliqué ignoré - ID: {fixture_id}, Date: {match_date}")
                        
            except KeyError as e:
                logger.error(f"Structure de match invalide: {e}")
            except Exception as e:
                logger.error(f"Erreur lors du filtrage: {e}")

        filtered_matches = list(unique_matches.values())
        logger.info(f"MonthFilter: {len(matches)} matchs -> {len(filtered_matches)} matchs uniques pour {self.month}/{self.year}")
        return filtered_matches