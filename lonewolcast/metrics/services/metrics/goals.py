from typing import List, Dict, Any
from .base import BaseMetric

class GoalsMetrics:
   class CleanSheetsMetric(BaseMetric):
       def calculate(self, matches: List[Dict], team_id: int = None) -> Dict[str, Any]:
           matches = self.filter_finished_matches(matches)
           if not matches:
               return {"count": 0, "total_matches": 0, "percentage": 0.0}

           if team_id:
               total_matches = len(matches)
               team_clean_sheets = {
                   "total": {
                       "kept": sum(1 for m in matches if self._team_kept_clean_sheet(m, team_id)),
                       "conceded": sum(1 for m in matches if not self._team_kept_clean_sheet(m, team_id))
                   },
                   "home": {
                       "kept": sum(1 for m in matches 
                           if m['teams']['home']['id'] == team_id and 
                           m['score']['fulltime']['away'] == 0),
                       "conceded": sum(1 for m in matches 
                           if m['teams']['home']['id'] == team_id and 
                           m['score']['fulltime']['away'] > 0)
                   },
                   "away": {
                       "kept": sum(1 for m in matches 
                           if m['teams']['away']['id'] == team_id and 
                           m['score']['fulltime']['home'] == 0),
                       "conceded": sum(1 for m in matches 
                           if m['teams']['away']['id'] == team_id and 
                           m['score']['fulltime']['home'] > 0)
                   }
               }
               clean_sheets = team_clean_sheets["total"]["kept"]
           else:
               total_matches = len(matches)
               clean_sheets = sum(
                   1 for match in matches
                   if match.get('score', {}).get('fulltime', {}).get('home', 0) == 0 or
                      match.get('score', {}).get('fulltime', {}).get('away', 0) == 0
               )

           response = {
               "count": clean_sheets,
               "total_matches": total_matches,
               "percentage": round((clean_sheets / total_matches) * 100, 2)
           }

           if team_id:
               response["details"] = team_clean_sheets

           return response

       def _team_kept_clean_sheet(self, match: Dict, team_id: int) -> bool:
           is_home = match['teams']['home']['id'] == team_id
           return (is_home and match['score']['fulltime']['away'] == 0) or \
                  (not is_home and match['score']['fulltime']['home'] == 0)

   class BTTSMetric(BaseMetric):
       def calculate(self, matches: List[Dict], team_id: int = None) -> Dict[str, Any]:
           matches = self.filter_finished_matches(matches)
           if not matches:
               return {
                   "yes": {"count": 0, "total_matches": 0, "percentage": 0.0},
                   "no": {"count": 0, "total_matches": 0, "percentage": 0.0}
               }

           total_matches = len(matches)
           btts_yes = sum(
               1 for match in matches
               if match.get('score', {}).get('fulltime', {}).get('home', 0) > 0 and
                  match.get('score', {}).get('fulltime', {}).get('away', 0) > 0
           )
           btts_no = total_matches - btts_yes

           result = {
               "yes": {
                   "count": btts_yes,
                   "total_matches": total_matches,
                   "percentage": round((btts_yes / total_matches) * 100, 2)
               },
               "no": {
                   "count": btts_no,
                   "total_matches": total_matches,
                   "percentage": round((btts_no / total_matches) * 100, 2)
               }
           }

           if team_id:
               result["team_details"] = self._get_team_btts_details(matches, team_id)

           return result

       def _get_team_btts_details(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
           team_matches = {"home": [], "away": [], "total": []}
           
           for match in matches:
               if match['teams']['home']['id'] == team_id:
                   team_matches["home"].append(match)
               elif match['teams']['away']['id'] == team_id:
                   team_matches["away"].append(match)
               team_matches["total"].append(match)

           return {
               position: {
                   "btts_matches": sum(
                       1 for m in matches
                       if m['score']['fulltime']['home'] > 0 and
                          m['score']['fulltime']['away'] > 0
                   ),
                   "total_matches": len(matches),
                   "percentage": round(
                       (sum(1 for m in matches
                           if m['score']['fulltime']['home'] > 0 and
                              m['score']['fulltime']['away'] > 0) / 
                       len(matches) * 100 if matches else 0), 2
                   )
               }
               for position, matches in team_matches.items()
           }

   class GoalsThresholdMetric(BaseMetric):
       def __init__(self, threshold: float):
           self.threshold = threshold

       def calculate(self, matches: List[Dict], team_id: int = None) -> Dict[str, Any]:
           matches = self.filter_finished_matches(matches)
           if not matches:
               return {
                   "over": {"count": 0, "total_matches": 0, "percentage": 0.0},
                   "under": {"count": 0, "total_matches": 0, "percentage": 0.0}
               }

           total_matches = len(matches)
           
           if team_id:
               result = self._calculate_team_thresholds(matches, team_id)
           else:
               over_count = sum(
                   1 for match in matches
                   if (match.get('score', {}).get('fulltime', {}).get('home', 0) +
                       match.get('score', {}).get('fulltime', {}).get('away', 0)) > self.threshold
               )
               under_count = total_matches - over_count

               result = {
                   "over": {
                       "count": over_count,
                       "total_matches": total_matches,
                       "percentage": round((over_count / total_matches) * 100, 2)
                   },
                   "under": {
                       "count": under_count,
                       "total_matches": total_matches,
                       "percentage": round((under_count / total_matches) * 100, 2)
                   }
               }

           return result

       def _calculate_team_thresholds(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
           home_matches = [m for m in matches if m['teams']['home']['id'] == team_id]
           away_matches = [m for m in matches if m['teams']['away']['id'] == team_id]

           return {
               "total": self._get_threshold_stats(matches),
               "home": self._get_threshold_stats(home_matches),
               "away": self._get_threshold_stats(away_matches)
           }

       def _get_threshold_stats(self, matches: List[Dict]) -> Dict[str, Any]:
           if not matches:
               return {
                   "over": {"count": 0, "total_matches": 0, "percentage": 0.0},
                   "under": {"count": 0, "total_matches": 0, "percentage": 0.0}
               }

           total = len(matches)
           over_count = sum(
               1 for m in matches
               if (m['score']['fulltime']['home'] + m['score']['fulltime']['away']) > self.threshold
           )
           under_count = total - over_count

           return {
               "over": {
                   "count": over_count,
                   "total_matches": total,
                   "percentage": round((over_count / total) * 100, 2)
               },
               "under": {
                   "count": under_count,
                   "total_matches": total,
                   "percentage": round((under_count / total) * 100, 2)
               }
           }

   class TotalGoalsMetric(BaseMetric):
       def calculate(self, matches: List[Dict], team_id: int = None) -> Dict[str, Any]:
           matches = self.filter_finished_matches(matches)
           if not matches:
               return {"count": 0, "average": 0.0}

           if team_id:
               return self._calculate_team_goals(matches, team_id)

           total_goals = sum(
               match.get('score', {}).get('fulltime', {}).get('home', 0) +
               match.get('score', {}).get('fulltime', {}).get('away', 0)
               for match in matches
           )

           return {
               "count": total_goals,
               "average": round(total_goals / len(matches), 2)
           }

       def _calculate_team_goals(self, matches: List[Dict], team_id: int) -> Dict[str, Any]:
           home_matches = []
           away_matches = []
           scored = {"total": 0, "home": 0, "away": 0}
           conceded = {"total": 0, "home": 0, "away": 0}

           for match in matches:
               if match['teams']['home']['id'] == team_id:
                   home_matches.append(match)
                   scored["home"] += match['score']['fulltime']['home']
                   scored["total"] += match['score']['fulltime']['home']
                   conceded["home"] += match['score']['fulltime']['away']
                   conceded["total"] += match['score']['fulltime']['away']
               elif match['teams']['away']['id'] == team_id:
                   away_matches.append(match)
                   scored["away"] += match['score']['fulltime']['away']
                   scored["total"] += match['score']['fulltime']['away']
                   conceded["away"] += match['score']['fulltime']['home']
                   conceded["total"] += match['score']['fulltime']['home']

           return {
               "total": {
                   "scored": scored["total"],
                   "conceded": conceded["total"],
                   "average_scored": round(scored["total"] / len(matches), 2),
                   "average_conceded": round(conceded["total"] / len(matches), 2)
               },
               "home": {
                   "scored": scored["home"],
                   "conceded": conceded["home"],
                   "average_scored": round(scored["home"] / len(home_matches), 2) if home_matches else 0,
                   "average_conceded": round(conceded["home"] / len(home_matches), 2) if home_matches else 0,
                   "matches": len(home_matches)
               },
               "away": {
                   "scored": scored["away"],
                   "conceded": conceded["away"],
                   "average_scored": round(scored["away"] / len(away_matches), 2) if away_matches else 0,
                   "average_conceded": round(conceded["away"] / len(away_matches), 2) if away_matches else 0,
                   "matches": len(away_matches)
               }
           }