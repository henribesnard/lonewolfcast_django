import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime
from loader.constants import MatchStatus

class PlayersStatsService:
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

    def fetch_players_stats(self, fixture_id):
        """Récupère les statistiques des joueurs pour un match."""
        try:
            self.wait_for_rate_limit()
            url = f"{settings.API_SPORTS_BASE_URL}/fixtures/players"
            params = {'fixture': str(fixture_id)}
            
            print(f"🔄 Récupération des stats joueurs - Match {fixture_id}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"⚠️ Erreur API: {data['errors']}")
                return None
            
            teams_stats = data.get('response', [])
            if teams_stats:
                print(f"✅ Statistiques de {len(teams_stats)} équipe(s) récupérées")
                return teams_stats
            
            print("ℹ️ Pas de statistiques disponibles")
            return None
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            return None

    def normalize_value(self, value):
        """Normalise une valeur statistique."""
        if isinstance(value, str) and value.endswith('%'):
            try:
                return float(value.rstrip('%'))
            except ValueError:
                return value
        return value

    def process_player_stats(self, stats):
        """Traite les statistiques d'un joueur."""
        if not stats:
            return {}
            
        processed = {}
        for category, values in stats.items():
            if isinstance(values, dict):
                processed[category] = {
                    k: self.normalize_value(v)
                    for k, v in values.items()
                }
            else:
                processed[category] = values
        return processed

    def process_team_stats(self, team_data):
        """Traite les statistiques d'une équipe."""
        return {
            'team': team_data['team'],
            'players': [
                {
                    'player': player['player'],
                    'statistics': [self.process_player_stats(stat) for stat in player['statistics']]
                }
                for player in team_data['players']
            ]
        }

    def save_players_stats(self, fixture_id, teams_stats, season, league_id):
        """Sauvegarde les statistiques des joueurs."""
        try:
            if not teams_stats:
                return False

            processed_teams = [self.process_team_stats(team_data) for team_data in teams_stats]
            match_ref = self.get_match_ref(season, league_id, fixture_id)
            
            match_ref.update({
                'players_stats': processed_teams,
                'players_stats_updated_at': datetime.now().isoformat()
            })
            
            print(f"💾 Statistiques des joueurs sauvegardées pour le match {fixture_id}")
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
                            'has_players_stats': 'players_stats' in fixture_data
                        })
        
        return matches

    def sync_finished_matches(self):
        """Synchronise les statistiques des joueurs pour les matchs terminés."""
        finished_matches = self.get_matches_by_status(MatchStatus.FINISHED_STATUSES)
        matches_without_stats = [m for m in finished_matches if not m['has_players_stats']]
        total = len(matches_without_stats)
        
        if not total:
            print("ℹ️ Aucun match terminé sans statistiques joueurs")
            return 0
        
        print(f"📊 Synchronisation des statistiques joueurs pour {total} match(s)")
        updated = 0
        
        for match in matches_without_stats:
            if self.sync_match_players_stats(
                match['fixture_id'],
                match['season'],
                match['league_id']
            ):
                updated += 1
        
        print(f"✅ {updated}/{total} matchs synchronisés")
        return updated

    def update_live_matches(self):
        """Met à jour les statistiques des joueurs pour les matchs en cours."""
        live_matches = self.get_matches_by_status(MatchStatus.LIVE_STATUSES)
        total = len(live_matches)
        
        if not total:
            print("ℹ️ Aucun match en cours")
            return 0
        
        print(f"🔄 Mise à jour des statistiques joueurs pour {total} match(s)")
        updated = 0
        
        for match in live_matches:
            if self.sync_match_players_stats(
                match['fixture_id'],
                match['season'],
                match['league_id']
            ):
                updated += 1
        
        print(f"✅ {updated}/{total} matchs mis à jour")
        return updated

    def sync_match_players_stats(self, fixture_id, season, league_id):
        """Synchronise les statistiques des joueurs pour un match."""
        stats = self.fetch_players_stats(fixture_id)
        if stats:
            return self.save_players_stats(fixture_id, stats, season, league_id)
        return False

    def clear_players_stats(self, matches=None):
        """Supprime les statistiques des joueurs."""
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
                match_ref.child('players_stats').delete()
                match_ref.child('players_stats_updated_at').delete()
                cleared += 1
            
            print(f"✅ Statistiques joueurs supprimées pour {cleared} match(s)")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la suppression: {str(e)}")
            return False

