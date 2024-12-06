import requests
from datetime import datetime
from django.conf import settings
from firebase_admin import db

class MatchSyncService:
    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_ref = db.reference('matches')

    def fetch_matches(self, date, league_id):
        try:
            league_id = int(league_id)
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures"
            params = {
                'date': date,
                'season': '2024',
                'timezone': 'Europe/Paris',
                'league': league_id
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            matches = response.json().get('response', [])
            print(f"✅ {len(matches)} matchs trouvés pour la ligue {league_id}")
            return matches
            
        except Exception as e:
            print(f"❌ Erreur pour la ligue {league_id}: {e}")
            return []

    def save_to_firebase(self, match_data):
        try:
            fixture_id = str(match_data['fixture']['id'])
            match_ref = self.firebase_ref.child(fixture_id)

            # Préparer les données du match
            firebase_data = {
                'fixture': {
                    'id': match_data['fixture']['id'],
                    'date': match_data['fixture']['date'],
                    'status': match_data['fixture']['status'],
                    'periods': match_data['fixture']['periods'],
                    'venue': match_data['fixture']['venue'],
                },
                'league': match_data['league'],
                'teams': match_data['teams'],
                'goals': match_data['goals'],
                'score': match_data['score'],
            }
            
            match_ref.set(firebase_data)
            print(f"✅ Match {fixture_id} sauvegardé")
            return True

        except Exception as e:
            print(f"❌ Erreur sauvegarde match {fixture_id}: {e}")
            return False

    def sync_matches(self):
        print("🔄 Début synchronisation des matchs...")
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            for league_id in settings.LEAGUES:
                matches_data = self.fetch_matches(today, league_id)
                
                for match_data in matches_data:
                    self.save_to_firebase(match_data)
                    
            print("✅ Synchronisation terminée")
            
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation: {e}")