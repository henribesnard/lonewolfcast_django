from django.core.management.base import BaseCommand
from loader.prediction_service import PredictionSyncService
from loader.models import Match


class Command(BaseCommand):
    help = 'Synchronize predictions for all matches with available fixtures'

    def handle(self, *args, **kwargs):
        service = PredictionSyncService()

        # Récupérer tous les matchs pour lesquels on souhaite synchroniser les prédictions
        matches = Match.objects.all()

        for match in matches:
            service.sync_prediction(match.fixture.id)
