# buskx/context_processors.py

from django.conf import settings
from django.urls import resolve
from django.utils import timezone

def seo_context(request):
    """Add SEO-related variables to template context"""
    context = {
        'GOOGLE_SITE_VERIFICATION': getattr(settings, 'GOOGLE_SITE_VERIFICATION', ''),
        'YANDEX_VERIFICATION': getattr(settings, 'YANDEX_VERIFICATION', ''),
        'BING_VERIFICATION': getattr(settings, 'BING_VERIFICATION', ''),
        'SITE_URL': request.build_absolute_uri('/'),
    }
    
    # Check if this is a campaign page
    try:
        resolver_match = resolve(request.path_info)
        if 'campaign_id' in resolver_match.kwargs:
            from main.models import Campaign
            campaign_id = resolver_match.kwargs.get('campaign_id')
            try:
                campaign = Campaign.objects.get(id=campaign_id)
                context.update({
                    'campaign_meta_title': campaign.title,
                    'campaign_meta_description': campaign.content[:160] if campaign.content else '',
                    'campaign_og_image': campaign.poster.url if campaign.poster else None,
                    'campaign_url': request.build_absolute_uri(),
                })
            except:
                pass
    except:
        pass
    
    return context


def notification_count(request):
    """Add notification count to context for authenticated users"""
    context = {
        'notification_count': 0
    }
    
    if request.user.is_authenticated:
        try:
            from main.models import Notification
            context['notification_count'] = Notification.objects.filter(
                user=request.user,
                viewed=False,
                is_active=True
            ).count()
        except:
            pass
    
    return context


def site_config(request):
    """Add site-wide configuration variables"""
    return {
        'SITE_NAME': 'Rallynex',
        'SITE_URL': request.build_absolute_uri('/'),
        'SITE_DESCRIPTION': 'Journey-based crowdfunding platform where changemakers share daily video updates to build community and raise funds.',
        'CURRENT_YEAR': timezone.now().year,
    }