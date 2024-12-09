from django.core.management.base import BaseCommand
from loader.match_service import MatchService
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = """
    Gestion des matchs de football:
    1. Synchronisation des matchs depuis une date donnée (--date YYYY-MM-DD)
    2. Mise à jour des matchs en cours uniquement (--active)
    3. Suppression de la base de données (--clear)
    """

    def add_arguments(self, parser):
        # Arguments mutuellement exclusifs
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--date',
            type=str,
            help='Date de début de synchronisation (format: YYYY-MM-DD). Par défaut: date du jour',
            default=datetime.now().strftime('%Y-%m-%d')
        )
        group.add_argument(
            '--active',
            action='store_true',
            help='Mettre à jour uniquement les matchs en cours et à venir'
        )
        group.add_argument(
            '--clear',
            action='store_true',
            help='Vider la base de données'
        )

        # Option supplémentaire pour --clear
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = MatchService()

        try:
            # Gestion de la suppression de la base
            if options['clear']:
                return self.handle_clear_database(service, options['force'])

            # Gestion des matchs actifs
            if options['active']:
                return self.handle_active_matches(service)

            # Synchronisation depuis une date
            return self.handle_sync_from_date(service, options['date'])

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Erreur inattendue: {str(e)}')
            )

    def handle_clear_database(self, service, force):
        """Gère la suppression de la base de données."""
        if not force:
            confirm = input('⚠️  Êtes-vous sûr de vouloir vider la base de données ? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

            confirm2 = input('⚠️  Tapez "CONFIRMER" pour confirmer la suppression: ')
            if confirm2 != "CONFIRMER":
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

        self.stdout.write(self.style.WARNING('🗑️  Suppression de la base de données en cours...'))
        if service.clear_database():
            self.stdout.write(self.style.SUCCESS('✅ Base de données vidée avec succès'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))

    def handle_active_matches(self, service):
        """Gère la mise à jour des matchs actifs."""
        self.stdout.write(self.style.HTTP_INFO('🔄 Recherche des matchs actifs...'))
        active_matches = service.get_active_matches()
        
        if not active_matches:
            self.stdout.write(self.style.SUCCESS('ℹ️  Aucun match actif trouvé'))
            return

        total = len(active_matches)
        self.stdout.write(self.style.HTTP_INFO(f'📊 {total} match(s) actif(s) trouvé(s)'))

        updated = service.update_active_matches()
        self.stdout.write(
            self.style.SUCCESS(f'✅ Mise à jour terminée: {updated}/{total} match(s) mis à jour')
        )

    def handle_sync_from_date(self, service, date_str):
        """Gère la synchronisation depuis une date donnée."""
        try:
            # Validation de la date
            start_date = datetime.strptime(date_str, '%Y-%m-%d')
            end_date = datetime.now()

            if start_date > end_date:
                self.stderr.write(
                    self.style.ERROR('La date de début ne peut pas être dans le futur')
                )
                return

            # Calcul du nombre de jours
            days_diff = (end_date - start_date).days + 1
            
            self.stdout.write(
                self.style.HTTP_INFO(
                    f'Début de la synchronisation des matchs du {date_str} au {end_date.strftime("%Y-%m-%d")} '
                    f'({days_diff} jours)'
                )
            )
            
            # Synchronisation jour par jour
            current_date = start_date
            day_count = 1
            
            while current_date <= end_date:
                current_date_str = current_date.strftime('%Y-%m-%d')
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f'\nJour {day_count}/{days_diff} - {current_date_str}'
                    )
                )
                
                service.sync_matches(current_date_str)
                
                current_date += timedelta(days=1)
                day_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSynchronisation terminée pour la période du {date_str} '
                    f'au {end_date.strftime("%Y-%m-%d")}'
                )
            )
            
        except ValueError:
            self.stderr.write(
                self.style.ERROR('Format de date invalide. Utilisez YYYY-MM-DD')
            )