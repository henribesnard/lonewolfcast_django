import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime
from loader.constants import MatchStatus

class EventService:
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

    def fetch_events(self, fixture_id):
        """Récupère les événements pour un match spécifique."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/events"
            params = {'fixture': str(fixture_id)}
            
            print(f"🔄 Récupération des événements - Match {fixture_id}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None
            
            events = data.get('response', [])
            if events:
                print(f"✅ {len(events)} événement(s) récupéré(s)")
                return events
            
            print("ℹ️ Pas d'événements disponibles")
            return None
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            return None

    def process_event(self, event):
        """Traite un événement pour la sauvegarde."""
        return {
            'time': event['time'],
            'team': event['team'],
            'player': event['player'],
            'assist': event['assist'],
            'type': event['type'],
            'detail': event['detail'],
            'comments': event['comments']
        }

    def save_events(self, fixture_id, events, season, league_id):
        """Sauvegarde les événements dans le nœud du match correspondant."""
        try:
            if not events:
                return False

            processed_events = [self.process_event(event) for event in events]
            match_ref = self.get_match_ref(season, league_id, fixture_id)
            
            match_ref.update({
                'events': processed_events,
                'events_updated_at': datetime.now().isoformat()
            })
            
            print(f"💾 Événements sauvegardés pour le match {fixture_id}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False

    def get_matches_by_status(self, status_set):
        """Récupère les matchs selon leur statut."""
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
                            'has_events': 'events' in fixture_data
                        })
        
        return matches

    def sync_finished_matches(self):
        """Synchronise les événements des matchs terminés."""
        finished_matches = self.get_matches_by_status(MatchStatus.FINISHED_STATUSES)
        matches_without_events = [m for m in finished_matches if not m['has_events']]
        total = len(matches_without_events)
        
        if not total:
            print("ℹ️ Aucun match terminé sans événements")
            return 0
        
        print(f"📊 Synchronisation des événements pour {total} match(s) terminé(s)")
        updated = 0
        
        for match in matches_without_events:
            if self.sync_match_events(
                match['fixture_id'],
                match['season'],
                match['league_id']
            ):
                updated += 1
        
        print(f"✅ {updated}/{total} matchs synchronisés")
        return updated

    def update_live_matches(self):
        """Met à jour les événements des matchs en cours."""
        live_matches = self.get_matches_by_status(MatchStatus.LIVE_STATUSES)
        total = len(live_matches)
        
        if not total:
            print("ℹ️ Aucun match en cours")
            return 0
        
        print(f"🔄 Mise à jour des événements pour {total} match(s) en cours")
        updated = 0
        
        for match in live_matches:
            if self.sync_match_events(
                match['fixture_id'],
                match['season'],
                match['league_id']
            ):
                updated += 1
        
        print(f"✅ {updated}/{total} matchs mis à jour")
        return updated

    def sync_match_events(self, fixture_id, season, league_id):
        """Synchronise les événements pour un match spécifique."""
        events = self.fetch_events(fixture_id)
        if events:
            return self.save_events(fixture_id, events, season, league_id)
        return False

    def clear_events(self, matches=None):
        """Supprime les événements des matchs spécifiés ou tous les matchs."""
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
                match_ref.child('events').delete()
                match_ref.child('events_updated_at').delete()
                cleared += 1
            
            print(f"✅ Événements supprimés pour {cleared} match(s)")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la suppression: {str(e)}")
            return False

