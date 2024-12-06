import requests
from django.conf import settings
from firebase_admin import db
import re

class PredictionSyncService:
    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_matches_ref = db.reference('matches')
        
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
            url = f"{settings.API_SPORTS_BASE_URL}/predictions"
            params = {'fixture': str(fixture_id)}
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Erreur API pour le match {fixture_id}: {str(e)}")
            return None

    def save_to_firebase(self, fixture_id, prediction_data):
        try:
            match_data = prediction_data.get('response', [{}])[0]
            cleaned_data = self.clean_data_for_firebase(match_data)
            match_ref = self.firebase_matches_ref.child(str(fixture_id))
            match_ref.update({'prediction': cleaned_data})
            print(f"✅ Prédictions sauvegardées pour le match {fixture_id}")
            return True
        except Exception as e:
            print(f"❌ Erreur Firebase pour le match {fixture_id}: {str(e)}")
            return False

    def sync_prediction(self, fixture_id):
        prediction_data = self.fetch_prediction(fixture_id)
        if prediction_data:
            return self.save_to_firebase(fixture_id, prediction_data)
        return False