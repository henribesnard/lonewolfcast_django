from django.core.management.base import BaseCommand
from firebase_admin import db
import time

class Command(BaseCommand):
    help = 'Efface toutes les données de la base Firebase par lots'

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
        parser.add_argument(
            '--batch-size',
            type=int,
            help='Nombre d\'éléments à supprimer par lot (par défaut: 100)',
            default=100
        )

    def delete_in_batches(self, ref, batch_size):
        """Supprime les données par lots."""
        total_deleted = 0
        while True:
            # Récupère un lot limité de clés
            query = ref.order_by_key().limit_to_first(batch_size)
            data = query.get()
            
            if not data:
                break
                
            # Supprime chaque élément individuellement
            for key in data.keys():
                try:
                    ref.child(key).delete()
                    total_deleted += 1
                    if total_deleted % 10 == 0:  # Affiche la progression tous les 10 éléments
                        self.stdout.write(f"🗑️  {total_deleted} éléments supprimés...")
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f"⚠️  Erreur lors de la suppression de {key}: {str(e)}")
                    )
            
            # Petite pause pour éviter de surcharger Firebase
            time.sleep(1)
        
        return total_deleted

    def handle(self, *args, **options):
        collection = options['collection']
        force = options['force']
        batch_size = options['batch_size']

        self.stdout.write(
            self.style.WARNING(
                f'\n⚠️  ATTENTION: Vous êtes sur le point de supprimer toutes les données '
                f'de la collection "{collection}" par lots de {batch_size}'
            )
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
            self.stdout.write('\n🗑️  Début de la suppression par lots...')
            start_time = time.time()
            
            # Récupère la référence et supprime les données par lots
            ref = db.reference(collection)
            total_deleted = self.delete_in_batches(ref, batch_size)
            
            elapsed_time = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Suppression réussie en {elapsed_time:.1f} secondes\n'
                    f'📊 Total éléments supprimés: {total_deleted}'
                )
            )
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'\n❌ Erreur lors de la suppression: {str(e)}')
            )