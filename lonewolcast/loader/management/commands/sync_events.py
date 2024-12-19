from django.core.management.base import BaseCommand
from loader.events_service import EventService

class Command(BaseCommand):
    help = """
    Gestion des événements des matchs:
    
    Commandes disponibles:
        --sync   : Synchronise les événements des matchs terminés
        --live   : Met à jour les événements des matchs en cours
        --clear  : Supprime tous les événements
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--sync',
            action='store_true',
            help='Synchronise les événements des matchs terminés'
        )
        group.add_argument(
            '--live',
            action='store_true',
            help='Met à jour les événements des matchs en cours'
        )
        group.add_argument(
            '--clear',
            action='store_true',
            help='Supprime tous les événements'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = EventService()

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
        self.stdout.write(self.style.HTTP_INFO('🔄 Synchronisation des événements des matchs terminés...'))
        updated = service.sync_finished_matches()
        self.stdout.write(self.style.SUCCESS(f'✅ {updated} matchs synchronisés'))

    def handle_update_live(self, service):
        self.stdout.write(self.style.HTTP_INFO('🔄 Mise à jour des événements des matchs en cours...'))
        updated = service.update_live_matches()
        self.stdout.write(self.style.SUCCESS(f'✅ {updated} matchs mis à jour'))

    def handle_clear(self, service, force):
        if not force:
            confirm = input('⚠️ Voulez-vous vraiment supprimer tous les événements ? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

        self.stdout.write(self.style.WARNING('🗑️ Suppression des événements...'))
        if service.clear_events():
            self.stdout.write(self.style.SUCCESS('✅ Événements supprimés'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))
