from .base import BaseFilter
from typing import List, Dict, Any
from enum import Enum
from datetime import datetime

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

    def apply(self, matches: List[Dict]) -> List[Dict]:
        return [
            match for match in matches
            if datetime.fromtimestamp(
                match.get('fixture', {}).get('timestamp', 0)
            ).weekday() == self.weekday.value
        ]
