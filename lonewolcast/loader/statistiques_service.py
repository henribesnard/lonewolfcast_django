import requests
from django.conf import settings
from firebase_admin import db

class StatsService:
    LIVE_STATUSES = ['1H', 'HT', '2H', 'ET', 'BT', 'P', 'INT']
    FINISHED_STATUSES = ['FT', 'AET', 'PEN']

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_ref = db.reference('matches')

    def should_fetch_stats(self, match_status):
        return match_status in self.LIVE_STATUSES + self.FINISHED_STATUSES

    def fetch_stats(self, fixture_id):
        try:
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/statistics"
            params = {'fixture': str(fixture_id)}
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('response'):
                print(f"❌ Pas de stats pour le match {fixture_id}")
                return None
            return data['response']
        except Exception as e:
            print(f"❌ Erreur API stats match {fixture_id}: {e}")
            return None

    def process_stats_data(self, stats_data):
        stats = {}
        for team_stats in stats_data:
            team_id = str(team_stats['team']['id'])
            stats[team_id] = {
                'team': team_stats['team'],
                'statistics': {
                    stat['type']: stat['value'] for stat in team_stats['statistics']
                }
            }
        return stats

    def save_to_firebase(self, fixture_id, stats_data):
        try:
            match_ref = self.firebase_ref.child(str(fixture_id))
            processed_stats = self.process_stats_data(stats_data)
            match_ref.update({'statistics': processed_stats})
            print(f"✅ Stats sauvegardées pour le match {fixture_id}")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde stats match {fixture_id}: {e}")
            return False

    def sync_match_stats(self, fixture_id, match_data):
        status = match_data.get('fixture', {}).get('status', {}).get('short')
        
        if not self.should_fetch_stats(status):
            print(f"⏭️ Stats non nécessaires pour le match {fixture_id} (status: {status})")
            return False
            
        stats = self.fetch_stats(fixture_id)
        if stats:
            return self.save_to_firebase(fixture_id, stats)
        return False

    def sync_all_matches_stats(self):
        matches = self.firebase_ref.get()
        if not matches:
            return

        for fixture_id, match_data in matches.items():
            self.sync_match_stats(fixture_id, match_data)