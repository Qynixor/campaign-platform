"""
Sitemap configuration for Rallynex
Tells Google which pages to index and how often to check them
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.views.generic import RedirectView
from .models import Journey, Profile, JournalEntry


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
        return Journey.objects.filter(privacy_status='public', is_active=True).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/j/{obj.slug}/"


class CreatorProfileSitemap(Sitemap):
    """Sitemap for public creator profiles"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # Order by id to fix UnorderedObjectListWarning
        return Profile.objects.filter(user__is_active=True).order_by('id')

    def lastmod(self, obj):
        return obj.user.date_joined

    def location(self, obj):
        return f"/@{obj.user.username}/"


class JournalSitemap(Sitemap):
    """Sitemap for public journal entries"""
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # Only include public journal entries, ordered to fix warning
        return JournalEntry.objects.filter(is_private=False).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('journal_detail', kwargs={'pk': obj.pk})