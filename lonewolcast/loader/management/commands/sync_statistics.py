from django.core.management.base import BaseCommand
from loader.statistics_service import StatisticsService
from loader.constants import MatchStatus

class Command(BaseCommand):
    help = """
    Gestion des statistiques globales des matchs:
    
    Commandes disponibles:
        --sync   : Synchronise les statistiques globales des matchs terminés sans statistiques
        --live   : Met à jour les statistiques globales des matchs en cours
        --clear  : Supprime toutes les statistiques globales
            (utiliser --force pour éviter la confirmation)

    Note: Pour les statistiques avec mi-temps (depuis 2024), utilisez sync_statistics_ht
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--sync',
            action='store_true',
            help='Synchronise les statistiques globales des matchs terminés'
        )
        group.add_argument(
            '--live',
            action='store_true',
            help='Met à jour les statistiques globales des matchs en cours'
        )
        group.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les statistiques globales'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = StatisticsService()

        try:
            if options['sync']:
                self.handle_sync_finished(service)
            elif options['live']:
                self.handle_update_live(service)
            elif options['clear']:
                self.handle_clear(service, options['force'])
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erreur: {str(e)}'))

    def handle_sync_finished(self, service):
        """Synchronisation des statistiques globales des matchs terminés."""
        self.stdout.write(
            self.style.HTTP_INFO('🔄 Synchronisation des statistiques globales des matchs terminés...')
        )
        updated = service.sync_finished_matches()
        self.stdout.write(
            self.style.SUCCESS(f'✅ {updated} statistiques globales synchronisées')
        )

    def handle_update_live(self, service):
        """Mise à jour des statistiques globales des matchs en cours."""
        self.stdout.write(
            self.style.HTTP_INFO('🔄 Mise à jour des statistiques globales des matchs en cours...')
        )
        updated = service.update_live_matches()
        self.stdout.write(
            self.style.SUCCESS(f'✅ {updated} statistiques globales mises à jour')
        )

    def handle_clear(self, service, force):
        """Suppression des statistiques globales."""
        if not force:
            confirm = input('⚠️ Voulez-vous vraiment supprimer toutes les statistiques globales ? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

        self.stdout.write(self.style.WARNING('🗑️ Suppression des statistiques globales...'))
        if service.clear_statistics():
            self.stdout.write(self.style.SUCCESS('✅ Statistiques globales supprimées'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))