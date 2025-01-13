from django.urls import path
from .views import ResultsMetricsView, GoalsMetricsView

urlpatterns = [
    path('results/', ResultsMetricsView.as_view(), name='results-metrics'),
    path('goals/', GoalsMetricsView.as_view(), name='goals-metrics')
]
