from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, Case, When, Value, BooleanField
from django.http import HttpResponse, HttpResponseServerError, HttpResponseBadRequest, JsonResponse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView
from django.views.generic.edit import DeleteView
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import LoginView
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

import paypalrestsdk
import os
import json
import base64
import time
import logging
import mimetypes
from decimal import Decimal
from dotenv import load_dotenv

from main.models import (
    Profile, Campaign, Comment, Activity, SupportCampaign,
    User, Love, CampaignView,  Notification,Report, NotInterested,
   CampaignProduct, ActivityComment, ActivityLove
)

from main.forms import (
    UserForm, ProfileForm, CampaignForm, CommentForm, ActivityForm,
    SupportForm, CampaignSearchForm, ProfileSearchForm,
     CampaignProductForm, ReportForm, NotInterestedForm,
     ActivityCommentForm,
    UserVerificationForm
)

from main.utils import calculate_similarity

from django.db.models import Count, Q
from itertools import chain
from collections import defaultdict

from main.models import Campaign

from django.db import connection, connections
from django.db.utils import OperationalError
from itertools import chain
from collections import defaultdict
import json
import time
import traceback


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.forms import inlineformset_factory
from django.db import transaction, connection  # Make sure transaction is imported
from django.db.utils import InternalError, OperationalError
from django import forms
from django.urls import reverse
from cloudinary.models import CloudinaryResource
from django.http import JsonResponse
import time
import traceback
from django.shortcuts import render, get_object_or_404
from django.db import connection, transaction
from django.db.models import Count
from django.utils import timezone
from django.db.utils import OperationalError
import json
import time
from collections import defaultdict
from itertools import chain
from django.shortcuts import render
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
import logging
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count, Q, Sum, F
from django.db.models.functions import ExtractDay
from django.utils import timezone
from datetime import timedelta

from main.models import Campaign, BoostedJourney
from main.boost_utils import get_category_boosts, record_boost_impression

logger = logging.getLogger(__name__)

def index(request):
    """
    Homepage/Discover view showing campaigns in various sections
    """
    try:
        # Base queryset - only active campaigns
        base_campaigns = Campaign.objects.filter(is_active=True).select_related('user__user')
        
        # Get all campaign categories for filter chips
        campaign_categories = Campaign.CATEGORY_CHOICES
        
        # ========== TRENDING CAMPAIGNS ==========
        trending_campaigns = base_campaigns.annotate(
            love_count_total=Count('loves', distinct=True),
            follower_count_total=Count('followers', distinct=True),
            trending_score=(
                Count('loves', distinct=True) * 2 +
                Count('followers', distinct=True) * 3
            )
        ).order_by('-love_count_total', '-follower_count_total', '-timestamp')[:15]
        
        # ========== RISING STARS ==========
        fourteen_days_ago = timezone.now() - timedelta(days=14)
        rising_campaigns = base_campaigns.filter(
            timestamp__gte=fourteen_days_ago,
            followers__isnull=False
        ).annotate(
            love_count_total=Count('loves', distinct=True),
            follower_count_total=Count('followers', distinct=True),
            days_old=ExtractDay(timezone.now() - F('timestamp')),
            growth_rate=Count('followers', distinct=True) * 100 / 
                       (ExtractDay(timezone.now() - F('timestamp')) + 1)
        ).filter(
            follower_count_total__gte=2
        ).order_by('-growth_rate', '-timestamp')[:15]
        
        # ========== FASTEST GROWING ==========
        seven_days_ago = timezone.now() - timedelta(days=7)
        fastest_growing_campaigns = base_campaigns.annotate(
            recent_followers=Count(
                'campaign_follows',
                filter=Q(campaign_follows__followed_at__gte=seven_days_ago),
                distinct=True
            ),
            follower_growth=Count(
                'campaign_follows',
                filter=Q(campaign_follows__followed_at__gte=seven_days_ago),
                distinct=True
            ) * 100 / (Count('followers', distinct=True) + 1)
        ).filter(
            recent_followers__gte=1
        ).order_by('-recent_followers', '-timestamp')[:15]
        
        # ========== MOST COMPLETED ==========
        most_completed_campaigns = base_campaigns.annotate(
            total_watch_count=Count('watch_times', distinct=True),
            completed_count=Count(
                'watch_times',
                filter=Q(watch_times__completed=True),
                distinct=True
            ),
            completion_rate=Count(
                'watch_times',
                filter=Q(watch_times__completed=True),
                distinct=True
            ) * 100 / (Count('watch_times', distinct=True) + 1)
        ).filter(
            total_watch_count__gte=5
        ).order_by('-completion_rate', '-timestamp')[:15]
        
        # ========== MOST WATCHED ==========
        most_watched_campaigns = base_campaigns.annotate(
            total_watch_time=Sum('watch_times__watch_time_seconds'),
            watch_count=Count('watch_times', distinct=True),
            avg_watch_time=Sum('watch_times__watch_time_seconds') / 
                          (Count('watch_times', distinct=True) + 1)
        ).filter(
            watch_count__gte=3
        ).order_by('-avg_watch_time', '-timestamp')[:15]
        
        # ========== MOST SAVED ==========
        most_saved_campaigns = base_campaigns.annotate(
            save_count=Count('saves', distinct=True)
        ).filter(
            save_count__gte=1
        ).order_by('-save_count', '-timestamp')[:15]
        
        # ========== SUGGESTED CAMPAIGNS ==========
        if request.user.is_authenticated:
            excluded_campaigns = Campaign.objects.filter(
                Q(followers=request.user) | 
                Q(loves__user=request.user)
            ).values_list('id', flat=True)
            
            user_categories = Campaign.objects.filter(
                Q(loves__user=request.user) |
                Q(followers=request.user)
            ).values_list('category', flat=True).distinct()
            
            if user_categories:
                suggested_campaigns = base_campaigns.filter(
                    category__in=user_categories
                ).exclude(id__in=excluded_campaigns)
            else:
                suggested_campaigns = base_campaigns.exclude(
                    id__in=excluded_campaigns
                ).order_by('-timestamp')
            
            suggested_campaigns = suggested_campaigns.annotate(
                relevance_score=Count('loves') + Count('followers') * 2
            ).order_by('-relevance_score', '-timestamp')[:15]
        else:
            thirty_days_ago = timezone.now() - timedelta(days=30)
            suggested_campaigns = base_campaigns.filter(
                activity__timestamp__gte=thirty_days_ago
            ).distinct().order_by('-timestamp')[:15]
        
        # ========== NEW CAMPAIGNS ==========
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_campaigns = base_campaigns.filter(
            timestamp__gte=thirty_days_ago
        ).order_by('-timestamp')[:15]
        
        # ========== CATEGORY SECTIONS WITH SPONSORED ==========
        category_popular = {}
        for category_value, category_label in campaign_categories:
            # Get ONLY category placement boosts for this specific category
            sponsored_campaigns = get_category_boosts(category_value, limit=3)
            
            # Record impressions
            sponsored_ids = []
            for item in sponsored_campaigns:
                record_boost_impression(item['boost'], request, f'category_{category_value}')
                sponsored_ids.append(item['campaign'].id)
            
            # Get organic campaigns (excluding sponsored)
            organic_campaigns = base_campaigns.filter(
                category=category_value
            ).exclude(
                id__in=sponsored_ids
            ).annotate(
                engagement_score=Count('loves', distinct=True) + 
                                 (Count('followers', distinct=True) * 2)
            ).order_by('-engagement_score', '-timestamp')[:8]
            
            # Only add if there are campaigns
            if sponsored_campaigns or organic_campaigns.exists():
                category_popular[category_value] = {
                    'sponsored': sponsored_campaigns,
                    'organic': organic_campaigns,
                    'label': category_label,
                    'sponsored_count': len(sponsored_campaigns),
                    'total_count': len(sponsored_campaigns) + organic_campaigns.count()
                }
        
        # ========== FEATURED SPOT CAMPAIGNS ==========
        from main.boost_utils import get_featured_spot_campaigns
        featured_spot_campaigns = get_featured_spot_campaigns(limit=5)
        
        for item in featured_spot_campaigns:
            if item.get('type') == 'boosted' and 'boost' in item:
                record_boost_impression(
                    item['boost'],
                    request,
                    'featured_spot'
                )
        
        # ========== CONTEXT FOR TEMPLATE ==========
        context = {
            # Category choices for filter chips
            'campaign_categories': campaign_categories,
            
            # New discovery sections
            'trending_campaigns': trending_campaigns,
            'rising_campaigns': rising_campaigns,
            'fastest_growing_campaigns': fastest_growing_campaigns,
            'most_completed_campaigns': most_completed_campaigns,
            'most_watched_campaigns': most_watched_campaigns,
            'most_saved_campaigns': most_saved_campaigns,
            
            # Original sections
            'suggested_campaigns': suggested_campaigns,
            'new_campaigns': new_campaigns,
            'category_popular': category_popular,
            'featured_spot_campaigns': featured_spot_campaigns,
            
            # Stats
            'total_campaigns': base_campaigns.count(),
            'total_active_changemakers': Campaign.objects.values('user').distinct().count(),
        }
        
        return render(request, 'accounts/index.html', context)
    
    except Exception as e:
        logger.error(f"Error in index view: {str(e)}", exc_info=True)
        context = {
            'campaign_categories': Campaign.CATEGORY_CHOICES,
            'trending_campaigns': [],
            'rising_campaigns': [],
            'fastest_growing_campaigns': [],
            'most_completed_campaigns': [],
            'most_watched_campaigns': [],
            'most_saved_campaigns': [],
            'suggested_campaigns': [],
            'new_campaigns': [],
            'category_popular': {},
            'featured_spot_campaigns': [],
            'total_campaigns': 0,
            'total_active_changemakers': 0,
            'error_message': "Unable to load campaigns at this time."
        }
        return render(request, 'accounts/index.html', context)


def track_category_impression(request):
    """Track category sponsored impressions"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        boost_id = data.get('boost_id')
        category = data.get('category')
        
        from main.models import BoostedJourney
        from main.boost_utils import record_boost_impression
        
        try:
            boost = BoostedJourney.objects.get(id=boost_id)
            record_boost_impression(boost, request, f"category_{category}")
            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Error tracking category impression: {e}")
            return HttpResponse(status=400)
    return HttpResponse(status=405)


def track_featured_impression(request):
    """Track featured spot impressions"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        boost_id = data.get('boost_id')
        
        from main.models import BoostedJourney
        from main.boost_utils import record_boost_impression
        
        try:
            boost = BoostedJourney.objects.get(id=boost_id)
            record_boost_impression(boost, request, 'featured_spot')
            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Error tracking featured impression: {e}")
            return HttpResponse(status=400)
    return HttpResponse(status=405)


# ===== LAZY-LOADED SECTION VIEWS =====

def section_trending(request):
    """Return HTML for trending section"""
    campaigns = Campaign.objects.filter(is_active=True).annotate(
        love_count_total=Count('loves', distinct=True),
        follower_count_total=Count('followers', distinct=True),
        trending_score=(
            Count('loves', distinct=True) * 2 +
            Count('followers', distinct=True) * 3
        )
    ).order_by('-love_count_total', '-follower_count_total', '-timestamp')[:8]
    
    html = render_to_string('sections/trending_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_rising(request):
    """Return HTML for rising stars section"""
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    
    campaigns = Campaign.objects.filter(
        is_active=True,
        timestamp__gte=fourteen_days_ago
    ).annotate(
        love_count_total=Count('loves', distinct=True),
        follower_count_total=Count('followers', distinct=True),
        days_old=ExtractDay(timezone.now() - F('timestamp')),
        growth_rate=Count('followers', distinct=True) * 100 / 
                   (ExtractDay(timezone.now() - F('timestamp')) + 1)
    ).filter(
        follower_count_total__gte=2
    ).order_by('-growth_rate', '-timestamp')[:8]
    
    html = render_to_string('sections/rising_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_fastest(request):
    """Return HTML for fastest growing section"""
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    campaigns = Campaign.objects.filter(is_active=True).annotate(
        recent_followers=Count(
            'campaign_follows',
            filter=Q(campaign_follows__followed_at__gte=seven_days_ago),
            distinct=True
        ),
        follower_growth=Count(
            'campaign_follows',
            filter=Q(campaign_follows__followed_at__gte=seven_days_ago),
            distinct=True
        ) * 100 / (Count('followers', distinct=True) + 1)
    ).filter(
        recent_followers__gte=1
    ).order_by('-recent_followers', '-timestamp')[:8]
    
    html = render_to_string('sections/fastest_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_most_completed(request):
    """Return HTML for most completed section"""
    campaigns = Campaign.objects.filter(is_active=True).annotate(
        total_watch_count=Count('watch_times', distinct=True),
        completed_count=Count(
            'watch_times',
            filter=Q(watch_times__completed=True),
            distinct=True
        ),
        completion_rate=Count(
            'watch_times',
            filter=Q(watch_times__completed=True),
            distinct=True
        ) * 100 / (Count('watch_times', distinct=True) + 1)
    ).filter(
        total_watch_count__gte=5
    ).order_by('-completion_rate', '-timestamp')[:8]
    
    html = render_to_string('sections/completed_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_most_watched(request):
    """Return HTML for most watched section"""
    campaigns = Campaign.objects.filter(is_active=True).annotate(
        total_watch_time=Sum('watch_times__watch_time_seconds'),
        watch_count=Count('watch_times', distinct=True),
        avg_watch_time=Sum('watch_times__watch_time_seconds') / 
                      (Count('watch_times', distinct=True) + 1)
    ).filter(
        watch_count__gte=3
    ).order_by('-avg_watch_time', '-timestamp')[:8]
    
    html = render_to_string('sections/watched_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_most_saved(request):
    """Return HTML for most saved section"""
    campaigns = Campaign.objects.filter(is_active=True).annotate(
        save_count=Count('saves', distinct=True)
    ).filter(
        save_count__gte=1
    ).order_by('-save_count', '-timestamp')[:8]
    
    html = render_to_string('sections/saved_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_suggested(request):
    """Return HTML for suggested section"""
    base_campaigns = Campaign.objects.filter(is_active=True)
    
    if request.user.is_authenticated:
        excluded_campaigns = Campaign.objects.filter(
            Q(followers=request.user) | 
            Q(loves__user=request.user)
        ).values_list('id', flat=True)
        
        user_categories = Campaign.objects.filter(
            Q(loves__user=request.user) |
            Q(followers=request.user)
        ).values_list('category', flat=True).distinct()
        
        if user_categories:
            campaigns = base_campaigns.filter(
                category__in=user_categories
            ).exclude(id__in=excluded_campaigns)
        else:
            campaigns = base_campaigns.exclude(id__in=excluded_campaigns).order_by('-timestamp')
        
        campaigns = campaigns.annotate(
            relevance_score=Count('loves') + Count('followers') * 2
        ).order_by('-relevance_score', '-timestamp')[:8]
    else:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        campaigns = base_campaigns.filter(
            activity__timestamp__gte=thirty_days_ago
        ).distinct().order_by('-timestamp')[:8]
    
    html = render_to_string('sections/suggested_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_new_causes(request):
    """Return HTML for new causes section"""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    campaigns = Campaign.objects.filter(
        is_active=True,
        timestamp__gte=thirty_days_ago
    ).order_by('-timestamp')[:8]
    
    html = render_to_string('sections/new_section.html', {
        'campaigns': campaigns
    }, request=request)
    
    return HttpResponse(html)


def section_category(request, category):
    """Return HTML for category section"""
    from main.boost_utils import get_category_boosts
    
    # Get sponsored campaigns
    sponsored_campaigns = get_category_boosts(category, limit=2)
    sponsored_ids = [item['campaign'].id for item in sponsored_campaigns]
    
    # Get organic campaigns
    organic_campaigns = Campaign.objects.filter(
        is_active=True,
        category=category
    ).exclude(
        id__in=sponsored_ids
    ).annotate(
        engagement_score=Count('loves', distinct=True) + 
                         (Count('followers', distinct=True) * 2)
    ).order_by('-engagement_score', '-timestamp')[:5]
    
    category_label = dict(Campaign.CATEGORY_CHOICES).get(category, category)
    
    html = render_to_string('sections/category_section.html', {
        'sponsored_campaigns': sponsored_campaigns,
        'organic_campaigns': organic_campaigns,
        'category_value': category,
        'category_label': category_label,
        'sponsored_count': len(sponsored_campaigns),
        'total_count': len(sponsored_campaigns) + organic_campaigns.count()
    }, request=request)
    
    return HttpResponse(html)



def home(request):
    # Your view logic here...
    return render(request, 'accounts/home.html', {})




def face(request):
    if request.user.is_authenticated:
        user_profile = get_object_or_404(Profile, user=request.user)
    else:
        user_profile = None  # Handle the case where the user is not authenticated or no profile is found

    context = {'user_profile': user_profile}
    return render(request, 'accounts/face.html', context)


from django.http import JsonResponse
from django.contrib.auth.models import User
import random

def check_username(request):
    username = request.GET.get("username", "").strip()

    if len(username) < 3:
        return JsonResponse({"available": False, "suggestions": []})

    # Check if username exists
    exists = User.objects.filter(username=username).exists()

    if not exists:
        return JsonResponse({"available": True})

    # Generate fun, memorable suggestions
    adjectives = ["Cool", "Smart", "Happy", "Brave", "Fast", "Creative", "Mighty", "Lucky", "Shiny", "Bright"]
    suggestions = []

    for _ in range(5):
        adj = random.choice(adjectives)
        num = random.randint(10, 99)  # 2-digit number → easier to remember
        suggestions.append(f"{adj}{username}{num}")  # adjective first for readability

    return JsonResponse({"available": False, "suggestions": suggestions})
