# statistiques_service.py
import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime

class StatsService:
    RATE_LIMIT = 450  
    DELAY = 60 / RATE_LIMIT  # ~0.13 secondes entre les appels

    # Statuts des matchs
    FINISHED_STATUSES = {'FT', 'AET', 'PEN', 'AWD', 'WO'}  # Matchs terminés
    LIVE_STATUSES = {'1H', 'HT', '2H', 'ET', 'BT', 'P', 'INT', 'LIVE'}  # Matchs en cours

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_ref = db.reference('matches')
        self.last_request_time = time.time()
        self.request_count = 0

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

    def fetch_stats(self, fixture_id):
        """Récupère les statistiques d'un match depuis l'API."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/statistics"
            params = {'fixture': str(fixture_id)}
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get('response')
        except Exception as e:
            print(f"❌ Erreur API stats match {fixture_id}: {str(e)}")
            return None

    def process_stats_data(self, stats_data):
        """Traite les données de statistiques pour Firebase."""
        stats = {}
        for team_stats in stats_data:
            team_id = str(team_stats['team']['id'])
            stats[team_id] = {
                'team': team_stats['team'],
                'statistics': {
                    stat['type']: stat['value'] 
                    for stat in team_stats['statistics']
                }
            }
        return stats

    def batch_save_to_firebase(self, stats_dict, batch_size=50):
        """Sauvegarde les statistiques par lots dans Firebase."""
        try:
            updates = {}
            processed = 0
            total = len(stats_dict)
            
            for fixture_id, stats_data in stats_dict.items():
                if stats_data:
                    processed_stats = self.process_stats_data(stats_data)
                    updates[f'{fixture_id}/statistics'] = processed_stats
                    processed += 1
                
                if len(updates) >= batch_size:
                    self.firebase_ref.update(updates)
                    updates = {}
                    print(f"💾 {processed}/{total} stats sauvegardées")

            if updates:
                self.firebase_ref.update(updates)
                print(f"💾 {processed}/{total} stats sauvegardées")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde batch: {str(e)}")
            return False

    def get_finished_matches_without_stats(self):
        """Récupère les matchs terminés sans statistiques."""
        try:
            all_matches = self.firebase_ref.get() or {}
            return {
                fixture_id: match_data 
                for fixture_id, match_data in all_matches.items()
                if (match_data.get('fixture', {}).get('status', {}).get('short') in self.FINISHED_STATUSES and
                    'statistics' not in match_data)
            }
        except Exception as e:
            print(f"❌ Erreur récupération matchs terminés: {str(e)}")
            return {}

    def get_all_finished_matches(self):
        """Récupère tous les matchs terminés."""
        try:
            all_matches = self.firebase_ref.get() or {}
            return {
                fixture_id: match_data 
                for fixture_id, match_data in all_matches.items()
                if match_data.get('fixture', {}).get('status', {}).get('short') in self.FINISHED_STATUSES
            }
        except Exception as e:
            print(f"❌ Erreur récupération matchs terminés: {str(e)}")
            return {}

    def get_live_matches(self):
        """Récupère tous les matchs en cours."""
        try:
            all_matches = self.firebase_ref.get() or {}
            return {
                fixture_id: match_data 
                for fixture_id, match_data in all_matches.items()
                if match_data.get('fixture', {}).get('status', {}).get('short') in self.LIVE_STATUSES
            }
        except Exception as e:
            print(f"❌ Erreur récupération matchs en cours: {str(e)}")
            return {}

    def sync_stats(self, matches):
        """Synchronise les statistiques pour une liste de matchs."""
        if not matches:
            return 0

        total = len(matches)
        print(f"\n📊 Traitement de {total} matchs...")
        
        stats_dict = {}
        processed = 0
        
        for fixture_id, match_data in matches.items():
            teams = match_data.get('teams', {})
            home_team = teams.get('home', {}).get('name', 'Inconnu')
            away_team = teams.get('away', {}).get('name', 'Inconnu')
            status = match_data.get('fixture', {}).get('status', {}).get('short')
            
            processed += 1
            if processed % 10 == 0:
                print(f"⏳ Progression: {processed}/{total}")
            
            print(f"\n⚽ Match {fixture_id}: {home_team} vs {away_team} ({status})")
            stats_data = self.fetch_stats(fixture_id)
            if stats_data:
                stats_dict[fixture_id] = stats_data
                print(f"✅ Stats récupérées")
            else:
                print(f"⚠️ Pas de stats disponibles")

        if stats_dict:
            print("\n💾 Sauvegarde des statistiques...")
            if self.batch_save_to_firebase(stats_dict):
                return len(stats_dict)
        return 0

