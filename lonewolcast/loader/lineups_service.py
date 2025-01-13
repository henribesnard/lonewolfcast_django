import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime

class MatchStatus:
    """Statuts des matchs pour filtrage."""
    FINISHED = {'FT', 'AET', 'PEN', 'ABD', 'AWD', 'WO', 'CANC'}
    LIVE = {'1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT', 'LIVE'}

class LineupService:
    """Service pour gérer les compositions des matchs."""
    RATE_LIMIT = 450
    DELAY = 60 / RATE_LIMIT

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

    def fetch_lineups(self, fixture_id):
        """Récupère les compositions pour un match spécifique."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/lineups"
            params = {'fixture': str(fixture_id)}

            print(f"🔄 Récupération des compositions - Match {fixture_id}")

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None

            lineups = data.get('response', [])
            if lineups:
                print(f"✅ Compositions récupérées pour le match {fixture_id}")
                return lineups

            print("ℹ️ Aucune composition disponible pour le match.")
            return None

        except Exception as e:
            print(f"❌ Erreur lors de la récupération des compositions : {str(e)}")
            return None

    def process_player(self, player_data):
        """Traite les données d'un joueur."""
        return {
            'id': player_data['player']['id'],
            'name': player_data['player']['name'],
            'number': player_data['player']['number'],
            'position': player_data['player']['pos'],
            'grid': player_data['player']['grid']
        }

    def process_lineup(self, lineup_data):
        """Traite les données d'une équipe."""
        return {
            'team': lineup_data['team'],
            'coach': lineup_data['coach'],
            'formation': lineup_data['formation'],
            'startXI': [self.process_player(player) for player in lineup_data['startXI']],
            'substitutes': [self.process_player(player) for player in lineup_data['substitutes']]
        }

    def save_lineups(self, fixture_id, lineups, season, league_id):
        """Sauvegarde les compositions dans le nœud du match correspondant."""
        try:
            if not lineups:
                return False

            processed_lineups = [self.process_lineup(lineup) for lineup in lineups]
            match_ref = self.get_match_ref(season, league_id, fixture_id)

            match_ref.update({
                'lineups': processed_lineups,
                'lineups_updated_at': datetime.now().isoformat()
            })

            print(f"💾 Compositions sauvegardées pour le match {fixture_id}")
            return True

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde des compositions : {str(e)}")
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
                            'has_lineups': 'lineups' in fixture_data
                        })

        return matches

    def sync_match_lineups(self, fixture_id, season, league_id):
        """Synchronise les compositions pour un match spécifique."""
        lineups = self.fetch_lineups(fixture_id)
        if lineups:
            return self.save_lineups(fixture_id, lineups, season, league_id)
        return False

    def sync_finished_matches(self):
        """Synchronise les compositions des matchs terminés."""
        finished_matches = self.get_matches_by_status(MatchStatus.FINISHED)
        matches_without_lineups = [m for m in finished_matches if not m['has_lineups']]
        total = len(matches_without_lineups)

        if not total:
            print("ℹ️ Aucun match terminé sans compositions.")
            return 0

        print(f"📊 Synchronisation des compositions pour {total} match(s) terminé(s).")
        updated = 0

        for match in matches_without_lineups:
            if self.sync_match_lineups(match['fixture_id'], match['season'], match['league_id']):
                updated += 1

        print(f"✅ {updated}/{total} matchs synchronisés.")
        return updated

    def update_live_matches(self):
        """Met à jour les compositions des matchs en cours."""
        live_matches = self.get_matches_by_status(MatchStatus.LIVE)
        total = len(live_matches)

        if not total:
            print("ℹ️ Aucun match en cours.")
            return 0

        print(f"🔄 Mise à jour des compositions pour {total} match(s) en cours.")
        updated = 0

        for match in live_matches:
            if self.sync_match_lineups(match['fixture_id'], match['season'], match['league_id']):
                updated += 1

        print(f"✅ {updated}/{total} matchs mis à jour.")
        return updated

    def clear_lineups(self, matches=None):
        """Supprime les compositions des matchs spécifiés ou de tous les matchs."""
        try:
            if not matches:
                matches = self.get_matches_by_status(MatchStatus.FINISHED | MatchStatus.LIVE)

            cleared = 0
            for match in matches:
                match_ref = self.get_match_ref(match['season'], match['league_id'], match['fixture_id'])
                match_ref.child('lineups').delete()
                match_ref.child('lineups_updated_at').delete()
                cleared += 1

            print(f"✅ Compositions supprimées pour {cleared} match(s).")
            return True

        except Exception as e:
            print(f"❌ Erreur lors de la suppression des compositions : {str(e)}")
            return False
