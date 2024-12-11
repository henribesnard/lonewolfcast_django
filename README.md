# lonewolfcast_django

# Synchroniser les matchs
python manage.py sync_matches # synchronise les matchs du jour 
python manage.py sync_matches --date 2024-07-01 # synchronise tous les matchs à partir d'une date 
python manage.py sync_matches --active # Mettre à jour uniquement les matchs actifs


# Synchroniser les prédictions
python manage.py sync_predictions # pour tous les matchs qui n'en ont pas 
python manage.py sync_predictions --all  # pour tous les matchs
python manage.py sync_predictions --upcoming # seulement pour les matchs à venir

# Synchoniser les stats 
python manage.py sync_stats
python manage.py sync_stats --live # Synchroniser tous les matchs en cours
python manage.py sync_stats --force  # Synchroniser tous les matchs terminés

# Supprimer la base 
python manage.py clear_firebase # Suppression avec confirmation (recommandé)
python manage.py clear_firebase --force  # Suppression forcée sans confirmation 
python manage.py clear_firebase --collection autre_collection # Suppression d'une collection spécifique 



# créer les batchs 
from datetime import date
from batch_manager.models import BatchJob

# Jobs pour sync_matches
BatchJob.objects.create(command='sync_matches', timing=5)
BatchJob.objects.create(command='sync_matches_from_date', start_date=date(2024, 7, 1))
BatchJob.objects.create(command='sync_matches_active', timing=5)

# Jobs pour sync_predictions
BatchJob.objects.create(command='sync_predictions_all')
BatchJob.objects.create(command='sync_predictions_upcoming', timing=5)

# Jobs pour sync_stats
BatchJob.objects.create(command='sync_stats')
BatchJob.objects.create(command='sync_stats_live', timing=5)
BatchJob.objects.create(command='sync_stats_force')