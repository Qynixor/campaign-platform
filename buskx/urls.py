"""
URL configuration for rallynex project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.contrib.staticfiles.finders import find
import os


def service_worker_view(request):
    """
    Serve service worker from main/static/main/js/sw.js
    """
    # Try multiple possible locations in order of priority
    sw_paths = [
        os.path.join(settings.BASE_DIR, 'main', 'static', 'main', 'js', 'sw.js'),
        os.path.join(settings.BASE_DIR, 'static', 'main', 'js', 'sw.js'),
        find('main/js/sw.js'),  # Django static finder
    ]
    
    sw_content = None
    for sw_path in sw_paths:
        if sw_path and os.path.exists(sw_path):
            with open(sw_path, 'r') as f:
                sw_content = f.read()
            break
    
    if sw_content is None:
        raise Http404("Service Worker not found at main/static/main/js/sw.js")
    
    response = HttpResponse(sw_content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, max-age=0'
    return response


def offline_view(request):
    """Offline fallback page"""
    return render(request, 'offline.html')


def manifest_view(request):
    """
    Serve manifest.json from main/static/main/js/manifest.json
    """
    manifest_paths = [
        os.path.join(settings.BASE_DIR, 'main', 'static', 'main', 'js', 'manifest.json'),
        os.path.join(settings.BASE_DIR, 'static', 'main', 'js', 'manifest.json'),
        find('main/js/manifest.json'),
    ]
    
    manifest_content = None
    for manifest_path in manifest_paths:
        if manifest_path and os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest_content = f.read()
            break
    
    if manifest_content is None:
        raise Http404("Manifest not found at main/static/main/js/manifest.json")
    
    return HttpResponse(manifest_content, content_type='application/manifest+json')


urlpatterns = [
    # PWA URLs - MUST be at root level
    path('sw.js', service_worker_view, name='service_worker'),
    path('offline/', offline_view, name='offline'),
    path('manifest.json', manifest_view, name='manifest'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Main app - includes all core functionality
    path('', include('main.urls')),
    
    # TinyMCE (for blog content editor)
    path('tinymce/', include('tinymce.urls')),
    
    # Favicon redirect
    path('favicon.ico', RedirectView.as_view(url='/static/main/icons/favicon.ico', permanent=True)),
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