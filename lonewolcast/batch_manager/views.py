from django.views.generic import ListView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .models import BatchJob
from .tasks import BatchRunner

class BatchJobListView(ListView):
   model = BatchJob
   template_name = 'batch_manager/index.html'
   context_object_name = 'jobs'

   def get_queryset(self):
       return BatchJob.objects.all().order_by('id')

@require_POST 
def toggle_job(request, pk):
   try:
       job = get_object_or_404(BatchJob, pk=pk)
       
       if job.is_running:
           BatchRunner.stop_job(job)
       else:
           BatchRunner.start_job(job)
           
       # Rafraîchir l'état
       job.refresh_from_db()
       
       return JsonResponse({
           'status': 'success',
           'running': job.is_running,
           'message': 'Job {} avec succès'.format('arrêté' if not job.is_running else 'démarré')
       })
       
   except BatchJob.DoesNotExist:
       return JsonResponse({
           'status': 'error',
           'message': 'Job non trouvé'
       }, status=404)
       
   except Exception as e:
       return JsonResponse({
           'status': 'error',
           'message': str(e)
       }, status=400)