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
            # Main pages
            ('landing', None, 1.0),
            ('conversion_start', None, 0.9),  # ← ADD THIS LINE
            ('about', None, 0.5),
            ('privacy', None, 0.3),
            ('terms', None, 0.3),
            ('faq', None, 0.5),
            ('contact', None, 0.5),
            ('discover', None, 0.8),
            
            # Blog pages
            ('blog_index', None, 0.8),
            ('blog_instagram', '2026-06-07', 0.6),
            ('blog_posts_not_journeys', '2026-06-07', 0.65),
            ('blog_challenge_product', '2026-06-07', 0.65),
            ('blog_journey_content', '2026-06-07', 0.65),
            ('blog_scattered_posts', '2026-06-07', 0.65),
            ('blog_buried_asset', '2026-06-07', 0.7),
            ('blog_blind_spot', '2026-06-07', 0.7),
            ('blog_challenge_fails', '2026-06-07', 0.75),
            ('blog_journey_page', '2026-06-07', 0.75),
            ('blog_challenge_lost', '2026-06-07', 0.75),
            
            # Template store
            ('template_store', None, 0.7),
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
        return Journey.objects.filter(is_public=True, is_active=True)

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