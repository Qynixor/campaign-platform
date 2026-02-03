from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Campaign, Profile
from .models import Blog

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


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
    protocol = "https"  # Ensure HTTPS is used

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
    protocol = "https"  # Ensure HTTPS is used

    def items(self):
        # Fetch all profiles that should be included in the sitemap
        return Profile.objects.filter(user__is_active=True)  # Example condition, adjust as needed

    def lastmod(self, obj):
        # Use a timestamp field to determine the last modification date
        return obj.user.date_joined  # Or a different field indicating last profile update

    def location(self, obj):
        # Generate the URL for the profile
        return reverse('profile_view', args=[obj.user.username])


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        # Only published blog posts
        return Blog.objects.filter(is_published=True)

    def lastmod(self, obj):
        # Use updated_at if you have it, otherwise created_at
        return obj.updated_at if hasattr(obj, "updated_at") else obj.created_at

    def location(self, obj):
        # Blog detail URL
        return reverse('blog_detail', args=[obj.slug])
