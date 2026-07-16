"""
Sitemap configuration for Rallynex
Tells Google which pages to index and how often to check them
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Journey, Profile, Reflection, Activity


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages - Fitness & Wellness focus"""
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return [
            ('landing', None, 1.0),       # Home page - highest priority
            ('discover', None, 0.8),      # Discover journeys
            ('about', None, 0.5),         # About page
            ('privacy', None, 0.3),       # Privacy policy
            ('terms', None, 0.3),         # Terms
            ('contact', None, 0.5),       # Contact page
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
    """Sitemap for all public fitness & wellness journeys"""
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Journey.objects.filter(
            privacy_status='public', 
            is_active=True
        ).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/j/{obj.slug}/"


class CreatorProfileSitemap(Sitemap):
    """Sitemap for public creator profiles"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Profile.objects.filter(user__is_active=True).order_by('id')

    def lastmod(self, obj):
        return obj.user.date_joined

    def location(self, obj):
        return f"/@{obj.user.username}/"


class ReflectionSitemap(Sitemap):
    """
    Sitemap for public reflections (replaces JournalEntry)
    Reflections are private by default, only public ones are indexed
    """
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Reflection.objects.filter(is_private=False).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('reflection_detail', kwargs={'pk': obj.pk})


class ActivitySitemap(Sitemap):
    """
    Sitemap for public activities (daily logs)
    """
    changefreq = "daily"
    priority = 0.6

    def items(self):
        return Activity.objects.filter(
            journey__privacy_status='public',
            journey__is_active=True,
            is_published=True
        ).order_by('-created_at')[:1000]

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at

    def location(self, obj):
        return f"/j/{obj.journey.slug}/?day={obj.day_number_field}"