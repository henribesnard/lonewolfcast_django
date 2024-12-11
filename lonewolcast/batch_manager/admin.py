# batch_manager/admin.py
from django.contrib import admin 
from .models import BatchJob

@admin.register(BatchJob)
class BatchJobAdmin(admin.ModelAdmin):
    list_display = ('command', 'timing', 'start_date', 'is_running', 'last_run')
    list_filter = ('command', 'is_running')