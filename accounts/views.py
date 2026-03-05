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
    UpdateVisibilityForm, ActivityCommentForm,
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

def index(request):
    """
    Homepage view with proper database connection handling
    FIXED: Added connection health checks and retry logic
    """
    # Ensure we have a fresh connection at the start
    try:
        connection.close_if_unusable_or_obsolete()
        connection.ensure_connection()
    except:
        pass  # Let the view handle connection errors
    
    user_profile = None
    unread_notifications = []
    unread_messages_count = 0
    show_login_button = not request.user.is_authenticated  # Show the login button for anonymous users

    # Get selected category filter from request
    category_filter = request.GET.get('category', '')

    if request.user.is_authenticated:
        try:
            with transaction.atomic():
                user_profile = get_object_or_404(Profile, user=request.user)
                user_profile.last_campaign_check = timezone.now()
                user_profile.save()
                unread_notifications = list(Notification.objects.filter(user=request.user, viewed=False))
              
              
        except OperationalError as e:
            print(f"Database error in authenticated section: {e}")
            # Continue with limited functionality

    # Fetch public campaigns with retry logic
    campaigns = []
    trending_campaigns = []
    
    try:
        # Use a fresh connection for complex queries
        connection.close_if_unusable_or_obsolete()
        
        # Campaigns query with retry
        for attempt in range(3):
            try:
                campaigns_query = Campaign.objects.filter(visibility='public')

                if category_filter:
                    campaigns_query = campaigns_query.filter(category=category_filter)

                campaigns = list(campaigns_query.select_related('user') \
                    .annotate(love_count_annotated=Count('loves')) \
                    .filter(love_count_annotated__gte=1) \
                    .order_by('-love_count_annotated')\
                    .select_related('user').prefetch_related('tags')[:50])  # Limit to prevent memory issues
                break
            except OperationalError as e:
                if attempt < 2:
                    print(f"🔄 Retrying campaigns query (attempt {attempt + 2}/3)...")
                    connection.close()
                    time.sleep(1)
                else:
                    raise

        # Trending campaigns with retry
        for attempt in range(3):
            try:
                trending_query = Campaign.objects.filter(visibility='public') \
                    .annotate(love_count_annotated=Count('loves')) \
                    .filter(love_count_annotated__gte=1)

                if category_filter:
                    trending_query = trending_query.filter(category=category_filter)

                trending_campaigns = list(trending_query.order_by('-love_count_annotated')[:10])
                break
            except OperationalError as e:
                if attempt < 2:
                    print(f"🔄 Retrying trending query (attempt {attempt + 2}/3)...")
                    connection.close()
                    time.sleep(1)
                else:
                    raise

    except OperationalError as e:
        print(f"❌ Database error in campaign queries: {e}")
        # Return a simplified page with error message
        context = {
            'campaigns': [],
            'trending_campaigns': [],
            'user_profile': user_profile,
            'unread_notifications': unread_notifications,
            'unread_messages_count': unread_messages_count,
            'show_login_button': show_login_button,
            'categories': [],
            'selected_category': category_filter,
            'top_contributors': [],
            'suggested_users': [],
            'user_joined_status': {},
            'error_message': "Temporary connection issue. Please refresh the page."
        }
        return render(request, 'accounts/index.html', context)

    # Top Contributors logic - with connection handling
    top_contributors = []
    try:
        # Use list() to force evaluation and catch errors early
        love_pairs = list(Love.objects.values_list('user_id', 'campaign_id'))
        comment_pairs = list(Comment.objects.values_list('user_id', 'campaign_id'))
        view_pairs = list(CampaignView.objects.values_list('user_id', 'campaign_id'))
        activity_love_pairs = list(ActivityLove.objects.values_list('user_id', 'activity__campaign_id'))
        activity_comment_pairs = list(ActivityComment.objects.values_list('user_id', 'activity__campaign_id'))

        # Combine all engagement pairs
        all_pairs = chain(love_pairs, comment_pairs, view_pairs,
                          activity_love_pairs, activity_comment_pairs)

        # Count number of unique campaigns each user engaged with
        user_campaign_map = defaultdict(set)

        for user_id, campaign_id in all_pairs:
            if user_id and campaign_id:  # Skip null values
                user_campaign_map[user_id].add(campaign_id)

        # Build a list of contributors with their campaign engagement count
        contributor_data = []
        for user_id, campaign_set in list(user_campaign_map.items())[:50]:  # Limit processing
            try:
                profile = Profile.objects.get(user__id=user_id)
                contributor_data.append({
                    'user': profile.user,
                    'image': profile.image,
                    'campaign_count': len(campaign_set),
                })
            except Profile.DoesNotExist:
                continue

        # Sort contributors by campaign_count descending
        top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]
    except OperationalError as e:
        print(f"Database error in contributors logic: {e}")
        top_contributors = []  # Fallback to empty list

    # =============================
    campaign_tags_dict = {}

    for camp in campaigns:
        try:
            campaign_tags_dict[str(camp.id)] = list(
                camp.tags.values_list('name', flat=True)
            )
        except:
            campaign_tags_dict[str(camp.id)] = []

    campaign_tags_json = json.dumps(campaign_tags_dict)
    

    context = {
        'campaign_tags_json': campaign_tags_json,
        'campaigns': campaigns,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
     
       
        'show_login_button': show_login_button,
    
        'selected_category': category_filter,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    
    }

    return render(request, 'accounts/index.html', context)



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
