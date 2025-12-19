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
    Profile, Campaign, Comment, Follow, Activity, SupportCampaign,
    User, Love, CampaignView, Chat, Notification, Message,
    AffiliateLink, AffiliateLibrary, AffiliateNewsSource, NativeAd,
    Report, NotInterested, QuranVerse, Surah, Adhkar, Hadith,
    PlatformFund,CampaignProduct, ActivityComment, ActivityLove
)

from main.forms import (
    UserForm, ProfileForm, CampaignForm, CommentForm, ActivityForm,
    SupportForm, ChatForm, MessageForm, CampaignSearchForm, ProfileSearchForm,
     CampaignProductForm, ReportForm, NotInterestedForm,
    SubscriptionForm, UpdateVisibilityForm, ActivityCommentForm,
    UserVerificationForm
)

from main.utils import calculate_similarity

from django.db.models import Count, Q
from itertools import chain
from collections import defaultdict

from main.models import Campaign

def index(request):
    user_profile = None
    unread_notifications = []
    unread_messages_count = 0
    show_login_button = not request.user.is_authenticated  # Show the login button for anonymous users

    # Get selected category filter from request
    category_filter = request.GET.get('category', '')

    if request.user.is_authenticated:
        user_profile = get_object_or_404(Profile, user=request.user)
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()
        unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
        user_chats = Chat.objects.filter(participants=request.user)
        unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()

    # Fetch public campaigns, filter by category if selected
    campaigns = Campaign.objects.filter(visibility='public')

    if category_filter:
        campaigns = campaigns.filter(category=category_filter)

    campaigns = campaigns.select_related('user') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)
        

    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain(love_pairs, comment_pairs, view_pairs,
                      activity_love_pairs, activity_comment_pairs)

    # Count number of unique campaigns each user engaged with
    user_campaign_map = defaultdict(set)

    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

    # Build a list of contributors with their campaign engagement count
    contributor_data = []
    for user_id, campaign_set in user_campaign_map.items():
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

    # Suggested Users (only for authenticated users)
    suggested_users = []
    if request.user.is_authenticated:
        current_user_following = request.user.following.all()  # Get all Follow objects
        following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
        all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
        suggested_users = []
        for profile in all_profiles:
            similarity_score = calculate_similarity(user_profile, profile)
            if similarity_score >= 0.5:
                followers_count = Follow.objects.filter(followed=profile.user).count()
                suggested_users.append({
                    'user': profile.user,
                    'followers_count': followers_count
                })

        # Limit to only 2 suggested users
        suggested_users = suggested_users[:2]

    # Fetch available categories
    categories = Campaign.objects.values_list('category', flat=True).distinct()

    form = SubscriptionForm()
    ads = NativeAd.objects.all()

    context = {
        'campaigns': campaigns,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'form': form,
        'ads': ads,
        'show_login_button': show_login_button,
        'categories': categories,
        'selected_category': category_filter,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'suggested_users': suggested_users,
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
