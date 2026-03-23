from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Campaign, Profile, Blog


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5
    protocol = "https"

    def items(self):
        return [
            'index',
            'explore_campaigns',
            'privacy_policy',
            'terms_of_service',
            'success_stories',
            'hiw',
            'faq',
            'aboutus',
            'fund',
            'geno',
            'face',
            'blog_list',
            'campaign_story_list',
            'journey',
            'saved_journeys',
        ]

    def location(self, item):
        return reverse(item)


class CampaignSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        # Fetch all active campaigns (no visibility field anymore)
        return Campaign.objects.filter(is_active=True)

    def lastmod(self, obj):
        # Return the timestamp of the last modification
        return obj.timestamp

    def location(self, obj):
        # Generate the URL for the campaign journey page
        return reverse('campaign_journey', args=[obj.id])


class ProfileSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        # Fetch all profiles that should be included in the sitemap
        return Profile.objects.filter(user__is_active=True)

    def lastmod(self, obj):
        # Use a timestamp field to determine the last modification date
        return obj.user.date_joined

    def location(self, obj):
        # Generate the URL for the profile
        return reverse('profile_view', args=[obj.user.username])


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        # Only published blog posts
        return Blog.objects.filter(status='published')

    def lastmod(self, obj):
        # Use updated_at for last modification date
        return obj.updated_at

    def location(self, obj):
        # Blog detail URL
        return reverse('blog_detail', args=[obj.slug])