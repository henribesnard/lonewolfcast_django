from django.apps import AppConfig

class BatchManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'batch_manager'

    def ready(self):
        from .tasks import BatchRunner
        BatchRunner.init_jobs()
