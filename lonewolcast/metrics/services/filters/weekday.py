from .base import BaseFilter
from typing import List, Dict, Any
from enum import Enum
from datetime import datetime
from firebase_admin import db
import logging

logger = logging.getLogger(__name__)

class Weekday(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

class WeekdayFilter(BaseFilter):
    """Filtre les matchs par jour de la semaine."""

    def __init__(self, weekday: Weekday):
        self.weekday = weekday

    def apply(self, ref: db.Reference) -> List[Dict]:
        matches = []
        try:
            seasons = ref.get()
            if not seasons:
                return matches

            for season_data in seasons.values():
                for league_data in season_data.values():
                    if 'fixtures' not in league_data:
                        continue

                    for match in league_data['fixtures'].values():
                        date_str = match.get('metadata', {}).get('date')
                        if not date_str:
                            continue

                        try:
                            match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if match_date.weekday() == self.weekday.value:
                                matches.append(match)
                        except Exception as e:
                            logger.error(f"Erreur lors du traitement de la date : {e}")
                            continue

            logger.info(f"WeekdayFilter: {len(matches)} matchs trouvés pour {self.weekday.name}")
            return matches

        except Exception as e:
            logger.error(f"Erreur lors du filtrage par jour de la semaine: {e}")
            return matches
