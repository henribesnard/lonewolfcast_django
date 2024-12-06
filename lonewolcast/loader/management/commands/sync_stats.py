from django.core.management.base import BaseCommand
from loader.statistiques_service import StatsService
from firebase_admin import db

class Command(BaseCommand):
    help = 'Synchronise les statistiques des matchs en direct ou terminés'

    def handle(self, *args, **kwargs):
        service = StatsService()
        matches_ref = db.reference('matches')
        matches = matches_ref.get() or {}

        self.stdout.write("🔄 Début de la synchronisation des stats...")

        count = 0
        for fixture_id, match_data in matches.items():
            if service.sync_match_stats(fixture_id, match_data):
                count += 1

        self.stdout.write(f"✅ Synchronisation terminée. {count} matchs mis à jour.")