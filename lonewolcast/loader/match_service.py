import requests
from django.conf import settings
from firebase_admin import db
import time
from datetime import datetime

class MatchService:
    RATE_LIMIT = 450
    DELAY = 60 / RATE_LIMIT

    # Statuts des matchs actifs (non terminés)
    ACTIVE_STATUSES = {
        'TBD', 'NS', '1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT', 'PST', 'LIVE'
    }

    def __init__(self):
        self.headers = {'x-apisports-key': settings.API_SPORTS_KEY}
        self.firebase_ref = db.reference('matches')
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
                print(f"⏳ Limite atteinte, pause de {sleep_time:.1f} secondes")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:
            time.sleep(self.DELAY)

        self.request_count += 1

    def get_season_for_date(self, date_str):
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.year if date.month > 6 else date.year - 1

    def fetch_matches(self, date_str):
        try:
            all_matches = []
            season = self.get_season_for_date(date_str)
            total_leagues = len(settings.LEAGUES)
            
            print(f"📅 Date: {date_str}")
            print(f"🏆 Saison: {season}")
            print(f"🏆 Recherche dans {total_leagues} leagues...")
            
            for idx, league in enumerate(settings.LEAGUES, 1):
                self.wait_for_rate_limit()
                
                print(f"\nTraitement league {league} ({idx}/{total_leagues})")
                
                url = f"{settings.API_SPORTS_BASE_URL}/fixtures"
                params = {
                    'date': date_str,
                    'league': str(league),
                    'season': str(season),
                    'timezone': 'Europe/Paris'
                }
                
                try:
                    response = requests.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    if 'errors' in data and data['errors']:
                        print(f"⚠️ Erreur API pour league {league}: {data['errors']}")
                        continue
                        
                    league_matches = data.get('response', [])
                    
                    if league_matches:
                        print(f"✅ {len(league_matches)} match(s) trouvé(s) pour la league {league}")
                        all_matches.extend(league_matches)
                    else:
                        print(f"ℹ️ Pas de match pour la league {league}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"❌ Erreur réseau pour league {league}: {str(e)}")
                    continue
                
            return all_matches
            
        except Exception as e:
            print(f"❌ Erreur générale: {str(e)}")
            return None

    def fetch_single_match(self, fixture_id):
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

    def process_match_data(self, match_data):
        return {
            'fixture': match_data['fixture'],
            'league': match_data['league'],
            'teams': match_data['teams'],
            'goals': match_data.get('goals', {'home': None, 'away': None}),
            'score': match_data.get('score', {}),
            'updated_at': datetime.now().isoformat()
        }

    def save_to_firebase(self, matches):
        if not matches:
            return False
            
        try:
            for match in matches:
                fixture_id = str(match['fixture']['id'])
                processed_match = self.process_match_data(match)
                self.firebase_ref.child(fixture_id).update(processed_match)
                print(f"💾 Match {fixture_id} sauvegardé")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde Firebase: {str(e)}")
            return False

    def clear_database(self, collection='matches'):
        try:
            ref = db.reference(collection)
            ref.delete()
            return True
        except Exception as e:
            print(f"❌ Erreur suppression Firebase: {str(e)}")
            return False

    def get_active_matches(self):
        try:
            all_matches = self.firebase_ref.get() or {}
            return {
                fixture_id: match_data
                for fixture_id, match_data in all_matches.items()
                if match_data.get('fixture', {}).get('status', {}).get('short') in self.ACTIVE_STATUSES
            }
        except Exception as e:
            print(f"❌ Erreur récupération matchs actifs: {str(e)}")
            return {}

    def sync_matches(self, date_str):
        print(f"🔄 Début synchronisation des matchs pour le {date_str}...")
        start_time = time.time()
        
        matches = self.fetch_matches(date_str)
        
        if not matches:
            print("ℹ️ Aucun match trouvé pour cette date")
            return

        total = len(matches)
        print(f"\n📊 Résumé:")
        print(f"- {total} match(s) trouvé(s) au total")

        if self.save_to_firebase(matches):
            elapsed_time = time.time() - start_time
            print(f"\n✅ Synchronisation réussie en {elapsed_time:.1f} secondes")
            print(f"📈 {total} match(s) synchronisé(s)")
        else:
            print("\n❌ Erreur lors de la synchronisation")

    def update_active_matches(self):
        active_matches = self.get_active_matches()
        total = len(active_matches)
        updated = 0

        print(f"🔄 Mise à jour de {total} match(s) actif(s)...")

        for fixture_id, match_data in active_matches.items():
            updated_data = self.fetch_single_match(fixture_id)
            if updated_data and self.save_to_firebase([updated_data]):
                updated += 1

        print(f"✅ {updated}/{total} match(s) mis à jour")
        return updated

# sync_matches.py
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = '''
    Gestion des matchs de football
    Commandes disponibles:
    - Synchronisation depuis une date
    - Mise à jour des matchs actifs
    - Suppression de la base de données
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date de début de synchronisation (YYYY-MM-DD)',
            default=datetime.now().strftime('%Y-%m-%d')
        )
        parser.add_argument(
            '--active',
            action='store_true',
            help='Mise à jour uniquement des matchs actifs'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Vider la base de données'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = MatchService()

        # Gestion de la suppression
        if options['clear']:
            if not options['force']:
                confirm = input('⚠️ Êtes-vous sûr de vouloir vider la base ? [y/N]: ')
                if confirm.lower() != 'y':
                    self.stdout.write(self.style.SUCCESS('Opération annulée'))
                    return

            if service.clear_database():
                self.stdout.write(self.style.SUCCESS('✅ Base de données vidée'))
            else:
                self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))
            return

        # Mise à jour des matchs actifs
        if options['active']:
            self.stdout.write(self.style.HTTP_INFO('🔄 Mise à jour des matchs actifs...'))
            service.update_active_matches()
            return

        # Synchronisation depuis une date
        try:
            start_date = datetime.strptime(options['date'], '%Y-%m-%d')
            end_date = datetime.now()

            if start_date > end_date:
                self.stderr.write(self.style.ERROR('La date ne peut pas être dans le futur'))
                return

            days_diff = (end_date - start_date).days + 1
            
            self.stdout.write(
                self.style.HTTP_INFO(
                    f'Synchronisation du {start_date.strftime("%Y-%m-%d")} '
                    f'au {end_date.strftime("%Y-%m-%d")} ({days_diff} jours)'
                )
            )
            
            current_date = start_date
            for i in range(days_diff):
                self.stdout.write(
                    self.style.HTTP_INFO(f'\nJour {i+1}/{days_diff}')
                )
                service.sync_matches(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)

        except ValueError:
            self.stderr.write(self.style.ERROR('Format de date invalide (YYYY-MM-DD)'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erreur: {str(e)}'))