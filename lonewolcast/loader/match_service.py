import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime

class MatchService:
    RATE_LIMIT = 450
    DELAY = 60 / RATE_LIMIT
    BATCH_SIZE = 100

    ACTIVE_STATUSES = {
        'TBD', 'NS', '1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT', 'PST', 'LIVE'
    }

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.root_ref = db.reference()
        self.last_request_time = time.time()
        self.request_count = 0
        self.leagues = settings.LEAGUES
        self.seasons = settings.SEASON_YEAR

    def get_base_ref(self):
        """Retourne la référence de base pour les matchs."""
        return self.root_ref.child('matches')

    def get_season_ref(self, season):
        """Retourne la référence pour une saison spécifique."""
        return self.get_base_ref().child(f'season_{season}')

    def get_league_ref(self, season, league_id):
        """Retourne la référence pour une league dans une saison."""
        return self.get_season_ref(season).child(f'league_{league_id}')

    def wait_for_rate_limit(self):
        """Gestion du rate limiting de l'API."""
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

    def fetch_matches_by_league_season(self, league_id, season):
        """Récupère tous les matchs d'une league pour une saison donnée."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures"
            params = {
                'league': str(league_id),
                'season': str(season)
            }
            
            print(f"\n🔄 Récupération des matchs - League {league_id}, Saison {season}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None
            
            matches = data.get('response', [])
            print(f"✅ {len(matches)} match(s) trouvé(s)")
            return matches
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            return None

    def fetch_single_match(self, fixture_id):
        """Récupère un match spécifique par son ID."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures"
            params = {'id': str(fixture_id)}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('response'):
                print(f"❌ Pas de données pour le match {fixture_id}")
                return None
                
            print(f"✅ Données récupérées pour le match {fixture_id}")
            return data['response'][0]
            
        except Exception as e:
            print(f"❌ Erreur API match {fixture_id}: {str(e)}")
            return None

    def process_match_data(self, match_data, season):
        """Traite les données d'un match pour la sauvegarde."""
        fixture_data = match_data['fixture']
        return {
            'metadata': {
                'fixture_id': fixture_data['id'],
                'league_id': match_data['league']['id'],
                'season': season,
                'status': fixture_data['status']['short'],
                'timestamp': fixture_data.get('timestamp'),
                'date': fixture_data.get('date'),
                'updated_at': datetime.now().isoformat()
            },
            'fixture': fixture_data,
            'league': match_data['league'],
            'teams': match_data['teams'],
            'goals': match_data.get('goals', {'home': None, 'away': None}),
            'score': match_data.get('score', {}),
            'events': match_data.get('events', []),
            'statistics': match_data.get('statistics', [])
        }

    def save_matches_batch(self, matches, current_season, league_id):
        """Sauvegarde un lot de matchs pour une saison et league spécifiques."""
        if not matches:
            return False

        try:
            fixtures_updates = {}
            for match in matches:
                fixture_id = match['fixture']['id']
                processed_match = self.process_match_data(match, current_season)
                fixtures_updates[f'fixture_{fixture_id}'] = processed_match

            league_ref = self.get_league_ref(current_season, league_id)
            league_ref.update(fixtures_updates)
            print(f"💾 {len(fixtures_updates)} match(s) sauvegardé(s) pour league {league_id}, saison {current_season}")
            return True

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False

    def sync_all_matches(self):
        """Synchronise tous les matchs pour toutes les leagues et saisons."""
        total_matches = 0
        start_time = time.time()

        for league_id in self.leagues:
            for season in self.seasons:
                matches = self.fetch_matches_by_league_season(league_id, season)
                if matches:
                    if self.save_matches_batch(matches, season, league_id):
                        total_matches += len(matches)

        elapsed_time = time.time() - start_time
        print(f"\n📊 Résumé:")
        print(f"✅ {total_matches} match(s) synchronisé(s)")
        print(f"⏱️ Durée: {elapsed_time:.1f} secondes")
        return total_matches

    def get_unfinished_matches(self):
        """Récupère tous les matchs non terminés."""
        try:
            unfinished_matches = {}
            
            for season in self.seasons:
                season_ref = self.get_season_ref(season)
                season_data = season_ref.get() or {}
                
                for league_key, league_data in season_data.items():
                    if not isinstance(league_data, dict):
                        continue
                        
                    for fixture_key, match_data in league_data.items():
                        if not isinstance(match_data, dict):
                            continue
                            
                        status = match_data.get('metadata', {}).get('status')
                        if status in self.ACTIVE_STATUSES:
                            fixture_id = match_data['metadata']['fixture_id']
                            unfinished_matches[fixture_id] = {
                                'season': season,
                                'league_id': match_data['metadata']['league_id'],
                                'data': match_data
                            }
            
            return unfinished_matches
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des matchs non terminés: {str(e)}")
            return {}

    def update_unfinished_matches(self):
        """Met à jour tous les matchs non terminés."""
        unfinished = self.get_unfinished_matches()
        if not unfinished:
            print("ℹ️ Aucun match à mettre à jour")
            return 0

        total = len(unfinished)
        print(f"🔄 Mise à jour de {total} match(s)...")
        updated = 0

        for fixture_id, match_info in unfinished.items():
            updated_data = self.fetch_single_match(fixture_id)
            if updated_data:
                season = match_info['season']
                league_id = match_info['league_id']
                if self.save_matches_batch([updated_data], season, league_id):
                    updated += 1
                    print(f"✅ Match {fixture_id} mis à jour")
                else:
                    print(f"❌ Échec de la mise à jour du match {fixture_id}")

        print(f"📊 Résumé: {updated}/{total} match(s) mis à jour")
        return updated

    def clear_season(self, season):
        """Supprime tous les matchs d'une saison."""
        try:
            self.get_season_ref(season).delete()
            print(f"✅ Saison {season} supprimée")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression de la saison {season}: {str(e)}")
            return False

    def clear_league(self, season, league_id):
        """Supprime tous les matchs d'une league pour une saison donnée."""
        try:
            self.get_league_ref(season, league_id).delete()
            print(f"✅ League {league_id} supprimée pour la saison {season}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression de la league {league_id}: {str(e)}")
            return False

    def clear_all(self):
        """Supprime toutes les données des matchs."""
        try:
            self.get_base_ref().delete()
            print("✅ Toutes les données ont été supprimées")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression des données: {str(e)}")
            return False