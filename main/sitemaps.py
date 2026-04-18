"""
Sitemap configuration for Rallynex
Tells Google which pages to index and how often to check them
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Journey, Blog, User, Profile


class StaticViewSitemap(Sitemap):
    """Static pages that don't change often"""
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return [
            'landing',
            'about',
            'privacy',
            'terms',
            'faq',
            'contact',
            'discover',
            'blog_list',
        ]

    def location(self, item):
        return reverse(item)


class JourneySitemap(Sitemap):
    """All public journeys - your main SEO content"""
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Journey.objects.filter(
            is_public=True, 
            is_active=True
        ).select_related('creator')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('journey_detail', kwargs={'slug': obj.slug})


class BlogSitemap(Sitemap):
    """Published blog posts"""
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Blog.objects.filter(
            status='published'
        ).select_related('author')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('blog_detail', kwargs={'slug': obj.slug})


class CreatorProfileSitemap(Sitemap):
    """Public creator profiles"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # Only profiles that have at least one public journey
        return Profile.objects.filter(
            journeys__is_public=True,
            journeys__is_active=True
        ).distinct().select_related('user')

    def lastmod(self, obj):
        return obj.user.date_joined

    def location(self, obj):
        return reverse('creator_profile', kwargs={'username': obj.user.username})