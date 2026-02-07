
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
            'jobs',
            'events',
            'library_affiliates',
            'news_affiliates',
            'changemakers_view',
            'affiliate_links',
            'platformfund',
            'blog_list',
            'campaign_story_list',
        ]

    def location(self, item):
        return reverse(item)


class CampaignSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        # Fetch all public campaigns
        return Campaign.objects.filter(visibility='public')

    def lastmod(self, obj):
        # Return the timestamp of the last modification
        return obj.timestamp

    def location(self, obj):
        # Generate the URL for the campaign
        return reverse('view_campaign', args=[obj.id])


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
        # Only published blog posts - use status field instead of is_published property
        # Option 1: Filter by status='published'
        return Blog.objects.filter(status='published')
        
        # Option 2: If you also want to ensure published_at is set
        # return Blog.objects.filter(status='published', published_at__isnull=False)
        
        # Option 3: If you want to order by publication date
        # return Blog.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, obj):
        # Use updated_at if available, otherwise created_at
        # Since your model has updated_at, we can use that
        return obj.updated_at

    def location(self, obj):
        # Blog detail URL
        return reverse('blog_detail', args=[obj.slug])