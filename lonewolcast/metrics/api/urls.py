from django.urls import path
from .views import ResultsMetricsView

urlpatterns = [
    path('results/', ResultsMetricsView.as_view(), name='results-metrics'),
]
