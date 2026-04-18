"""
URL configuration for rallynex project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.staticfiles.finders import find
from django.contrib.sitemaps.views import sitemap
import os

# Import your sitemaps
from main.sitemaps import StaticViewSitemap, JourneySitemap, BlogSitemap, CreatorProfileSitemap

# Sitemap configuration
sitemaps = {
    'static': StaticViewSitemap,
    'journeys': JourneySitemap,
    'blog': BlogSitemap,
    'creators': CreatorProfileSitemap,
}


def service_worker_view(request):
    """Serve service worker from static files with correct MIME type."""
    sw_path = find('main/js/sw.js')
    
    if not sw_path:
        fallback_path = os.path.join(settings.BASE_DIR, 'main', 'static', 'main', 'js', 'sw.js')
        if os.path.exists(fallback_path):
            sw_path = fallback_path
    
    if sw_path and os.path.exists(sw_path):
        with open(sw_path, 'r') as f:
            sw_content = f.read()
        response = HttpResponse(sw_content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache, max-age=0'
        return response
    
    return HttpResponse("Service Worker not found", status=404)


def offline_view(request):
    """Offline fallback page"""
    return render(request, 'offline.html')


def manifest_view(request):
    """Serve manifest.json from static files."""
    manifest_path = find('main/js/manifest.json')
    
    if not manifest_path:
        fallback_path = os.path.join(settings.BASE_DIR, 'main', 'static', 'main', 'js', 'manifest.json')
        if os.path.exists(fallback_path):
            manifest_path = fallback_path
    
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
        return HttpResponse(manifest_content, content_type='application/manifest+json')
    
    return HttpResponse("Manifest not found", status=404)


urlpatterns = [
    # ==================== PWA URLs ====================
    path('sw.js', service_worker_view, name='service_worker'),
    path('offline/', offline_view, name='offline'),
    path('manifest.json', manifest_view, name='manifest'),
    
    # ==================== SEO URLs ====================
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    
    # ==================== Admin ====================
    path('admin/', admin.site.urls),
    
    # ==================== Main App ====================
    path('', include('main.urls')),
    
    # ==================== TinyMCE ====================
    path('tinymce/', include('tinymce.urls')),
    
    # ==================== Favicon ====================
    path('favicon.ico', RedirectView.as_view(url='/static/icons/favicon.ico', permanent=True)),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
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