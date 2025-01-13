from typing import List, Dict, Any
from .base import BaseMetric

class ResultMetrics:
    class HomeWinsMetric(BaseMetric):
        def calculate(self, matches: List[Dict]) -> Dict[str, Any]:
            matches = self.filter_finished_matches(matches)
            
            if not matches:
                return {
                    "count": 0,
                    "total_matches": 0,
                    "percentage": 0.0
                }

            total_matches = len(matches)
            home_wins = sum(
                1 for match in matches
                if match.get('score', {}).get('fulltime', {}).get('home', 0) > 
                   match.get('score', {}).get('fulltime', {}).get('away', 0)
            )

            return {
                "count": home_wins,
                "total_matches": total_matches,
                "percentage": round((home_wins / total_matches) * 100, 2)
            }

    class AwayWinsMetric(BaseMetric):
        def calculate(self, matches: List[Dict]) -> Dict[str, Any]:
            matches = self.filter_finished_matches(matches)
            
            if not matches:
                return {
                    "count": 0,
                    "total_matches": 0,
                    "percentage": 0.0
                }

            total_matches = len(matches)
            away_wins = sum(
                1 for match in matches
                if match.get('score', {}).get('fulltime', {}).get('away', 0) > 
                   match.get('score', {}).get('fulltime', {}).get('home', 0)
            )

            return {
                "count": away_wins,
                "total_matches": total_matches,
                "percentage": round((away_wins / total_matches) * 100, 2)
            }

    class DrawsMetric(BaseMetric):
        def calculate(self, matches: List[Dict]) -> Dict[str, Any]:
            matches = self.filter_finished_matches(matches)
            
            if not matches:
                return {
                    "count": 0,
                    "total_matches": 0,
                    "percentage": 0.0
                }

            total_matches = len(matches)
            draws = sum(
                1 for match in matches
                if match.get('score', {}).get('fulltime', {}).get('home', 0) == 
                   match.get('score', {}).get('fulltime', {}).get('away', 0)
            )

            return {
                "count": draws,
                "total_matches": total_matches,
                "percentage": round((draws / total_matches) * 100, 2)
            }
