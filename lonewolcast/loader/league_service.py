import requests
import time
from django.conf import settings
from firebase_admin import db
from datetime import datetime

class LeagueService:
    RATE_LIMIT = 450
    DELAY = 60 / RATE_LIMIT

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_ref = db.reference('leagues')
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
                print(f"⏳ Limite d'API atteinte, pause de {sleep_time:.1f} secondes")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:
            time.sleep(self.DELAY)

        self.request_count += 1

    def fetch_leagues(self):
        """Récupère toutes les leagues depuis l'API."""
        try:
            self.wait_for_rate_limit()
            
            url = f"{settings.API_SPORTS_BASE_URL}/leagues"
            print("🔄 Récupération des leagues depuis l'API...")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None
                
            leagues = data.get('response', [])
            print(f"✅ {len(leagues)} leagues récupérées")
            return leagues
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des leagues: {str(e)}")
            return None

    def process_league_data(self, league_data):
        """Traite les données d'une league pour la sauvegarde."""
        return {
            'league': league_data['league'],
            'country': league_data['country'],
            'seasons': league_data['seasons'],
            'updated_at': datetime.now().isoformat()
        }

    def save_to_firebase(self, leagues):
        """Sauvegarde les leagues dans Firebase."""
        if not leagues:
            return False
            
        try:
            updates = {}
            for league in leagues:
                league_id = str(league['league']['id'])
                processed_league = self.process_league_data(league)
                updates[league_id] = processed_league
                print(f"📝 Préparation league {league_id} - {league['league']['name']}")
            
            self.firebase_ref.update(updates)
            print(f"💾 {len(updates)} leagues sauvegardées avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde Firebase: {str(e)}")
            return False

    def clear_database(self):
        """Vide la collection des leagues."""
        try:
            self.firebase_ref.delete()
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression: {str(e)}")
            return False

    def sync_leagues(self):
        """Synchronise toutes les leagues."""
        print("🔄 Début de la synchronisation des leagues...")
        start_time = time.time()
        
        leagues = self.fetch_leagues()
        
        if not leagues:
            print("ℹ️ Aucune league trouvée")
            return False

        success = self.save_to_firebase(leagues)
        
        if success:
            elapsed_time = time.time() - start_time
            print(f"\n✅ Synchronisation réussie en {elapsed_time:.1f} secondes")
            print(f"📊 {len(leagues)} leagues synchronisées")
        else:
            print("\n❌ Échec de la synchronisation")
            
        return success