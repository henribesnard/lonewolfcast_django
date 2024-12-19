import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime
from loader.constants import MatchStatus

class StatisticsService:
    RATE_LIMIT = 450
    DELAY = 60 / RATE_LIMIT

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.root_ref = db.reference()
        self.last_request_time = time.time()
        self.request_count = 0

    def get_match_ref(self, season, league_id, fixture_id):
        return (self.root_ref
                .child('matches')
                .child(f'season_{season}')
                .child(f'league_{league_id}')
                .child(f'fixture_{fixture_id}'))

    def wait_for_rate_limit(self):
        current_time = time.time()
        elapsed_time = current_time - self.last_request_time
        
        if elapsed_time >= 60:
            self.request_count = 0
            self.last_request_time = current_time
            return

        if self.request_count >= self.RATE_LIMIT:
            sleep_time = 60 - elapsed_time
            if sleep_time > 0:
                print(f"⏳ Limite atteinte, pause de {sleep_time:.1f} secondes")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:
            time.sleep(self.DELAY)

        self.request_count += 1

    def fetch_statistics(self, fixture_id):
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/statistics"
            params = {'fixture': str(fixture_id)}
            
            print(f"🔄 Récupération des statistiques globales - Match {fixture_id}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None
            
            stats = data.get('response', [])
            if stats:
                print(f"✅ Statistiques globales récupérées")
                return stats
            
            print("ℹ️ Pas de statistiques disponibles")
            return None
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            return None

    def normalize_value(self, value):
        """Normalise une valeur statistique."""
        if value is None:
            return 0
        if isinstance(value, str):
            if value.endswith('%'):
                try:
                    return float(value.rstrip('%'))
                except ValueError:
                    return 0
            # Gestion des valeurs décimales comme "1.06"
            try:
                return float(value)
            except ValueError:
                return value
        return value

    def process_team_statistics(self, team_stats):
        """Traite les statistiques d'une équipe."""
        processed_stats = {}
        for stat in team_stats['statistics']:
            processed_stats[stat['type']] = self.normalize_value(stat['value'])
        
        return {
            'team': team_stats['team'],
            'statistics': processed_stats
        }

    def save_statistics(self, fixture_id, stats, season, league_id):
        try:
            if not stats:
                return False

            processed_stats = [self.process_team_statistics(team_stats) for team_stats in stats]
            match_ref = self.get_match_ref(season, league_id, fixture_id)
            
            match_ref.update({
                'statistics_global': processed_stats,
                'statistics_global_updated_at': datetime.now().isoformat()
            })
            
            print(f"💾 Statistiques globales sauvegardées pour le match {fixture_id}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False

    def get_matches_by_status(self, status_set):
        matches = []
        seasons_ref = self.root_ref.child('matches').get() or {}
        
        for season_key, season_data in seasons_ref.items():
            if not isinstance(season_data, dict):
                continue
                
            season = season_key.replace('season_', '')
            for league_key, league_data in season_data.items():
                if not isinstance(league_data, dict):
                    continue
                    
                league_id = league_key.replace('league_', '')
                for fixture_key, fixture_data in league_data.items():
                    if not isinstance(fixture_data, dict):
                        continue
                    
                    match_status = fixture_data.get('metadata', {}).get('status')
                    if match_status in status_set:
                        fixture_id = fixture_key.replace('fixture_', '')
                        matches.append({
                            'fixture_id': fixture_id,
                            'season': season,
                            'league_id': league_id,
                            'has_stats': 'statistics_global' in fixture_data
                        })
        
        return matches

    def sync_finished_matches(self):
        finished_matches = self.get_matches_by_status(MatchStatus.FINISHED_STATUSES)
        matches_without_stats = [m for m in finished_matches if not m['has_stats']]
        total = len(matches_without_stats)
        
        if not total:
            print("ℹ️ Aucun match terminé sans statistiques globales")
            return 0
        
        print(f"📊 Synchronisation des statistiques globales pour {total} match(s) terminé(s)")
        updated = 0
        
        for match in matches_without_stats:
            if self.sync_match_statistics(match['fixture_id'], match['season'], match['league_id']):
                updated += 1
        
        print(f"✅ {updated}/{total} statistiques globales synchronisées")
        return updated

    def update_live_matches(self):
        live_matches = self.get_matches_by_status(MatchStatus.LIVE_STATUSES)
        total = len(live_matches)
        
        if not total:
            print("ℹ️ Aucun match en cours")
            return 0
        
        print(f"🔄 Mise à jour des statistiques globales pour {total} match(s) en cours")
        updated = 0
        
        for match in live_matches:
            if self.sync_match_statistics(match['fixture_id'], match['season'], match['league_id']):
                updated += 1
        
        print(f"✅ {updated}/{total} statistiques globales mises à jour")
        return updated

    def sync_match_statistics(self, fixture_id, season, league_id):
        stats = self.fetch_statistics(fixture_id)
        if stats:
            return self.save_statistics(fixture_id, stats, season, league_id)
        return False

    def clear_statistics(self, matches=None):
        try:
            if not matches:
                matches = self.get_matches_by_status(MatchStatus.FINISHED_STATUSES | MatchStatus.LIVE_STATUSES)
            
            cleared = 0
            for match in matches:
                match_ref = self.get_match_ref(
                    match['season'],
                    match['league_id'],
                    match['fixture_id']
                )
                match_ref.child('statistics_global').delete()
                match_ref.child('statistics_global_updated_at').delete()
                cleared += 1
            
            print(f"✅ Statistiques globales supprimées pour {cleared} match(s)")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la suppression: {str(e)}")
            return False