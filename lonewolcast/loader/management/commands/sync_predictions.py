# sync_predictions.py
from django.core.management.base import BaseCommand
from loader.prediction_service import PredictionService

class Command(BaseCommand):
    help = """
    Synchronise les prédictions des matchs. Options disponibles:
    --all : Synchronise tous les matchs sans prédiction
    --upcoming : Synchronise uniquement les matchs à venir (NS, PST, TBD)
    Sans option : Synchronise tous les matchs sans prédiction (comportement par défaut)
    """

    def add_arguments(self, parser):
        # Arguments mutuellement exclusifs
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--all',
            action='store_true',
            help='Synchronise tous les matchs sans prédiction'
        )
        group.add_argument(
            '--upcoming',
            action='store_true',
            help='Synchronise uniquement les matchs à venir (NS, PST, TBD)'
        )

    def handle(self, *args, **options):
        try:
            service = PredictionService()

            # Si --upcoming est spécifié, on ne traite que les matchs à venir
            if options['upcoming']:
                self.stdout.write(
                    self.style.HTTP_INFO("🔄 Recherche des matchs à venir sans prédiction...")
                )
                matches = service.get_upcoming_matches_without_prediction()
                match_type = "à venir"
            # Sinon (--all ou aucune option), on traite tous les matchs
            else:
                self.stdout.write(
                    self.style.HTTP_INFO("🔄 Recherche des matchs sans prédiction...")
                )
                matches = service.get_matches_without_prediction()
                match_type = "sans prédiction"
            
            if not matches:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Tous les matchs {match_type} ont déjà des prédictions")
                )
                return
                
            total = len(matches)
            self.stdout.write(
                self.style.HTTP_INFO(f"📝 {total} match(s) {match_type} trouvé(s)")
            )
            
            synced = service.sync_predictions(matches)
            
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Synchronisation terminée : {synced}/{total} prédictions ajoutées")
            )
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'❌ Erreur lors de la synchronisation: {str(e)}')
            )