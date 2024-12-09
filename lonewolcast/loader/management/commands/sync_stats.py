from django.core.management.base import BaseCommand
from loader.statistiques_service import StatsService
import time

class Command(BaseCommand):
    help = """
    Gestion des statistiques des matchs.
    Commandes disponibles :
    sync_stats : Synchronise les stats des matchs terminés qui n'en ont pas
    sync_stats --live : Met à jour les stats des matchs en cours
    sync_stats --force : Force la mise à jour des stats de tous les matchs terminés
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--live',
            action='store_true',
            help='Met à jour les statistiques des matchs en cours'
        )
        group.add_argument(
            '--force',
            action='store_true',
            help='Force la mise à jour des statistiques de tous les matchs terminés'
        )

    def handle(self, *args, **options):
        try:
            start_time = time.time()
            service = StatsService()

            if options['live']:
                self.stdout.write(
                    self.style.HTTP_INFO("🔄 Recherche des matchs en cours...")
                )
                matches = service.get_live_matches()
                match_type = "en cours"
            elif options['force']:
                self.stdout.write(
                    self.style.HTTP_INFO("🔄 Recherche de tous les matchs terminés...")
                )
                matches = service.get_all_finished_matches()
                match_type = "terminés"
            else:
                self.stdout.write(
                    self.style.HTTP_INFO("🔄 Recherche des matchs terminés sans statistiques...")
                )
                matches = service.get_finished_matches_without_stats()
                match_type = "terminés sans statistiques"

            if not matches:
                self.stdout.write(
                    self.style.SUCCESS(f"ℹ️ Aucun match {match_type} trouvé")
                )
                return

            total = len(matches)
            self.stdout.write(
                self.style.HTTP_INFO(f"📝 {total} match(s) {match_type} trouvé(s)")
            )

            if options['force']:
                confirm = input(f'\n⚠️  Vous allez mettre à jour les stats de {total} matchs. Continuer ? [y/N]: ')
                if confirm.lower() != 'y':
                    self.stdout.write(self.style.SUCCESS('\nOpération annulée'))
                    return

            synced = service.sync_stats(matches)
            elapsed_time = time.time() - start_time

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Synchronisation terminée en {elapsed_time:.1f} secondes\n"
                    f"Stats synchronisées: {synced}/{total}"
                )
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'❌ Erreur lors de la synchronisation: {str(e)}')
            )