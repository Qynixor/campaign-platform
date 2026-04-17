"""
URL configuration for buskx project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

"""
URL configuration for rallynex project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
import json
import os


def service_worker_view(request):
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    with open(sw_path, 'r') as f:
        sw_content = f.read()
    return HttpResponse(sw_content, content_type='application/javascript')

def offline_view(request):
    return render(request, 'offline.html')


urlpatterns = [

    # PWA URLs - Must be at root level
  
    path('sw.js', service_worker_view, name='service_worker'),
    path('offline/', offline_view, name='offline'),

    # Admin
    path('admin/', admin.site.urls),
    
    # Main app - includes all core functionality
    path('', include('main.urls')),
    
    # Accounts app (if you have separate accounts app)
    # path('accounts/', include('accounts.urls')),
    
    # TinyMCE (for blog content editor)
    path('tinymce/', include('tinymce.urls')),
    
    # Favicon redirect
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Django Debug Toolbar (if installed)
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Custom error handlers
handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'
handler403 = 'main.views.handler403'