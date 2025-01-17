# statistics_ht_service.py
import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime

class MatchStatus:
    """Statuts des matchs pour filtrage."""
    FINISHED = {'FT', 'AET', 'PEN', 'ABD', 'AWD', 'WO', 'CANC'}
    LIVE = {'1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT', 'LIVE'}

class MatchStatisticsHalfTimeService:
    """Service pour gérer les statistiques mi-temps avec la nouvelle structure (depuis 2024)."""
    RATE_LIMIT = 450
    DELAY = 60 / RATE_LIMIT
    MIN_SEASON = 2024  # Les statistiques sont disponibles uniquement pour les saisons >= 2024

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.root_ref = db.reference()
        self.last_request_time = time.time()
        self.request_count = 0

    def get_match_ref(self, season, league_id, fixture_id):
        """Retourne la référence Firebase pour un match donné."""
        return (self.root_ref
                .child('matches')
                .child(f'season_{season}')
                .child(f'league_{league_id}')
                .child('fixtures')
                .child(f'fixture_{fixture_id}'))

    def wait_for_rate_limit(self):
        """Gestion du taux limite pour l'API."""
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
        """Récupère les statistiques de mi-temps d'un match via l'API."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/statistics"
            params = {'fixture': str(fixture_id), 'half': 'true'}

            print(f"🔄 Récupération des statistiques mi-temps - Match {fixture_id}")

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None

            stats = data.get('response', [])
            if stats:
                print(f"✅ Statistiques mi-temps récupérées pour le match {fixture_id}")
                return stats

            print("ℹ️ Aucune statistique mi-temps disponible pour le match.")
            return None

        except Exception as e:
            print(f"❌ Erreur lors de la récupération des statistiques : {str(e)}")
            return None

    def normalize_value(self, value):
        """Normalise une valeur statistique (exemple : 50% -> 50.0)."""
        if isinstance(value, str) and value.endswith('%'):
            try:
                return float(value.rstrip('%'))
            except ValueError:
                return value
        return value

    def process_period_statistics(self, stats):
        """Traite les statistiques d'une période spécifique."""
        return {
            stat['type']: self.normalize_value(stat['value'])
            for stat in stats
        }

    def process_team_statistics(self, team_stats):
        """Traite les statistiques pour une équipe donnée."""
        return {
            'team': team_stats['team'],
            'statistics': {
                'full': self.process_period_statistics(team_stats['statistics']),
                'first_half': self.process_period_statistics(team_stats['statistics_1h']),
                'second_half': self.process_period_statistics(team_stats['statistics_2h'])
            }
        }

    def save_statistics(self, fixture_id, stats, season, league_id):
        """Sauvegarde les statistiques mi-temps dans Firebase."""
        try:
            if not stats or int(season) < self.MIN_SEASON:
                return False

            processed_stats = [self.process_team_statistics(team_stats) for team_stats in stats]
            match_ref = self.get_match_ref(season, league_id, fixture_id)

            match_ref.update({
                'statistics_with_ht_data': processed_stats,
                'statistics_ht_updated_at': datetime.now().isoformat()
            })

            print(f"💾 Statistiques mi-temps sauvegardées pour le match {fixture_id}")
            return True

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde des statistiques : {str(e)}")
            return False

    def get_matches_by_status(self, status_set):
        """Récupère les matchs selon leur statut."""
        matches = []
        seasons_ref = self.root_ref.child('matches').get() or {}

        for season_key, season_data in seasons_ref.items():
            if not isinstance(season_data, dict):
                continue

            season = int(season_key.replace('season_', ''))
            if season < self.MIN_SEASON:
                continue

            for league_key, league_data in season_data.items():
                if not isinstance(league_data, dict):
                    continue

                league_id = league_key.replace('league_', '')
                for fixture_key, fixture_data in league_data.get('fixtures', {}).items():
                    if not isinstance(fixture_data, dict):
                        continue

                    match_status = fixture_data.get('metadata', {}).get('status')
                    if match_status in status_set:
                        fixture_id = fixture_key.replace('fixture_', '')
                        matches.append({
                            'fixture_id': fixture_id,
                            'season': season,
                            'league_id': league_id,
                            'has_stats': 'statistics_with_ht_data' in fixture_data
                        })

        return matches

    def sync_match_statistics(self, fixture_id, season, league_id):
        """Synchronise les statistiques pour un match donné."""
        stats = self.fetch_statistics(fixture_id)
        if stats:
            return self.save_statistics(fixture_id, stats, season, league_id)
        return False

    def sync_finished_matches(self):
        """Synchronise les statistiques des matchs terminés."""
        finished_matches = self.get_matches_by_status(MatchStatus.FINISHED)
        matches_without_stats = [m for m in finished_matches if not m['has_stats']]
        total = len(matches_without_stats)

        if not total:
            print("ℹ️ Aucun match terminé sans statistiques mi-temps (depuis 2024).")
            return 0

        print(f"📊 Synchronisation des statistiques mi-temps pour {total} match(s) terminé(s).")
        updated = 0

        for match in matches_without_stats:
            if self.sync_match_statistics(match['fixture_id'], match['season'], match['league_id']):
                updated += 1

        print(f"✅ {updated}/{total} statistiques mi-temps synchronisées.")
        return updated

    def update_live_matches(self):
        """Met à jour les statistiques des matchs en cours."""
        live_matches = self.get_matches_by_status(MatchStatus.LIVE)
        total = len(live_matches)

        if not total:
            print("ℹ️ Aucun match en cours (depuis 2024).")
            return 0

        print(f"🔄 Mise à jour des statistiques mi-temps pour {total} match(s) en cours.")
        updated = 0

        for match in live_matches:
            if self.sync_match_statistics(match['fixture_id'], match['season'], match['league_id']):
                updated += 1

        print(f"✅ {updated}/{total} statistiques mi-temps mises à jour.")
        return updated
