from django.core.management.base import BaseCommand
from loader.match_service import MatchSyncService

class Command(BaseCommand):
    help = 'Synchronize matches with API-Sports and Firebase'

    def handle(self, *args, **options):
        service = MatchSyncService()
        service.sync_matches()