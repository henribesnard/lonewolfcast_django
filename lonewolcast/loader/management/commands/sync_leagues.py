from django.core.management.base import BaseCommand
from loader.league_service import LeagueService

class Command(BaseCommand):
    help = """
    Gestion des leagues de football:
    1. Synchronisation des leagues
    2. Suppression de la base de données
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Vider la base de données des leagues'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = LeagueService()

        try:
            # Gestion de la suppression de la base
            if options['clear']:
                return self.handle_clear_database(service, options['force'])

            # Synchronisation des leagues
            return self.handle_sync_leagues(service)

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Erreur inattendue: {str(e)}')
            )

    def handle_clear_database(self, service, force):
        """Gère la suppression de la base de données."""
        if not force:
            confirm = input('⚠️  Êtes-vous sûr de vouloir vider la base des leagues ? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

        self.stdout.write(self.style.WARNING('🗑️  Suppression des leagues en cours...'))
        if service.clear_database():
            self.stdout.write(self.style.SUCCESS('✅ Base des leagues vidée avec succès'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))

    def handle_sync_leagues(self, service):
        """Gère la synchronisation des leagues."""
        self.stdout.write(self.style.HTTP_INFO('🔄 Synchronisation des leagues en cours...'))
        
        if service.sync_leagues():
            self.stdout.write(self.style.SUCCESS('✅ Synchronisation des leagues terminée'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la synchronisation'))