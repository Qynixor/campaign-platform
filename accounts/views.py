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
        # Trending based on engagement (loves + followers)
        trending_campaigns = base_campaigns.annotate(
            love_count_total=Count('loves', distinct=True),
            follower_count_total=Count('followers', distinct=True),
        ).order_by('-love_count_total', '-follower_count_total', '-timestamp')[:15]
        
        # ========== SUGGESTED CAMPAIGNS ==========
        # Personalized suggestions based on user's interests
        suggested_campaigns = base_campaigns
        
        if request.user.is_authenticated:
            # Exclude campaigns the user already follows/loves
            excluded_campaigns = Campaign.objects.filter(
                Q(followers=request.user) | 
                Q(loves__user=request.user)
            ).values_list('id', flat=True)
            
            # Get categories the user has interacted with
            user_categories = Campaign.objects.filter(
                Q(loves__user=request.user) |
                Q(followers=request.user)
            ).values_list('category', flat=True).distinct()
            
            if user_categories:
                # Prioritize campaigns from categories the user likes
                suggested_campaigns = base_campaigns.filter(
                    category__in=user_categories
                ).exclude(id__in=excluded_campaigns)
            else:
                # If no interaction history, show recent campaigns
                suggested_campaigns = base_campaigns.exclude(
                    id__in=excluded_campaigns
                ).order_by('-timestamp')
            
            suggested_campaigns = suggested_campaigns.annotate(
                relevance_score=Count('loves') + Count('followers') * 2
            ).order_by('-relevance_score', '-timestamp')[:15]
        else:
            # For non-authenticated users, show recently active campaigns
            thirty_days_ago = timezone.now() - timedelta(days=30)
            suggested_campaigns = base_campaigns.filter(
                activity__timestamp__gte=thirty_days_ago
            ).distinct().order_by('-timestamp')[:15]
        
        # ========== NEW CAMPAIGNS ==========
        # Latest campaigns created in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_campaigns = base_campaigns.filter(
            timestamp__gte=thirty_days_ago
        ).order_by('-timestamp')[:15]
        
        # ========== POPULAR BY CATEGORY ==========
        # Top campaigns in each category
        category_popular = {}
        for category_value, category_label in campaign_categories:
            category_campaigns = base_campaigns.filter(
                category=category_value
            ).annotate(
                engagement_score=Count('loves', distinct=True) + 
                                 (Count('followers', distinct=True) * 2)
            ).order_by('-engagement_score', '-timestamp')[:8]
            
            if category_campaigns.exists():
                category_popular[category_value] = category_campaigns
        
        # ========== CONTEXT FOR TEMPLATE ==========
        context = {
            # Category choices for filter chips
            'campaign_categories': campaign_categories,
            
            # Main sections
            'trending_campaigns': trending_campaigns,
            'suggested_campaigns': suggested_campaigns,
            'new_campaigns': new_campaigns,
            
            # Popular campaigns by category
            'category_popular': category_popular,
            
            # Stats
            'total_campaigns': base_campaigns.count(),
            'total_active_changemakers': Campaign.objects.values('user').distinct().count(),
        }
        
        return render(request, 'accounts/index.html', context)
    
    except Exception as e:
        logger.error(f"Error in index view: {str(e)}", exc_info=True)
        # Return a basic context even if there's an error
        context = {
            'campaign_categories': Campaign.CATEGORY_CHOICES,
            'trending_campaigns': [],
            'suggested_campaigns': [],
            'new_campaigns': [],
            'category_popular': {},
            'total_campaigns': 0,
            'total_active_changemakers': 0,
            'error_message': "Unable to load campaigns at this time."
        }
        return render(request, 'accounts/index.html', context)
# Optional helper functions for more sophisticated suggestions

def get_user_interests(user):
    """
    Analyze user's interests based on their interactions
    """
    if not user.is_authenticated:
        return {}
    
    # Get categories from campaigns they've loved
    loved_categories = Campaign.objects.filter(
        loves__user=user
    ).values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get categories from campaigns they follow
    followed_categories = Campaign.objects.filter(
        followers=user
    ).values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get categories from campaigns they've commented on
    commented_categories = Campaign.objects.filter(
        comments__user__user=user
    ).values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Combine and weight interests
    interests = {}
    
    for item in loved_categories:
        interests[item['category']] = interests.get(item['category'], 0) + (item['count'] * 3)
    
    for item in followed_categories:
        interests[item['category']] = interests.get(item['category'], 0) + (item['count'] * 2)
    
    for item in commented_categories:
        interests[item['category']] = interests.get(item['category'], 0) + (item['count'] * 1)
    
    return dict(sorted(interests.items(), key=lambda x: x[1], reverse=True))


def get_trending_campaigns(days=7, limit=15):
    """
    Get campaigns that are trending based on recent engagement
    """
    since_date = timezone.now() - timedelta(days=days)
    
    return Campaign.objects.filter(
        is_active=True
    ).annotate(
        recent_loves=Count('loves', filter=Q(loves__timestamp__gte=since_date), distinct=True),
        recent_follows=Count('followers', filter=Q(campaign_follows__followed_at__gte=since_date), distinct=True),
        recent_activities=Count('activity', filter=Q(activity__timestamp__gte=since_date), distinct=True),
        trending_score=(
            Count('loves', filter=Q(loves__timestamp__gte=since_date), distinct=True) * 3 +
            Count('followers', filter=Q(campaign_follows__followed_at__gte=since_date), distinct=True) * 2 +
            Count('activity', filter=Q(activity__timestamp__gte=since_date), distinct=True) * 4
        )
    ).order_by('-trending_score')[:limit]


def get_category_recommendations(user, category, limit=8):
    """
    Get recommendations for a specific category
    """
    base_qs = Campaign.objects.filter(
        is_active=True,
        category=category
    )
    
    if user.is_authenticated:
        # Exclude campaigns user has already interacted with
        base_qs = base_qs.exclude(
            Q(followers=user) | 
            Q(loves__user=user)
        )
    
    return base_qs.annotate(
        popularity=Count('loves', distinct=True) + Count('followers', distinct=True)
    ).order_by('-popularity', '-timestamp')[:limit]


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
