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
        """Retourne la référence pour une ligue dans une saison."""
        return self.get_season_ref(season).child(f'league_{league_id}')

    def fetch_league_metadata(self, league_id):
        """Récupère les métadonnées de la ligue depuis Firebase."""
        league_ref = self.root_ref.child('leagues').child(str(league_id))
        return league_ref.get() or {}

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
        """Récupère tous les matchs d'une ligue pour une saison donnée."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures"
            params = {'league': str(league_id), 'season': str(season)}

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None

            return data.get('response', [])

        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            return None

    def save_metadata_league_and_season(self, league_id, season):
        """Sauvegarde les métadonnées de la ligue et de la saison."""
        league_metadata = self.fetch_league_metadata(league_id)
        if not league_metadata:
            print(f"⚠️ Métadonnées non trouvées pour la ligue {league_id}")
            return False

        league_ref = self.get_league_ref(season, league_id)

        # Sauvegarder les métadonnées de la ligue
        league_ref.child('metadata_league').set({
            'id': league_metadata.get('league', {}).get('id'),
            'name': league_metadata.get('league', {}).get('name'),
            'country': league_metadata.get('country', {}).get('name'),
            'logo': league_metadata.get('league', {}).get('logo'),
            'type': league_metadata.get('league', {}).get('type'),
            'updated_at': league_metadata.get('updated_at')
        })

        # Récupérer les métadonnées de la saison
        seasons_metadata = league_metadata.get('seasons', [])
        season_metadata = next(
            (s for s in seasons_metadata if s.get('year') == season),
            None
        )

        if season_metadata:
            league_ref.child('metadata_season').set({
                'start': season_metadata.get('start'),
                'end': season_metadata.get('end'),
                'year': season_metadata.get('year'),
                'current': season_metadata.get('current'),
                'updated_at': season_metadata.get('updated_at')
            })
        return True

    def process_match_data(self, match_data):
        """Traite les données d'un match pour la sauvegarde."""
        fixture_data = match_data['fixture']
        return {
            'metadata': {
                'fixture_id': fixture_data['id'],
                'date': fixture_data.get('date'),
                'status': fixture_data['status']['short'],
                'updated_at': datetime.now().isoformat()
            },
            'fixture': {
                'referee': fixture_data.get('referee'),
                'venue': fixture_data.get('venue', {})
            },
            'teams': match_data.get('teams', {}),
            'goals': match_data.get('goals', {'home': None, 'away': None}),
            'score': match_data.get('score', {})
        }

    def save_matches_batch(self, matches, season, league_id):
        """Sauvegarde un lot de matchs pour une saison et ligue spécifiques."""
        if not matches:
            return False

        try:
            fixtures_updates = {}
            for match in matches:
                fixture_id = match['fixture']['id']
                processed_match = self.process_match_data(match)
                fixtures_updates[f'fixture_{fixture_id}'] = processed_match

            league_ref = self.get_league_ref(season, league_id).child('fixtures')
            league_ref.update(fixtures_updates)
            print(f"💾 {len(fixtures_updates)} match(s) sauvegardé(s) pour league {league_id}, saison {season}")
            return True

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False

    def sync_all_matches(self):
        """Synchronise tous les matchs pour toutes les ligues et saisons."""
        total_matches = 0  # Initialiser le compteur global
        print("🔄 Début de la synchronisation...\n")

        for season in self.seasons:
            for league_id in self.leagues:
                if not self.save_metadata_league_and_season(league_id, season):
                    continue
                matches = self.fetch_matches_by_league_season(league_id, season)
                if matches:
                    if self.save_matches_batch(matches, season, league_id):
                        total_matches += len(matches)

        print(f"\n📊 Résumé : {total_matches} match(s) synchronisé(s)")
        return total_matches

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
        """Supprime tous les matchs d'une ligue pour une saison donnée."""
        try:
            self.get_league_ref(season, league_id).delete()
            print(f"✅ League {league_id} supprimée pour la saison {season}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression de la ligue {league_id}: {str(e)}")
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
