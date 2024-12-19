from django.core.management.base import BaseCommand
from loader.players_stats_service import PlayersStatsService

class Command(BaseCommand):
    help = """
    Gestion des statistiques des joueurs:
    
    Commandes disponibles:
        --sync   : Synchronise les statistiques des joueurs pour les matchs terminés
        --live   : Met à jour les statistiques des joueurs pour les matchs en cours
        --clear  : Supprime toutes les statistiques des joueurs
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--sync',
            action='store_true',
            help='Synchronise les statistiques des joueurs des matchs terminés'
        )
        group.add_argument(
            '--live',
            action='store_true',
            help='Met à jour les statistiques des joueurs des matchs en cours'
        )
        group.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les statistiques des joueurs'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = PlayersStatsService()

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
        self.stdout.write(
            self.style.HTTP_INFO('🔄 Synchronisation des statistiques des joueurs...')
        )
        updated = service.sync_finished_matches()
        self.stdout.write(
            self.style.SUCCESS(f'✅ {updated} matchs synchronisés')
        )

    def handle_update_live(self, service):
        self.stdout.write(
            self.style.HTTP_INFO('🔄 Mise à jour des statistiques des joueurs en cours...')
        )
        updated = service.update_live_matches()
        self.stdout.write(
            self.style.SUCCESS(f'✅ {updated} matchs mis à jour')
        )

    def handle_clear(self, service, force):
        if not force:
            confirm = input('⚠️ Voulez-vous vraiment supprimer toutes les statistiques des joueurs ? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

        self.stdout.write(self.style.WARNING('🗑️ Suppression des statistiques des joueurs...'))
        if service.clear_players_stats():
            self.stdout.write(self.style.SUCCESS('✅ Statistiques des joueurs supprimées'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))