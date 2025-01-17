from .base import BaseFilter
from typing import List, Dict, Any
from enum import Enum
from datetime import datetime, time
from firebase_admin import db

class GameTimeSlot(Enum):
    SLOT_12_14 = 'slot_12_14'  # 12:00-13:59
    SLOT_14_17 = 'slot_14_17'  # 14:00-16:59
    SLOT_17_20 = 'slot_17_20'  # 17:00-19:59
    SLOT_20_23 = 'slot_20_23'  # 20:00-22:59

class GameTimeFilter(BaseFilter):
    """Filtre les matchs par plage horaire."""

    def __init__(self, time_slot: GameTimeSlot):
        self.time_slot = time_slot

    def get_time_range(self, time_slot: GameTimeSlot) -> tuple[time, time]:
        ranges = {
            GameTimeSlot.SLOT_12_14: (time(12, 0), time(13, 59)),
            GameTimeSlot.SLOT_14_17: (time(14, 0), time(16, 59)),
            GameTimeSlot.SLOT_17_20: (time(17, 0), time(19, 59)),
            GameTimeSlot.SLOT_20_23: (time(20, 0), time(22, 59))
        }
        return ranges[time_slot]

    def apply(self, ref: db.Reference) -> List[Dict]:
        start_time, end_time = self.get_time_range(self.time_slot)
        matches = []
        
        seasons = ref.get()
        if not seasons:
            return matches
            
        for season_data in seasons.values():
            for league_data in season_data.values():
                if 'fixtures' in league_data:
                    for match in league_data['fixtures'].values():
                        match_timestamp = match.get('metadata', {}).get('timestamp', 0)
                        match_datetime = datetime.fromtimestamp(match_timestamp)
                        match_time = match_datetime.time()
                        
                        if start_time <= match_time <= end_time:
                            matches.append(match)
        return matches