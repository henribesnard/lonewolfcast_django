import subprocess
import threading
import time
from django.utils import timezone

class BatchRunner:
   _running_tasks = {}
   _command_mapping = {
       'sync_matches': 'sync_matches',
       'sync_matches_from_date': 'sync_matches',
       'sync_matches_active': 'sync_matches',
       'sync_predictions_all': 'sync_predictions',
       'sync_predictions_upcoming': 'sync_predictions',
       'sync_stats': 'sync_stats',
       'sync_stats_live': 'sync_stats',
       'sync_stats_force': 'sync_stats'
   }

   @classmethod
   def init_jobs(cls):
       from .models import BatchJob
       BatchJob.objects.all().update(is_running=False)
       cls._running_tasks = {}

   @classmethod
   def run_command(cls, job):
       while True:
           try:
               job.refresh_from_db()
               if not job.is_running:
                   print(f"Arrêt du job {job.command}")
                   break

               start_time = timezone.now()
               
               cmd = ['python', 'manage.py', cls._command_mapping[job.command]]
               
               if job.command == 'sync_matches_from_date' and job.start_date:
                   cmd.extend(['--date', job.start_date.strftime('%Y-%m-%d')])
               elif 'active' in job.command:
                   cmd.append('--active')
               elif job.command.endswith('_all'):
                   cmd.append('--all')
               elif 'upcoming' in job.command:
                   cmd.append('--upcoming')
               elif 'live' in job.command:
                   cmd.append('--live')
               elif 'force' in job.command:
                   cmd.append('--force')

               print(f"Exécution: {' '.join(cmd)}")
               subprocess.run(cmd, check=True, timeout=3600)
               
               job.last_run = timezone.now()
               job.save()

               if not job.timing:
                   print(f"Job unique {job.command} terminé")
                   job.is_running = False
                   job.save()
                   break

               elapsed = (timezone.now() - start_time).total_seconds()
               wait_time = max(0, (job.timing * 60) - elapsed)
               time.sleep(wait_time)

           except Exception as e:
               print(f"Erreur job {job.command}: {str(e)}")
               time.sleep(60)

   @classmethod
   def start_job(cls, job):
       if job.id in cls._running_tasks:
           return False
       
       job.is_running = True
       job.save()
       
       thread = threading.Thread(
           target=cls.run_command,
           args=(job,),
           name=f"batch-{job.id}-{job.command}",
           daemon=True
       )
       thread.start()
       cls._running_tasks[job.id] = thread
       print(f"Job {job.command} démarré")
       return True

   @classmethod
   def stop_job(cls, job):
       if job.id not in cls._running_tasks:
           return False
       
       print(f"Arrêt demandé pour {job.command}")
       job.is_running = False
       job.save()
       
       if job.id in cls._running_tasks:
           del cls._running_tasks[job.id]
       
       return True