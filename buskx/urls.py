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

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from main.sitemaps import StaticViewSitemap, CampaignSitemap,ProfileSitemap,BlogSitemap
from main import views as main_views
from accounts import views as accounts_views
from django.contrib.sitemaps.views import sitemap
from django.views.generic import RedirectView


sitemaps = {
    'static': StaticViewSitemap,
    'campaigns': CampaignSitemap,
    'profiles': ProfileSitemap,
    'blogs': BlogSitemap,
}



urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/password/reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('', include('accounts.urls')),
    path('', include('main.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', accounts_views.index, name='index'),
    path('privacy-policy/', main_views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', main_views.terms_of_service, name='terms_of_service'),
    

    path('robots.txt', main_views.robots_txt),
    path("favicon.ico", RedirectView.as_view(
        url=settings.STATIC_URL + "favicon.ico",
        permanent=True
    )),
]

# Configuring URL patterns for serving media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


    