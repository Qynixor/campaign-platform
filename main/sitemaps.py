"""
Sitemap configuration for Rallynex
Tells Google which pages to index and how often to check them
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Journey, Profile

class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return [
            # Main pages - documentation-first
            ('landing', None, 1.0),      # Home page - highest priority
            ('discover', None, 0.8),      # Discover journeys
            ('about', None, 0.5),         # About page
            ('privacy', None, 0.3),       # Privacy policy (noindex in template)
            ('terms', None, 0.3),         # Terms (noindex in template)
            ('contact', None, 0.5),       # Contact page
            # ('conversion_start', None, 0.9),  # REMOVED - doesn't exist
            # ('faq', None, 0.5),                # REMOVED - FAQ content moved to contact AI
            # ('blog_index', None, 0.8),        # REMOVED - blog pages removed
            # All blog specific pages removed
            # ('template_store', None, 0.7),     # REMOVED - template store removed
        ]

    def location(self, item):
        return reverse(item[0])

    def lastmod(self, item):
        if len(item) > 1 and item[1]:
            from datetime import date
            return date.fromisoformat(item[1])
        return None

    def priority(self, item):
        if len(item) > 2:
            return item[2]
        return 0.5


class JourneySitemap(Sitemap):
    """Sitemap for all public journeys"""
    changefreq = "daily"
    priority = 0.9

    def items(self):
        # Use privacy_status instead of is_public
        return Journey.objects.filter(privacy_status='public', is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/j/{obj.slug}/"


class CreatorProfileSitemap(Sitemap):
    """Sitemap for public creator profiles"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Profile.objects.filter(user__is_active=True)

    def lastmod(self, obj):
        return obj.user.date_joined

    def location(self, obj):
        return f"/@{obj.user.username}/"