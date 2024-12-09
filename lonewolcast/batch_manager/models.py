from django.db import models
from django.utils import timezone

class BatchJob(models.Model):
   COMMAND_CHOICES = [
       ('sync_matches', 'Synchroniser les matchs du jour'),
       ('sync_matches_from_date', 'Synchroniser les matchs depuis une date'),
       ('sync_matches_active', 'Synchroniser les matchs actifs'),
       ('sync_predictions_all', 'Synchroniser toutes les prédictions'),
       ('sync_predictions_upcoming', 'Synchroniser les prédictions à venir'),
       ('sync_stats', 'Synchroniser les stats'),
       ('sync_stats_live', 'Synchroniser les stats des matchs en cours'),
       ('sync_stats_force', 'Synchroniser stats matchs terminés'),
   ]

   command = models.CharField(max_length=50, choices=COMMAND_CHOICES)
   timing = models.IntegerField(null=True, blank=True, help_text='Intervalle en minutes')
   start_date = models.DateField(null=True, blank=True)
   is_running = models.BooleanField(default=False)
   last_run = models.DateTimeField(null=True, blank=True)

   def save(self, *args, **kwargs):
       if self._state.adding:
           self.is_running = False
       super().save(*args, **kwargs)