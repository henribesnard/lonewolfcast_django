# prediction_service.py
import requests
from django.conf import settings
from firebase_admin import db
import re
import time

class PredictionService:
    RATE_LIMIT = 450  # Requêtes max par minute
    DELAY = 60 / RATE_LIMIT  # Environ 0.133 secondes entre les requêtes
    UPCOMING_STATUSES = {'NS', 'PST', 'TBD'}

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_ref = db.reference('matches')
        self.last_request_time = time.time()
        self.request_count = 0

    def wait_for_rate_limit(self):
        """Gestion optimisée du rate limiting."""
        current_time = time.time()
        elapsed_time = current_time - self.last_request_time
        
        # Réinitialisation du compteur après une minute
        if elapsed_time >= 60:
            self.request_count = 0
            self.last_request_time = current_time
            return

        # Si on approche la limite, on attend
        if self.request_count >= self.RATE_LIMIT:
            sleep_time = 60 - elapsed_time
            if sleep_time > 0:
                print(f"⏳ Limite atteinte, pause de {sleep_time:.1f} secondes")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:
            # Petit délai entre les requêtes
            time.sleep(self.DELAY)

        self.request_count += 1

    def clean_key(self, key):
        if not key:
            return "empty"
        clean_key = str(key)
        clean_key = re.sub(r'[.$#\[\]/\-]', '_', clean_key)
        clean_key = clean_key.replace('%', 'percent')
        return clean_key
        
    def clean_data_for_firebase(self, data):
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                clean_key = self.clean_key(key)
                if value is not None:
                    cleaned_value = self.clean_data_for_firebase(value)
                    cleaned[clean_key] = cleaned_value
            return cleaned
        elif isinstance(data, list):
            return [self.clean_data_for_firebase(item) for item in data if item is not None]
        return data

    def fetch_prediction(self, fixture_id):
        try:
            self.wait_for_rate_limit()
            
            url = f"{settings.API_SPORTS_BASE_URL}/predictions"
            params = {'fixture': str(fixture_id)}
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            print(f"❌ Erreur API pour le match {fixture_id}: {str(e)}")
            return None

    def batch_save_to_firebase(self, predictions, batch_size=50):
        """Sauvegarde des prédictions par lots pour plus d'efficacité."""
        try:
            updates = {}
            for fixture_id, prediction_data in predictions.items():
                if prediction_data and 'response' in prediction_data:
                    match_data = prediction_data['response'][0]
                    cleaned_data = self.clean_data_for_firebase(match_data)
                    updates[f'{fixture_id}/prediction'] = cleaned_data

                if len(updates) >= batch_size:
                    self.firebase_ref.update(updates)
                    updates = {}

            if updates:  # Sauvegarder le dernier lot
                self.firebase_ref.update(updates)
                
            return True
        except Exception as e:
            print(f"❌ Erreur Firebase batch save: {str(e)}")
            return False

    def get_matches_without_prediction(self):
        try:
            all_matches = self.firebase_ref.get() or {}
            return {
                fixture_id: match_data 
                for fixture_id, match_data in all_matches.items()
                if 'prediction' not in match_data
            }
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des matchs: {str(e)}")
            return {}

    def get_upcoming_matches_without_prediction(self):
        try:
            all_matches = self.firebase_ref.get() or {}
            return {
                fixture_id: match_data 
                for fixture_id, match_data in all_matches.items()
                if ('prediction' not in match_data and 
                    match_data.get('fixture', {}).get('status', {}).get('short') in self.UPCOMING_STATUSES)
            }
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des matchs: {str(e)}")
            return {}

    def sync_predictions(self, matches):
        if not matches:
            return 0

        total = len(matches)
        print(f"\n📊 Traitement de {total} matchs...")
        
        # Récupération des prédictions
        predictions = {}
        processed = 0
        
        for fixture_id, match_data in matches.items():
            teams = match_data.get('teams', {})
            processed += 1
            
            if processed % 10 == 0:  # Log tous les 10 matchs
                print(f"⏳ Progression: {processed}/{total}")
            
            prediction_data = self.fetch_prediction(fixture_id)
            if prediction_data:
                predictions[fixture_id] = prediction_data

        # Sauvegarde par lots
        print("\n💾 Sauvegarde des prédictions...")
        if self.batch_save_to_firebase(predictions):
            synced = len(predictions)
            print(f"✅ {synced}/{total} prédictions sauvegardées")
            return synced
        
        return 0