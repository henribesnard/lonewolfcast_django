from django.urls import path
from . import views

app_name = 'batch_manager'

urlpatterns = [
    path('', views.BatchJobListView.as_view(), name='index'),
    path('toggle/<int:pk>/', views.toggle_job, name='toggle'),
]