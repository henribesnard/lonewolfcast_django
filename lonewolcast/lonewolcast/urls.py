from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('batch/', include('batch_manager.urls')),
    # Redirection de la racine vers /batch/
    path('', RedirectView.as_view(url='/batch/', permanent=False)),
]
