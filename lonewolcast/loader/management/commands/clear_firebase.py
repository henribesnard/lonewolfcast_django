# clear_firebase.py
from django.core.management.base import BaseCommand
from firebase_admin import db
import time

class Command(BaseCommand):
    help = 'Efface toutes les données de la base Firebase'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la suppression sans confirmation',
        )
        parser.add_argument(
            '--collection',
            type=str,
            help='Nom spécifique de la collection à vider (par défaut: matches)',
            default='matches'
        )

    def handle(self, *args, **options):
        collection = options['collection']
        force = options['force']
        
        self.stdout.write(
            self.style.WARNING(f'\n⚠️  ATTENTION: Vous êtes sur le point de supprimer toutes les données de la collection "{collection}"')
        )
        
        if not force:
            confirm = input('\nÊtes-vous sûr de vouloir continuer ? Cette action est irréversible. [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('\nOpération annulée'))
                return
            
            # Double confirmation pour plus de sécurité
            confirm2 = input('\nTapez le nom de la collection pour confirmer la suppression: ')
            if confirm2 != collection:
                self.stdout.write(self.style.SUCCESS('\nOpération annulée - le nom ne correspond pas'))
                return

        try:
            self.stdout.write('\n🗑️  Début de la suppression...')
            start_time = time.time()
            
            # Récupère la référence et supprime les données
            ref = db.reference(collection)
            ref.delete()
            
            elapsed_time = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Suppression réussie en {elapsed_time:.1f} secondes'
                )
            )
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'\n❌ Erreur lors de la suppression: {str(e)}')
            )