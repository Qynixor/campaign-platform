import paypalrestsdk

import time  # Import the time module

import logging
import json
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse

from django.contrib.auth.models import User
from .forms import (
    UserForm, ProfileForm, CampaignForm, CommentForm, ActivityForm,
    SupportForm, ChatForm, MessageForm, CampaignSearchForm, ProfileSearchForm
)

from .models import (
    Profile, Campaign, Comment, Follow, Activity, SupportCampaign,
    User, Love, CampaignView, Chat, Notification,Message
)
from main.models import UserSubscription

from django.http import JsonResponse
from django.core.exceptions import MultipleObjectsReturned
from django.http import HttpResponseServerError
from django.http import HttpResponse, HttpResponseServerError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.views.generic import CreateView

from django.conf import settings
from decimal import Decimal  # Add this import statement
# Import necessary modules
import os
from dotenv import load_dotenv
from django.urls import reverse
from django.shortcuts import render, redirect

from django.core import exceptions
from django.conf import settings
from .models import Campaign
from django.http import HttpRequest

import paypalrestsdk
from decimal import Decimal
from .models import AffiliateLink
from django.conf import settings

from .utils import calculate_similarity
# views.py
from .forms import ActivityCommentForm
from .models import ActivityComment,ActivityLove

from .models import SupportCampaign, CampaignProduct
from .forms import CampaignProductForm
from django.urls import reverse
from django.utils import timezone

from django.db.models import Case, When, Value, BooleanField

from django.core.files.uploadedfile import SimpleUploadedFile
from mimetypes import guess_type
from .models import  Report
from .forms import ReportForm,NotInterestedForm
from .models import  NotInterested
from django.contrib.admin.views.decorators import staff_member_required
from .models import QuranVerse,Surah
from .models import Adhkar
from .models import Hadith
from .models import PlatformFund
from .forms import SubscriptionForm
from django.views.decorators.http import require_POST
from .forms import UpdateVisibilityForm

from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import mimetypes

from .models import AffiliateLibrary, AffiliateNewsSource
from .models import NativeAd
from django.views.generic.edit import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserVerificationForm

from django.db.models import Count



from django.db.models import Count, Q
from itertools import chain
from collections import defaultdict

from django.db.models import Count, Sum
from django.shortcuts import render
from .models import Campaign, ActivityLove, ActivityComment


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Case, When, Value, BooleanField, Q
from django.utils import timezone
from .models import Campaign, Profile, Notification, Chat, Message, NativeAd, NotInterested, Love
from django.contrib.auth.models import AnonymousUser


from django.http import HttpResponse

def robots_txt(request):
    content = """User-agent: *
Allow: /

Disallow: /admin/
Disallow: /accounts/
Disallow: /tinymce/


Sitemap: https://rallynex.com/sitemap.xml

"""
    return HttpResponse(content, content_type="text/plain")

















@login_required
def campaign_list(request):
    # Get the current user's profile
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Get all campaigns, annotate whether the current user marked them as "not interested"
    campaigns = Campaign.objects.annotate(
        is_not_interested=Case(
            When(not_interested_by__user=user_profile, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )
    
    # Exclude campaigns that the current user has marked as "not interested"
    public_campaigns = campaigns.filter(
        is_not_interested=False, 
        visibility='public'  # Ensure only public campaigns are displayed
    ).order_by('-timestamp')
    
    # Fetch followed users' campaigns
    following_users = request.user.following.values_list('followed', flat=True)
    followed_campaigns = public_campaigns.filter(user__user__in=following_users)
    
    # Include the current user's own public campaigns
    own_campaigns = public_campaigns.filter(user=user_profile)
    
    # Combine followed campaigns and own campaigns for display
    campaigns_to_display = followed_campaigns | own_campaigns
    
    # Fetch new campaigns from followed users added after the user's last check
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check
    ).exclude(id__in=NotInterested.objects.filter(user=user_profile).values_list('campaign_id', flat=True)).order_by('-timestamp')
    
    # Update the user's last campaign check time
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    # Render the campaign list page
    return render(request, 'revenue/campaign_list.html', {
        'public_campaigns': campaigns_to_display,  # Filtered campaigns to display
        'new_campaigns_from_follows': new_campaigns_from_follows,  # New campaigns ordered by latest
    })












def campaign_engagement_data(request, campaign_id):
    campaign = Campaign.objects.get(id=campaign_id)

    # Aggregating engagement metrics

    views = CampaignView.objects.filter(campaign=campaign).count()
    loves = campaign.loves.count()
    comments = Comment.objects.filter(campaign=campaign).count()
    activities = Activity.objects.filter(campaign=campaign).count()
    activity_loves = ActivityLove.objects.filter(activity__campaign=campaign).count()
    active_products = CampaignProduct.objects.filter(campaign=campaign, is_active=True).count()
    activity_comments = ActivityComment.objects.filter(activity__campaign=campaign).count()

    # Prepare data
    engagement_data = {
       
        "views": views,
        "loves": loves,
        "comments": comments,
        "activities": activities,
        "activity_loves": activity_loves,
      
        "active_products": active_products,
        "activity_comments": activity_comments,  # New data point for Activity Comments
    }

    # Optionally, return as JSON for dynamic updates
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(engagement_data)

    user_profile = get_object_or_404(Profile, user=request.user)
    
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Other data to pass to the template (e.g., unread notifications, ads, etc.)
    form = SubscriptionForm()
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()
    ads = NativeAd.objects.all()
    # Pass data to the template
    # Suggested users
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })
    suggested_users = suggested_users[:2]

    # Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
   
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    return render(request, 'revenue/engagement_graph.html', {"campaign": campaign, "engagement_data": engagement_data,'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'form': form,
        'ads': ads,
           
                'user_profile': user_profile,
               'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
      })



def top_participants_view(request, campaign_id):
    # Fetch the campaign and user profile
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Update last campaign check time
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]

    # Aggregate engagement metrics
    loves = ActivityLove.objects.filter(activity__campaign=campaign).values('user').annotate(total=Count('id'))
    comments = ActivityComment.objects.filter(activity__campaign=campaign).values('user').annotate(total=Count('id'))
   
    # Combine all scores for each user
    participant_scores = {}
    for love in loves:
        participant_scores[love['user']] = participant_scores.get(love['user'], 0) + love['total']
    for comment in comments:
        participant_scores[comment['user']] = participant_scores.get(comment['user'], 0) + comment['total']
  
    # Sort participants by score and get top 10
    sorted_participants = sorted(participant_scores.items(), key=lambda x: x[1], reverse=True)
    top_participants = [
        {
            'user': User.objects.get(pk=participant[0]),
            'score': participant[1]
        } for participant in sorted_participants[:10]
    ]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic (site-wide)
    engaged_users = set()
   
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Get suggested users with improved logic
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

    # Other template data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()
    ads = NativeAd.objects.all()
    form = SubscriptionForm()

    context = {
        'campaign': campaign,
        'top_participants': top_participants,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'form': form,
        'ads': ads,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/top_participants.html', context)


def explore_campaigns(request):
        # Fetch all public campaigns
    public_campaigns = Campaign.objects.filter(visibility='public')  # Adjust this query to match your actual filtering criteria
    
    # Pass the public_campaigns to the template
    return render(request, 'marketing/landing.html', {'public_campaigns': public_campaigns})



def changemakers_view(request):
    # Get all profiles and filter those who are changemakers
    changemakers = [profile for profile in Profile.objects.all() if profile.is_changemaker()]

    return render(request, 'revenue/changemakers.html', {'changemakers': changemakers})


@login_required
def verify_profile(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Other data to pass to the template
    form = SubscriptionForm()
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()
    ads = NativeAd.objects.all()

    if request.method == 'POST':
        form = UserVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(user=request.user)
            
            # Clear existing messages before adding the new one
            storage = messages.get_messages(request)
            storage.used = True

            messages.success(request, 'Your verification request has been submitted successfully.')
            return redirect('verify_profile')
    else:
        form = UserVerificationForm()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
    
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Get suggested users with followers count (using the improved logic)
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    context = {
        'form': form,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'ads': ads,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/verify_profile.html', context)

@login_required
def join_leave_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    profile = request.user.profile

    if campaign in profile.campaigns.all():
        # If the user has already joined the campaign, they leave
        profile.campaigns.remove(campaign)
    else:
        # Otherwise, they join the campaign
        profile.campaigns.add(campaign)

    return redirect('view_campaign', campaign_id=campaign.id)  # Redirect to the campaign detail page





@login_required
def campaign_joiners(request, campaign_id):
    # Get user and campaign data
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    joiners = campaign.user_profiles.all()
    
    # Update last campaign check time
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Notifications and messages
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    # Other template data
    form = SubscriptionForm()
    ads = NativeAd.objects.all()

    context = {
        'campaign': campaign,
        'joiners': joiners,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'form': form,
        'ads': ads,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/joiners.html', context)




class CampaignDeleteView(LoginRequiredMixin, DeleteView):
    model = Campaign
    template_name = 'main/campaign_confirm_delete.html'
    success_url = reverse_lazy('home')

    def get_queryset(self):
        user_profile = get_object_or_404(Profile, user=self.request.user)
        return super().get_queryset().filter(user=user_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_filter = self.request.GET.get('category', '')
        user_profile = get_object_or_404(Profile, user=self.request.user)

        # Unread notifications
        unread_notifications = Notification.objects.filter(user=self.request.user, viewed=False)
        context['unread_notifications'] = unread_notifications

        # Unread messages
        user_chats = Chat.objects.filter(participants=self.request.user)
        unread_messages_count = Message.objects.filter(
            chat__in=user_chats
        ).exclude(sender=self.request.user).count()
        context['unread_messages_count'] = unread_messages_count

        # User profile
        context['user_profile'] = user_profile

        # New campaigns from followed users
        following_users = user_profile.following.all()
        new_campaigns_from_follows = Campaign.objects.filter(
            user__user__in=following_users,
            visibility='public',
            timestamp__gt=user_profile.last_campaign_check
        )
        context['new_campaigns_from_follows'] = new_campaigns_from_follows

        # Update campaign check timestamp
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()

        # Improved suggested users logic
        current_user_following = self.request.user.following.all()
        following_user_ids = [follow.followed_id for follow in current_user_following]
    
        # Exclude current user and already followed users
        # FIXED: Changed request.user to self.request.user
        all_profiles = Profile.objects.exclude(user=self.request.user).exclude(user__id__in=following_user_ids)
    
        suggested_users = []
    
        for profile in all_profiles:
            similarity_score = calculate_similarity(user_profile, profile)
            if similarity_score >= 0.5:
                followers_count = Follow.objects.filter(followed=profile.user).count()
                suggested_users.append({
                    'user': profile.user,
                    'followers_count': followers_count
                })

        suggested_users = suggested_users[:2]
        context['suggested_users'] = suggested_users  # Don't forget to add to context!

        # Ads
        ads = NativeAd.objects.all()
        context['ads'] = ads

        # 🔥 Trending campaigns (Only those with at least 1 love)
        trending_campaigns = Campaign.objects.filter(visibility='public') \
            .annotate(love_count_annotated=Count('loves')) \
            .filter(love_count_annotated__gte=1)

        # Apply category filter if provided
        if category_filter:
            trending_campaigns = trending_campaigns.filter(category=category_filter)

        trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]
        context['trending_campaigns'] = trending_campaigns

        # Top Contributors logic
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
        context['top_contributors'] = top_contributors

        # Categories
        categories = Campaign.objects.values_list('category', flat=True).distinct()
        context['categories'] = categories
        context['selected_category'] = category_filter

        return context








def native_ad_list(request):
    ads = NativeAd.objects.all()
    return render(request, 'native_ad_list.html', {'ads': ads})

def native_ad_detail(request, ad_id):
    ad = get_object_or_404(NativeAd, pk=ad_id)
    return render(request, 'native_ad_detail.html', {'ad': ad})





def library_affiliates(request):
    following_users = [follow.followed for follow in request.user.following.all()]  # Get users the current user is following
    user_profile = get_object_or_404(Profile, user=request.user)
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    # Check if there are new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(user__user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check)

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    libraries = AffiliateLibrary.objects.all()
    ads = NativeAd.objects.all() 

    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

          
    return render(request, 'affiliate/library_affiliates.html', {'ads':ads,'libraries': libraries,'user_profile': user_profile,
                                               'unread_notifications': unread_notifications,
    
                                               'new_campaigns_from_follows': new_campaigns_from_follows,  'suggested_users': suggested_users,
         })

def news_affiliates(request):
    following_users = [follow.followed for follow in request.user.following.all()]  # Get users the current user is following
    user_profile = get_object_or_404(Profile, user=request.user)
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    # Check if there are new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(user__user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check)

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    news_sources = AffiliateNewsSource.objects.all()
    ads = NativeAd.objects.all() 

    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

          
    return render(request, 'affiliate/news_affiliates.html', {'ads':ads,'news_sources': news_sources,'user_profile': user_profile,
                                               'unread_notifications': unread_notifications,
    
                                               'new_campaigns_from_follows': new_campaigns_from_follows,  'suggested_users': suggested_users,
         })






@csrf_exempt
def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        file_name = default_storage.save(file.name, ContentFile(file.read()))
        file_url = default_storage.url(file_name)
        file_mime_type, _ = mimetypes.guess_type(file_url)
        return JsonResponse({'location': file_url, 'type': file_mime_type})
    return JsonResponse({'error': 'File upload failed'}, status=400)



class CustomLoginView(LoginView):
    def get_success_url(self):
        return reverse_lazy('rallynex_logo')



@login_required
def rallynex_logo(request):
    return render(request, 'main/rallynex_logo.html')








def subscribe(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have successfully subscribed!')
            return redirect('home')  # Change 'home' to the name of your home view
    else:
        form = SubscriptionForm()
    return render(request, 'revenue/subscribe.html', {'form': form})


    

def jobs(request):
    return render(request, 'revenue/jobs.html')

def events(request):
    return render(request, 'revenue/events.html')

def privacy_policy(request):
    return render(request, 'revenue/privacy_policy.html')

def terms_of_service(request):
    return render(request, 'revenue/terms_of_service.html')

# Add this function:
def project_support(request):
    """Redirect from old project_support to landing page"""
    return redirect('explore_campaigns')  # or return redirect('/landing/')


def platformfund_view(request):
    if request.user.is_authenticated:
        following_users = [follow.followed for follow in request.user.following.all()]  
        user_profile = get_object_or_404(Profile, user=request.user)
        unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
        
        # Check if there are new campaigns from follows
        new_campaigns_from_follows = Campaign.objects.filter(
            user__user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check
        )

        # Update last_campaign_check for the user's profile
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()
    else:
        following_users = []
        user_profile = None
        unread_notifications = []
        new_campaigns_from_follows = []

    platformfunds = PlatformFund.objects.all()
    ads = NativeAd.objects.all()  

    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

          
    return render(request, 'revenue/platformfund.html', {
        'ads': ads,
        'platformfunds': platformfunds,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
          'suggested_users': suggested_users,
        
    })





@login_required
def hadith_list(request):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Hadith data
    hadiths = Hadith.objects.all()
    
    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
   
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'hadiths': hadiths,
        'ads': ads,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/hadith_list.html', context)

@login_required
def hadith_detail(request, hadith_id):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Hadith data
    hadith = get_object_or_404(Hadith, pk=hadith_id)
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'hadith': hadith,
        'ads': ads,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/hadith_detail.html', context)

@login_required
def adhkar_list(request):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Adhkar data
    adhkars = Adhkar.objects.all()
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()

    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'adhkars': adhkars,
        'ads': ads,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/adhkar_list.html', context)




@login_required
def adhkar_detail(request, adhkar_id):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Adhkar data
    adhkar = get_object_or_404(Adhkar, id=adhkar_id)
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'adhkar': adhkar,
        'ads': ads,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/adhkar_detail.html', context)





@login_required
def quran_view(request):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Quran data
    surahs = Surah.objects.all()
    quran_verses = QuranVerse.objects.all()
    
    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
  
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'surahs': surahs,
        'quran_verses': quran_verses,
        'ads': ads,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/quran.html', context)


@login_required
def mark_not_interested(request, campaign_id):
    campaign = Campaign.objects.get(pk=campaign_id)
    user_profile = request.user.profile
    
    # Check if the user has already marked this campaign as not interested
    existing_entry = NotInterested.objects.filter(user=user_profile, campaign=campaign).exists()
    
    if not existing_entry:
        # If not, create a new entry
        not_interested_entry = NotInterested.objects.create(user=user_profile, campaign=campaign)
        not_interested_entry.save()
    
    # Redirect back to the campaign detail page or any other appropriate page
    return redirect('home')

@login_required
def report_campaign(request, campaign_id):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Handle form submission
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.campaign = campaign
            report.reported_by = request.user.profile
            report.save()
            messages.success(request, 'Thank you for reporting. We will review your report shortly.')
            return redirect('view_campaign', campaign_id=campaign.id)
    else:
        form = ReportForm()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'form': form,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/report_campaign.html', context)




def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        # Save the image to the desired location or process it as needed
        # Example: activity.image = image_file; activity.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})






def love_activity(request, activity_id):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            activity = Activity.objects.get(id=activity_id)
            # Check if the user has already loved this activity
            if not ActivityLove.objects.filter(activity=activity, user=request.user).exists():
                # Create a new love for this activity by the user
                ActivityLove.objects.create(activity=activity, user=request.user)
            # Get updated love count for the activity
            love_count = activity.loves.count()
            return JsonResponse({'love_count': love_count})
        except Activity.DoesNotExist:
            return JsonResponse({'error': 'Activity not found'}, status=404)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)







def activity_detail(request, activity_id):
    # Get basic objects
    user_profile = get_object_or_404(Profile, user=request.user)
    activity = get_object_or_404(Activity, id=activity_id)
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Notification and messaging data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    
    # Update last check time
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Suggested users logic
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
    

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'activity': activity,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/activity_detail.html', context)






def add_activity_comment(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    user_profile = get_object_or_404(Profile, user=request.user)
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check if there are new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]


    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
       

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
 
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    if request.method == 'POST':
        form = ActivityCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.activity = activity
            comment.user = request.user
            comment.save()
            return JsonResponse({
                'success': True, 
                'content': comment.content, 
                'username': comment.user.username, 
                'timestamp': comment.timestamp,
                'profile_image_url': comment.user.profile.image.url
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        comments = activity.activitycomment_set.all().order_by('-timestamp')
        form = ActivityCommentForm()
        
        context = {
            'activity': activity, 
            'comments': comments, 
            'form': form,
            'user_profile': user_profile,
            'unread_notifications': unread_notifications,
            'new_campaigns_from_follows': new_campaigns_from_follows,
            'ads': ads,
            'suggested_users': suggested_users,
            'trending_campaigns': trending_campaigns,
            'top_contributors': top_contributors,
            'categories': categories,
            'selected_category': category_filter,
        }
        
        return render(request, 'main/add_activity_comment.html', context)



@login_required
def suggest(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Improved: Get followed user IDs explicitly
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Get all profiles except the current user's and those they're following
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)

    # Suggested users based on similarity score
    suggested_users = []
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count,
                'similarity_score': similarity_score  # Optional: include for debugging
            })
    
    # Sort by similarity score (highest first) and take top 20 for the suggestions page
    suggested_users = sorted(suggested_users, key=lambda x: x['similarity_score'], reverse=True)[:20]

    # Unread notifications
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    # New campaigns from followed users (using the same following_user_ids)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last check timestamp
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Trending campaigns
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic (unchanged)
    engaged_users = set()
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
                      activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]

    # Ads
    ads = NativeAd.objects.all()

    return render(request, 'main/suggest.html', {
        'ads': ads,
        'suggested_users': suggested_users,  # Fixed typo from 'suggested_users'
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    })



@login_required
def affiliate_links(request):
    following_users = [follow.followed for follow in request.user.following.all()]  # Get users the current user is following
    user_profile = get_object_or_404(Profile, user=request.user)
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check if there are new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(user__user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check)

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Get all affiliate links sorted by the newest first
    affiliate_links = AffiliateLink.objects.all().order_by('-created_at')

    # Fetch ads if necessary
    ads = NativeAd.objects.all()  
    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

    # Return the rendered response
    return render(request, 'revenue/affiliate_links.html', {
        'ads': ads,
        'affiliate_links': affiliate_links,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
          'suggested_users': suggested_users,
      
    })




@login_required
def update_visibility(request, campaign_id):
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]

    user_profile = get_object_or_404(Profile, user=request.user)
    
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except ObjectDoesNotExist:
        return HttpResponseServerError("Campaign not found")

    # Get all support campaigns
    support_campaigns = SupportCampaign.objects.filter(campaign_id=campaign_id)

    if request.method == 'POST':
        # Update visibility settings: only donation, pledge, and products
        for support_campaign in support_campaigns:
            support_campaign.donate_monetary_visible = request.POST.get('donate_monetary_visible', False) == 'on'
            support_campaign.campaign_product_visible = request.POST.get('campaign_product_visible', False) == 'on'
            support_campaign.pledge_visible = request.POST.get('pledge_visible', False) == 'on'
            support_campaign.save()
        return redirect('support', campaign_id=campaign_id)

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()

    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain(love_pairs, comment_pairs, view_pairs, activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]

    # Suggested users
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

    suggested_users = suggested_users[:2]

    # New campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'support_campaigns': support_campaigns,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }

    return render(request, 'main/update_visibility.html', context)



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Campaign, Profile, SupportCampaign, CampaignProduct, NativeAd, Notification






@login_required
def support(request, campaign_id):
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    campaign = get_object_or_404(Campaign, id=campaign_id)
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Retrieve or create the SupportCampaign object
    support_campaign, created = SupportCampaign.objects.get_or_create(
        user=request.user, 
        campaign=campaign
    )
    
    # Get products related to the campaign
    products = CampaignProduct.objects.filter(campaign=campaign) if campaign else None
    
    # Notification and follows data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    
    # Update last check time
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]


    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
     

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic

    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'campaign': campaign,
        'support_campaign': support_campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'products': products,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,

    }
    
    return render(request, 'main/support.html', context)





@login_required
def update_hidden_links(request):
    if request.method == 'POST':
        link_name = request.POST.get('link_name')
        campaign_id = request.POST.get('campaign_id')
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            # Check if the user is the owner of the campaign
            if request.user == campaign.user.user:
                # Update the visibility status of the link based on link_name
                if link_name == 'donate_monetary':
                    campaign.donate_monetary_visible = False
                elif link_name == 'campaign_product':
                    campaign.campaign_product_visible = False
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid link name'})
                campaign.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'User is not the owner of the campaign'})
        except Campaign.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Campaign not found'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'})









@login_required
def donate_monetary(request, campaign_id):
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check if there are new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
    

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
  
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/donate_monetary.html', context)






def support_campaign_create(request):
    if request.method == 'POST':
        form = SupportCampaignForm(request.POST)
        if form.is_valid():
            support_campaign = form.save(commit=False)
            support_campaign.user = request.user
            support_campaign.save()
            return redirect('success_url')  # Redirect to a success URL
    else:
        form = SupportCampaignForm()
    campaign_products = CampaignProduct.objects.all()  # Retrieve all campaign products
    return render(request, 'support_campaign_create.html', {'form': form, 'campaign_products': campaign_products})






def fill_paypal_account(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('campaigns_list')  # Redirect to campaigns list or any other appropriate page
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'main/fill_paypal_account.html', {'form': form})




@login_required
def search_campaign(request):
    # Get user data with improved following logic
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    user_profile = get_object_or_404(Profile, user=request.user)
    query = request.GET.get('search_query')
    
    # Initialize empty querysets for all searchable models
    campaigns = Campaign.objects.none()
    profiles = Profile.objects.none()
    quran_verses = QuranVerse.objects.none()
    adhkar = Adhkar.objects.none()
    hadiths = Hadith.objects.none()
    
    if query:
        # Search across different models - CLEAN APPROACH
        campaigns = Campaign.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(category__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()  # This SHOULD prevent duplicates
            # Temporary debug - remove after testing
      
        # Alternative: More explicit approach if you're still worried
        # campaigns = Campaign.objects.distinct().filter(
        #     Q(title__icontains=query) | 
        #     Q(content__icontains=query) |
        #     Q(category__icontains=query) |
        #     Q(tags__name__icontains=query)
        # )
        
        profiles = Profile.objects.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(bio__icontains=query)
        ).distinct()
        
        quran_verses = QuranVerse.objects.filter(
            Q(verse_text__icontains=query) |
            Q(translation__icontains=query) |
            Q(description__icontains=query) |
            Q(surah__name__icontains=query)
        ).distinct()
        
        adhkar = Adhkar.objects.filter(
            Q(type__icontains=query) |
            Q(text__icontains=query) |
            Q(translation__icontains=query) |
            Q(reference__icontains=query)
        ).distinct()
        
        hadiths = Hadith.objects.filter(
            Q(narrator__icontains=query) |
            Q(text__icontains=query) |
            Q(reference__icontains=query) |
            Q(authenticity__icontains=query)
        ).distinct()
    
    
    # Notifications handling
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    unread_notifications = notifications.filter(viewed=False)
    unread_notifications.update(viewed=True)
    unread_count = unread_notifications.count()
    
    # New campaigns from follows using consistent following_user_ids
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()

    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'campaigns': campaigns,
        'profiles': profiles,
        'quran_verses': quran_verses,
        'adhkar': adhkar,
        'hadiths': hadiths,
        'user_profile': user_profile,
        'unread_count': unread_count,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'search_query': query,  # Pass the search query back to template
    }
    
    return render(request, 'main/search_results.html', context)






from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from itertools import chain
from collections import defaultdict
from .models import (
    Profile, Notification, Campaign, Love, Comment, 
    CampaignView, ActivityLove, ActivityComment, Follow,
    NativeAd
)
from .utils import calculate_similarity  # Make sure this import matches your project structure

@login_required
def notification_list(request):
    # Handle delete requests
    if request.method == 'POST' and 'delete_notification' in request.POST:
        notification_id = request.POST.get('notification_id')
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_active = False  # Soft delete
            notification.save()
            messages.success(request, 'Notification deleted successfully.')
        except Notification.DoesNotExist:
            messages.error(request, 'Notification not found.')
        return redirect('notification_list')
    
    if request.method == 'POST' and 'clear_all' in request.POST:
        # Soft delete all notifications for this user
        Notification.objects.filter(user=request.user, is_active=True).update(is_active=False)
        messages.success(request, 'All notifications cleared.')
        return redirect('notification_list')
    
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Retrieve only active notifications for the logged-in user
    notifications = Notification.objects.filter(user=request.user, is_active=True).order_by('-timestamp')

    # Mark notifications as viewed
    unread_notifications = notifications.filter(viewed=False)
    unread_notifications.update(viewed=True)

    # Count unread notifications
    unread_count = unread_notifications.count()
    
    # Check if there are new campaigns from follows (using consistent following_user_ids)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
      

    # Apply category filter if provided
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

    # Get suggested users with improved logic
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

    ads = NativeAd.objects.all()
    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'notifications': notifications,
        'user_profile': user_profile,
        'unread_count': unread_count,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    return render(request, 'main/notification_list.html', context)






@login_required
def create_chat(request):
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    user_profile = get_object_or_404(Profile, user=request.user)
    
    if request.method == 'POST':
        form = ChatForm(request.user, request.POST)
        if form.is_valid():
            chat = form.save(commit=False)
            chat.manager = request.user
            chat.save()
            form.save_m2m()
            return redirect('chat_detail', chat_id=chat.id)
    else:
        form = ChatForm(request.user)
    
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
      

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic

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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'form': form,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/create_chat.html', context)


# views.py - Fixed send_message view
import re
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count
from itertools import chain
from collections import defaultdict
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from .models import Chat, Message, Profile, Notification, Campaign, NativeAd, Follow, Love, Comment, CampaignView, ActivityLove, ActivityComment
from .forms import MessageForm
from .utils import calculate_similarity

@method_decorator(login_required, name='dispatch')
class ChatDetailView(View):
    def get(self, request, chat_id):
        chat = get_object_or_404(
            Chat.objects.select_related("manager").prefetch_related("participants"),
            id=chat_id
        )
        
        # Check if user is a participant or manager
        if request.user not in chat.participants.all() and request.user != chat.manager:
            return redirect('home')
        
        category_filter = request.GET.get('category', '')
        user_profile = get_object_or_404(Profile, user=request.user)
        following_users = request.user.following.values_list('followed', flat=True)
        followers = request.user.followers.values_list('follower', flat=True)

        combined_users = set(following_users) | set(followers)

        user_choices = User.objects.filter(pk__in=combined_users).exclude(
            pk=request.user.pk
        ).exclude(pk__in=chat.participants.values_list("pk", flat=True))

        messages = Message.objects.filter(chat=chat).select_related("sender__profile").order_by('timestamp')[:50]

        # Initialize message_form
        message_form = MessageForm(initial={'chat': chat})
        
        # Handle AJAX polling for new messages
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            last_message_id = request.GET.get('last_message', 0)
            try:
                last_message_id = int(last_message_id)
            except (ValueError, TypeError):
                last_message_id = 0
                
            new_messages = Message.objects.filter(
                chat=chat, 
                id__gt=last_message_id
            ).select_related("sender__profile").order_by('timestamp')
            
            messages_data = []
            for msg in new_messages:
                messages_data.append({
                    'id': msg.id,
                    'content': msg.content,
                    'sender': msg.sender.username,
                    'sender_image': msg.sender.profile.image.url,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_own': msg.sender == request.user,
                    'file_url': msg.file.url if msg.file else None,
                    'file_name': msg.file_name if msg.file else None,
                    'file_type': msg.file_type if msg.file else None
                })
            
            return JsonResponse({'messages': messages_data})
        
        # Regular page load - prepare context
        unread_notifications = Notification.objects.filter(user=request.user, viewed=False)[:10]
        new_campaigns_from_follows = Campaign.objects.filter(
            user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check
        )

        user_profile.last_campaign_check = timezone.now()
        user_profile.save()

        ads = NativeAd.objects.all()
        
        # Suggested users logic
        current_user_following = request.user.following.all()
        following_user_ids = [follow.followed_id for follow in current_user_following]
        
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

        suggested_users = suggested_users[:2]

        trending_campaigns = Campaign.objects.filter(visibility='public') \
            .annotate(love_count_annotated=Count('loves')) \
            .filter(love_count_annotated__gte=1)
           
        if category_filter:
            trending_campaigns = trending_campaigns.filter(category=category_filter)

        trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

        # Top Contributors logic
        contributor_data = []
        try:
            love_pairs = Love.objects.values_list('user_id', 'campaign_id')
            comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
            view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
            activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
            activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

            all_pairs = chain(love_pairs, comment_pairs, view_pairs, activity_love_pairs, activity_comment_pairs)

            user_campaign_map = defaultdict(set)
            for user_id, campaign_id in all_pairs:
                user_campaign_map[user_id].add(campaign_id)

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

            top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]
        except Exception as e:
            top_contributors = []

        categories = Campaign.objects.values_list('category', flat=True).distinct()

        context = {
            'ads': ads,
            'unread_notifications': unread_notifications,
            'new_campaigns_from_follows': new_campaigns_from_follows,
            'user_profile': user_profile,
            'chat': chat,
            'message_form': message_form,
            'messages': messages,
            'user_choices': user_choices,
            'suggested_users': suggested_users,
            'trending_campaigns': trending_campaigns,
            'top_contributors': top_contributors,
            'categories': categories,
            'selected_category': category_filter,
            'user': request.user,
        }

        return render(request, 'main/chat_detail.html', context)

@csrf_exempt
@login_required
def send_message(request, chat_id):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        file = request.FILES.get('file')
        
        # Allow either content or file (or both)
        if not content and not file:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        chat = get_object_or_404(Chat, id=chat_id)
        
        # Check if user is a participant or manager
        if request.user not in chat.participants.all() and request.user != chat.manager:
            return JsonResponse({'success': False, 'error': 'You are not authorized to send messages in this chat'})
        
        try:
            # Auto-detect and convert URLs to clickable links if there's content
            if content:
                url_pattern = re.compile(r'https?://\S+')
                content = url_pattern.sub(
                    lambda m: f'<a href="{m.group(0)}" target="_blank" style="color: #075e54; text-decoration: underline;">{m.group(0)}</a>', 
                    content
                )
            
            # Create the message
            message = Message.objects.create(
                chat=chat,
                sender=request.user,
                content=content,
                file=file,
                file_name=file.name if file else '',
                file_type=file.content_type if file else ''
            )
            
            # Return the message data
            return JsonResponse({
                'success': True,
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'sender_image': message.sender.profile.image.url,
                    'timestamp': message.timestamp.isoformat(),
                    'is_own': True,
                    'file_url': message.file.url if message.file else None,
                    'file_name': message.file_name,
                    'file_type': message.file_type
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
def user_chats(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    last_chat_check = user_profile.last_chat_check

    # Update user's last chat check timestamp
    user_profile.last_chat_check = timezone.now()
    user_profile.save()

    # Get user chats and check for unread messages
    user_chats = Chat.objects.filter(participants=request.user) | Chat.objects.filter(manager=request.user)
    for chat in user_chats:
        chat.has_unread_messages = chat.messages.filter(timestamp__gt=last_chat_check).exists()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Get suggested users with improved logic
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    # Exclude current user and already followed users
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

    # Other data
    following_users = [follow.followed for follow in request.user.following.all()]
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'user_chats': user_chats,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/user_chats.html', context)


@require_POST
@login_required
def add_participants(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user == chat.manager:
        user_ids = request.POST.getlist('participants')
        users_to_add = User.objects.filter(id__in=user_ids)
        chat.participants.add(*users_to_add)
        return JsonResponse({'redirect': f'/chat/{chat_id}/'})
    return JsonResponse({'error': 'Unauthorized'}, status=403)

@require_POST
@login_required
def remove_participants(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user == chat.manager:
        user_ids = request.POST.getlist('participants')
        users_to_remove = chat.participants.filter(id__in=user_ids)
        chat.participants.remove(*users_to_remove)
        return JsonResponse({'redirect': f'/chat/{chat_id}/'})
    return JsonResponse({'error': 'Unauthorized'}, status=403)

@require_POST
@login_required
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user == chat.manager:
        chat.delete()
        return JsonResponse({'redirect': '/user/chats/'})
    return JsonResponse({'error': 'Unauthorized'}, status=403)




def view_campaign(request, campaign_id):
    category_filter = request.GET.get('category', '')  # Get category filter from request
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    user_profile = None
    already_loved = False
    following_users = []  # default empty

    if request.user.is_authenticated:
        # Following users
        following_users = [follow.followed for follow in request.user.following.all()]
        
        # Profile and loves
        user_profile = request.user.profile
        already_loved = Love.objects.filter(user=request.user, campaign=campaign).exists()

        # Track campaign view
        if not CampaignView.objects.filter(user=user_profile, campaign=campaign).exists():
            CampaignView.objects.create(user=user_profile, campaign=campaign)

        # Unread notifications
        unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

        # New campaigns from follows
        new_campaigns_from_follows = Campaign.objects.filter(
            user__user__in=following_users, 
            visibility='public', 
            timestamp__gt=user_profile.last_campaign_check
        )

        # Update last check
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()
    else:
        unread_notifications = Notification.objects.none()
        new_campaigns_from_follows = Campaign.objects.none()

    ads = NativeAd.objects.all()
    
    # Suggested users logic (only for authenticated users)
    suggested_users = []
    if request.user.is_authenticated:
        current_user_following = request.user.following.all()
        following_user_ids = [follow.followed_id for follow in current_user_following]

        all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
        
        for profile in all_profiles:
            similarity_score = calculate_similarity(user_profile, profile)
            if similarity_score >= 0.5:
                followers_count = Follow.objects.filter(followed=profile.user).count()
                suggested_users.append({
                    'user': profile.user,
                    'followers_count': followers_count
                })
        suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)

    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain(love_pairs, comment_pairs, view_pairs, activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'campaign': campaign,
        'ads': ads,
        'user_profile': user_profile,
        'already_loved': already_loved,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }

    return render(request, 'main/campaign_detail.html', context)




def campaign_detail(request, pk):
    # Retrieve the campaign object using its primary key (pk)
    campaign = get_object_or_404(Campaign, pk=pk)
    form = SubscriptionForm()
    # Pass the campaign object to the template for rendering
    return render(request, 'main/campaign_detail.html', {'campaign': campaign,'form':form})



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import json
from .models import Campaign, SoundTribe, Profile

# ==================== SOUND TRIBE VIEWS ====================

@require_POST
@csrf_exempt
def join_sound_tribe(request, campaign_id):
    """
    Handle user joining the sound tribe for a campaign
    """
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False, 
                'error': 'Please log in to join the sound tribe'
            })
        
        campaign = Campaign.objects.get(id=campaign_id)
        profile = request.user.profile
        
        # Create or get tribe entry
        tribe_entry, created = SoundTribe.objects.get_or_create(
            user=profile,
            campaign=campaign
        )
        
        # Get updated tribe data
        member_count = campaign.get_sound_tribe_members_count()
        
        # Get recent members with profile data
        recent_members = SoundTribe.objects.filter(
            campaign=campaign
        ).select_related('user__user', 'user').order_by('-timestamp')[:6]
        
        recent_members_data = [
            {
                'username': member.user.user.username,
                'profile_pic': member.user.image.url if member.user.image else '',
                'profile_url': reverse('profile_view', kwargs={'username': member.user.user.username}),
                'timestamp': member.timestamp.strftime('%H:%M')
            }
            for member in recent_members
        ]
        
        return JsonResponse({
            'success': True,
            'member_count': member_count,
            'recent_members': recent_members_data,
            'is_new': created,
            'message': 'Welcome to the Soundmark Tribe! 🎵'
        })
        
    except Campaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaign not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def get_sound_tribe_data(request, campaign_id):
    """
    Get current sound tribe data for popup display
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        has_joined = False
        
        # Check if current user has joined the tribe
        if request.user.is_authenticated:
            has_joined = campaign.has_user_joined_tribe(request.user.profile)
        
        member_count = campaign.get_sound_tribe_members_count()
        
        # Get recent members with profile data
        recent_members = SoundTribe.objects.filter(
            campaign=campaign
        ).select_related('user__user', 'user').order_by('-timestamp')[:6]
        
        recent_members_data = [
            {
                'username': member.user.user.username,
                'profile_pic': member.user.image.url if member.user.image else '',
                'profile_url': reverse('profile_view', kwargs={'username': member.user.user.username}),
                'timestamp': member.timestamp.strftime('%H:%M')
            }
            for member in recent_members
        ]
        
        return JsonResponse({
            'success': True,
            'member_count': member_count,
            'has_joined': has_joined,
            'recent_members': recent_members_data
        })
        
    except Campaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaign not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



def thank_you(request):
    
    return render(request, 'main/thank_you.html')






def activity_list(request, campaign_id):
    # Get data from request
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Get all activities associated with the campaign
    activities = Activity.objects.filter(campaign=campaign).order_by('-timestamp')
    
    # Add comment count for each activity
    for activity in activities:
        activity.comment_count = ActivityComment.objects.filter(activity=activity).count()
    
    # List of image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    activity_count = activities.count()
    
    # Notification and messaging data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]


    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
     

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
 
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'campaign': campaign, 
        'activities': activities, 
        'image_extensions': image_extensions,
        'user_profile': user_profile,
        'activity_count': activity_count,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/activity_list.html', context)





# views.py
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
from .models import ActivityComment, ActivityCommentLike
from django.db.models import Count


@require_GET
@login_required
def get_activity_comments(request, activity_id):
    try:
        activity = Activity.objects.get(id=activity_id)
        all_comments = request.GET.get('all', 'false').lower() == 'true'
        
        # Get base queryset
        comments = ActivityComment.objects.filter(activity=activity, parent_comment__isnull=True)
        
        # Count total comments
        total_comments = comments.count()
        
        # Apply ordering (remove pagination)
        comments = comments.order_by('-timestamp')
        
        # If not requesting all comments, still limit to 5 for initial load
        if not all_comments and total_comments > 5:
            comments = comments[:5]
        
        # Prepare comment data
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'username': comment.user.username,
                'user_image': comment.user.profile.image.url if comment.user.profile.image else '',
                'content': comment.content,
                'timestamp': timezone.localtime(comment.timestamp).strftime('%b %d, %Y at %I:%M %p'),
                'like_count': ActivityCommentLike.objects.filter(comment=comment).count(),
                'liked': ActivityCommentLike.objects.filter(comment=comment, user=request.user).exists(),
                'reply_count': comment.replies.count()
            })
        
        return JsonResponse({
            'success': True,
            'comments': comments_data,
            'total_comments': total_comments
        })
    except Activity.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Activity not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)







from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

@require_POST
def post_activity_comment(request):
    try:
        data = json.loads(request.body)
        activity_id = data.get('activity_id')
        content = data.get('content')
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Comment cannot be empty'})
            
        activity = Activity.objects.get(id=activity_id)
        comment = ActivityComment.objects.create(
            activity=activity,
            user=request.user,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'comment_id': comment.id
        })
        
    except Activity.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Activity not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})







@require_POST
@login_required
def like_activity_comment(request):
    try:
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        action = data.get('action')
        
        if not comment_id or not action:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        comment = ActivityComment.objects.get(id=comment_id)
        
        if action == 'like':
            # Check if already liked
            if not ActivityCommentLike.objects.filter(comment=comment, user=request.user).exists():
                ActivityCommentLike.objects.create(comment=comment, user=request.user)
        elif action == 'unlike':
            ActivityCommentLike.objects.filter(comment=comment, user=request.user).delete()
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        
        # Get updated like count
        like_count = ActivityCommentLike.objects.filter(comment=comment).count()
        
        return JsonResponse({
            'success': True,
            'like_count': like_count
        })
    except ActivityComment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Comment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
import json
from .models import ActivityComment
from django.shortcuts import get_object_or_404

@require_POST
@login_required
@csrf_exempt
def post_comment_reply(request):
    try:
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        content = data.get('content')
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Content is required'}, status=400)
        
        parent_comment = get_object_or_404(ActivityComment, id=comment_id)
        reply = ActivityComment.objects.create(
            activity=parent_comment.activity,
            user=request.user,
            content=content,
            parent_comment=parent_comment
        )
        
        return JsonResponse({
            'success': True,
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'username': reply.user.username,
                'user_image': reply.user.profile.image.url if hasattr(reply.user, 'profile') and reply.user.profile.image else '',
                'timestamp': reply.timestamp.strftime('%b %d, %Y %I:%M %p'),
                'like_count': reply.like_count,
                'liked': False  # New replies aren't liked by default
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_GET
@login_required
def get_comment_replies(request, comment_id):
    try:
        parent_comment = get_object_or_404(ActivityComment, id=comment_id)
        replies = parent_comment.replies.all().order_by('timestamp')
        
        replies_data = []
        for reply in replies:
            replies_data.append({
                'id': reply.id,
                'content': reply.content,
                'username': reply.user.username,
                'user_image': reply.user.profile.image.url if hasattr(reply.user, 'profile') and reply.user.profile.image else '',
                'timestamp': reply.timestamp.strftime('%b %d, %Y %I:%M %p'),
                'like_count': reply.like_count,
                'liked': request.user in reply.likes.all()
            })
        
        return JsonResponse({
            'success': True,
            'replies': replies_data,
            'total_replies': parent_comment.reply_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)




@require_POST
@login_required
@csrf_exempt
def like_comment_reply(request):
    try:
        data = json.loads(request.body)
        reply_id = data.get('reply_id')
        action = data.get('action')  # 'like' or 'unlike'
        
        if action not in ['like', 'unlike']:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        
        reply = get_object_or_404(ActivityComment, id=reply_id)
        
        if action == 'like':
            # Using the ActivityCommentLike model
            if not ActivityCommentLike.objects.filter(comment=reply, user=request.user).exists():
                ActivityCommentLike.objects.create(comment=reply, user=request.user)
        else:
            ActivityCommentLike.objects.filter(comment=reply, user=request.user).delete()
        
        return JsonResponse({
            'success': True,
            'like_count': ActivityCommentLike.objects.filter(comment=reply).count(),
            'action': action
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)






from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.forms import inlineformset_factory
from django.db import transaction
from django import forms
from django.urls import reverse
from cloudinary.models import CloudinaryResource

# Models
from .models import (
    Campaign, Activity, Profile, Notification, 
    NativeAd, Follow, Love, Comment, 
    CampaignView, ActivityLove, ActivityComment,
    UserSubscription
)

# Utilities
from .utils import calculate_similarity, validate_no_long_words

# ActivityForm Definition
class ActivityForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        label="Add Media (optional)",
        help_text="Upload image, video or audio file (max 10MB)",
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*,video/*,audio/*',
            'class': 'file-input',
            'multiple': False
        })
    )
    
    class Meta:
        model = Activity
        fields = ['content', 'file']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share an update, ask for help, celebrate progress...',
                'class': 'activity-content'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make both fields completely optional
        self.fields['content'].required = False
        self.fields['file'].required = False
            
    def clean(self):
        cleaned_data = super().clean()
        # Both fields are optional - user can leave entire form empty
        # Empty forms will be skipped in the view
        return cleaned_data

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            validate_no_long_words(content)
        return content

    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        # Skip validation if it's an existing CloudinaryResource
        if file and isinstance(file, CloudinaryResource):
            return file
            
        # Only validate for new file uploads
        if file and hasattr(file, 'size'):
            # Validate file size (10MB max)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise forms.ValidationError(f'File size must be under {max_size/1024/1024}MB')
            
            # Validate file types
            allowed_types = ['image', 'video', 'audio']
            if not any(file.content_type.startswith(t) for t in allowed_types):
                raise forms.ValidationError('Only image, video, and audio files are allowed')
        
        return file




@login_required
def create_activity(request, campaign_id):
    """
    PROGRESSIVE ACTIVITY CREATION VIEW
    --------------------------------
    First visit: Show 1 empty form
    Second visit: Show previous activity (editable) + 1 empty form
    Third visit: Show 2 previous activities + 1 empty form
    ...up to max 10 forms total
    Empty forms are allowed - user doesn't have to fill every form
    """
    
    # 🔒 CHECK USER CAMPAIGN LIMIT
    subscription = UserSubscription.get_for_user(request.user)
    user_campaign_count = Campaign.objects.filter(user=request.user.profile).count()
    
    # Check if user has active subscription
    if not subscription.has_active_subscription():
        # If user has reached their free campaign limit, restrict activity creation
        if user_campaign_count >= subscription.campaign_limit:
            messages.warning(
                request,
                "You've reached your free campaign limit. Upgrade to Rallynex Pro to create activities."
            )
            return redirect('subscription_required')
    
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # 🔒 ADDITIONAL CHECK: Ensure user owns the campaign
    if campaign.user != user_profile:
        messages.error(request, "You can only create activities for your own campaigns.")
        # Redirect to activity_list instead of view_campaign
        return redirect('activity_list', campaign_id=campaign_id)

    # Get existing activities for this campaign, ordered newest first
    existing_activities = Activity.objects.filter(campaign=campaign).order_by('-timestamp')
    
    # Calculate how many forms to show
    # Show existing activities + 1 empty form, but max 10 total
    MAX_FORMS = 10
    existing_count = existing_activities.count()
    
    if existing_count >= MAX_FORMS:
        # Already at max, show all existing (no empty form)
        forms_to_show = MAX_FORMS
        empty_forms = 0
    else:
        # Show existing + 1 empty form
        forms_to_show = existing_count + 1
        empty_forms = 1
    
    # Create the formset with dynamic number of forms
    ActivityFormSet = inlineformset_factory(
        Campaign,
        Activity,
        form=ActivityForm,
        extra=empty_forms,  # Add empty forms
        can_delete=True,
        max_num=MAX_FORMS,
        fields=['content', 'file']
    )

    if request.method == 'POST':
        formset = ActivityFormSet(
            request.POST, 
            request.FILES, 
            instance=campaign,
            queryset=existing_activities  # Pre-populate with existing activities
        )
        
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    
                    saved_count = 0
                    new_count = 0
                    updated_count = 0
                    
                    for instance in instances:
                        # Skip COMPLETELY empty forms (no content AND no file)
                        # Also skip if it's an existing activity with no changes
                        if not instance.content and not instance.file:
                            # Check if this is an existing activity with no changes
                            if instance.pk:
                                # Get the original instance
                                original = Activity.objects.get(pk=instance.pk)
                                # If no changes at all, skip
                                if (instance.content == original.content and 
                                    instance.file == original.file):
                                    continue
                            else:
                                # New form with no content or file, skip
                                continue
                            
                        # If there's a file but no content, add default content
                        if instance.file and not instance.content:
                            instance.content = "Shared a file"
                            
                        instance.save()
                        saved_count += 1
                        
                        if not instance.pk:  # New activity
                            new_count += 1
                        else:  # Updated activity
                            updated_count += 1
                    
                    # Handle deleted forms
                    deleted_count = 0
                    for form in formset.deleted_forms:
                        if form.instance.pk:
                            form.instance.delete()
                            deleted_count += 1
                    
                    # Create success message based on actions
                    if saved_count > 0 or deleted_count > 0:
                        action_messages = []
                        if new_count > 0:
                            action_messages.append(f"Created {new_count} new activity{'s' if new_count > 1 else ''}")
                        if updated_count > 0:
                            action_messages.append(f"Updated {updated_count} existing activity{'s' if updated_count > 1 else ''}")
                        if deleted_count > 0:
                            action_messages.append(f"Deleted {deleted_count} activity{'s' if deleted_count > 1 else ''}")
                        
                        if action_messages:
                            messages.success(request, ' • '.join(action_messages))
                        else:
                            messages.success(request, 'Changes saved successfully!')
                    else:
                        # Check if user submitted completely empty forms
                        messages.info(request, 'No changes were made.')
                    
                    # CHANGED: Redirect to activity_list instead of view_campaign
                    return redirect('activity_list', campaign_id=campaign_id)
                    
            except Exception as e:
                messages.error(request, f'Error saving activities: {str(e)}')
                print(f"Error in create_activity: {e}")
        else:
            # Show form errors
            error_count = 0
            error_messages = []
            for i, form in enumerate(formset):
                if form.errors:
                    error_count += len(form.errors)
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_messages.append(f"Form {i+1} - {field}: {error}")
            
            if error_count > 0:
                messages.error(request, f'Please correct the {error_count} error{"s" if error_count > 1 else ""} below.')
                # Print errors to console for debugging
                print("Form errors:", error_messages)
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        # GET request - show forms with existing activities + empty form(s)
        formset = ActivityFormSet(
            instance=campaign,
            queryset=existing_activities
        )

    # Get context data for notifications, etc.
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    ads = NativeAd.objects.all()

    # Suggested users logic
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
    
    suggested_users = []
    for profile in all_profiles[:2]:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Trending campaigns
    from django.db.models import Count
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)
      
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    from itertools import chain
    from collections import defaultdict
    
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain(love_pairs, comment_pairs, view_pairs,
                      activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    # Emojis for the emoji picker
    emojis = [
        '📢', '🎉', '💼', '📊', '💡', '🔍', '📣', '🎯', '🔔', '📱', '💸', '⭐', '💥', '🌟', 
        '🌳', '🌍', '🌱', '🌲', '🌿', '🍃', '🏞️', '🦋', '🐝', '🐞', '🦜', '🐢', '🐘', '🐆', '🐅', '🐬',
        '💉', '❤️', '🩺', '🚑', '🏥', '🧬', '💊', '🩹', '🧑‍⚕️', '👨‍⚕️', '🩸', '🫁', '🫀', '🧠', '🦷', '👁️',
        '📚', '🎓', '🏫', '🖊️', '📖', '✍️', '🧑‍🏫', '👨‍🏫', '📜', '🔖', '📕', '📝', '📋', '📑', '🧮', '🎒',
        '🤝', '🗣️', '💬', '🏘️', '🏠', '👩‍🏫', '👨‍🏫', '🧑‍🎓', '👩‍🎓', '👨‍🎓', '🏘️', '🏡', '🏙️', '🚪', '🛠️', '🛏️',
        '⚖️', '🕊️', '🏳️‍🌈', '🔒', '🛡️', '📜', '📛', '🤲', '✌️', '👐', '🙏', '🧑‍⚖️', '👨‍⚖️', '📝', '🪧', '🎗️',
        '🐾', '🐕', '🐈', '🐅', '🐆', '🐘', '🐄', '🐑', '🐇', '🐿️', '🐦', '🦢', '🦉', '🐠', '🦑', '🦓', '🐅',
    ]

    initial_emojis = emojis[:10]
    additional_emojis = emojis[10:]

    context = {
        'ads': ads,
        'formset': formset,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'initial_emojis': initial_emojis,
        'additional_emojis': additional_emojis,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
        'is_pro': subscription.has_active_subscription(),
        'campaign_count': user_campaign_count,
        'campaign_limit': subscription.campaign_limit,
        'existing_activities_count': existing_count,
        'max_forms': MAX_FORMS,
        'is_at_max': existing_count >= MAX_FORMS,
    }

    return render(request, 'main/activity_create.html', context)









@login_required
def manage_campaigns(request):
    # Get the user's profile
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Get selected category filter from request
    category_filter = request.GET.get('category', '')

    # Fetch all campaigns (both public and private) for the current user's profile
    all_campaigns = Campaign.objects.filter(user=user_profile)
    
    # Apply category filter if provided
    if category_filter:
        all_campaigns = all_campaigns.filter(category=category_filter)

    all_campaigns = all_campaigns.order_by('-timestamp')

    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check if there are new campaigns from follows
    following_users = [follow.followed for follow in request.user.following.all()]
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, visibility='public', timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    ads = NativeAd.objects.all()
    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]


    # Fetch available categories
    categories = Campaign.objects.filter(user=user_profile).values_list('category', flat=True).distinct()

    return render(request, 'main/manage_campaigns.html', {
        'ads': ads,
        'campaigns': all_campaigns,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'categories': categories,  # Pass categories to template
        'selected_category': category_filter,  # Retain selected category
          'suggested_users': suggested_users,
 
    })


@login_required
def private_campaign(request):
    # Get user and profile data with improved following logic
    user_profile = get_object_or_404(Profile, user=request.user)
    category_filter = request.GET.get('category', '')
    
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]

    # Get private campaigns with not_interested annotation
    campaigns = Campaign.objects.annotate(
        is_not_interested=Case(
            When(not_interested_by__user=user_profile, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )

    # Filter visible private campaigns using following_user_ids
    visible_campaigns = campaigns.filter(
        Q(user__user__id__in=following_user_ids) | Q(user=user_profile),
        visibility='private',
        is_not_interested=False
    ).filter(
        Q(visible_to_followers=user_profile) | Q(user=user_profile)
    )

    # Apply category filter if provided
    if category_filter:
        visible_campaigns = visible_campaigns.filter(category=category_filter)

    visible_campaigns = visible_campaigns.order_by('-timestamp')

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Notifications and messages
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()

    # New campaigns from follows using consistent following_user_ids
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids, 
        visibility='private', 
        timestamp__gt=user_profile.last_campaign_check
    ).exclude(id__in=NotInterested.objects.filter(user=user_profile).values_list('campaign_id', flat=True)) \
     .order_by('-timestamp')

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    # Ads and categories
    ads = NativeAd.objects.all()
    categories = Campaign.objects.filter(
        Q(user__user__id__in=following_user_ids) | Q(user=user_profile),
        visibility='private'
    ).values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'private_campaigns': visible_campaigns,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'unread_messages_count': unread_messages_count,
        'categories': categories,
        'selected_category': category_filter,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/private_campaign.html', context)

import time

@login_required
def update_visibilit(request, campaign_id):
    start_time = time.time()  # Start timing

    # Get user and campaign data
    user_profile = get_object_or_404(Profile, user=request.user)
    
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    # Get followers for visibility settings
    followers = Profile.objects.filter(user__in=Follow.objects.filter(followed=request.user).values('follower'))
    campaign = get_object_or_404(Campaign, pk=campaign_id, user=user_profile)

    # Handle form submission
    if request.method == 'POST':
        form = UpdateVisibilityForm(request.POST, instance=campaign, followers=followers)
        if form.is_valid():
            campaign = form.save(commit=False)
            if campaign.visibility == 'private':
                campaign.visible_to_followers.set(form.cleaned_data['followers_visibility'])
            campaign.save()
            return redirect('private_campaign')
    else:
        form = UpdateVisibilityForm(instance=campaign, followers=followers)

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    end_time = time.time()  # End timing
    print(f"Form processing took {end_time - start_time} seconds")

    context = {
        'form': form,
        'campaign': campaign,
        'ads': ads,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/manage_campaign_visibility.html', context)



@login_required
def delete_campaign(request, campaign_id):
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        # Check if the current user is the owner of the campaign
        if request.user == campaign.user.user:
            # Delete the campaign
            campaign.delete()
        else:
            # Raise 403 Forbidden if the current user is not the owner of the campaign
            raise Http404("You are not allowed to delete this campaign.")
    except Campaign.DoesNotExist:
        raise Http404("Campaign does not exist.")
    
    # Redirect to a relevant page after deleting the campaign
    return redirect('private_campaign')








def success_page(request):
    return render(request, 'main/success_page.html')





def toggle_love(request, campaign_id):
    if request.method == 'POST' and request.user.is_authenticated:
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        user = request.user

        # Check if the user has already loved the campaign
        if Love.objects.filter(campaign=campaign, user=user).exists():
            # User has loved the campaign, remove the love
            Love.objects.filter(campaign=campaign, user=user).delete()
            love_count = campaign.love_count
        else:
            # User hasn't loved the campaign, add the love
            Love.objects.create(campaign=campaign, user=user)
            love_count = campaign.love_count

        # Return updated love count
        return JsonResponse({'love_count': love_count})

    # If the request method is not POST or user is not authenticated, return 404
    return JsonResponse({}, status=404)

from .models import CommentLike  # Adjust path if it's in another app

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Campaign
from django.db.models import Count, Case, When, Value, Q
from django.db.models.fields import CharField

# views.py
from django.http import JsonResponse

def record_campaign_view(request, campaign_id):
    if request.method == 'POST':
        # Handle logic (e.g., increment views)
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)




@login_required
def get_comments(request):
    campaign_id = request.GET.get('campaign_id')
    if not campaign_id:
        return JsonResponse({'error': 'Campaign ID is required'}, status=400)
    
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        # Get top-level comments (not replies)
        comments = campaign.comments.filter(parent_comment__isnull=True).annotate(
            like_count=Count('likes', filter=Q(likes__is_like=True)),
            dislike_count=Count('likes', filter=Q(likes__is_like=False)),
            reply_count=Count('replies'),
            user_like_status=Case(
                When(likes__user=request.user.profile, likes__is_like=True, then=Value('liked')),
                When(likes__user=request.user.profile, likes__is_like=False, then=Value('disliked')),
                default=Value(None),
                output_field=CharField()  # Changed from models.CharField() to CharField()
            )
        ).order_by('-timestamp')
        
        # Prepare comments data for JSON response
        comments_data = []
        for comment in comments:
            profile_image_url = comment.user.image.url if comment.user.image else None
            comments_data.append({
                'id': comment.id,
                'user_username': comment.user.user.username,
                'user_profile_image': request.build_absolute_uri(profile_image_url) if profile_image_url else None,
                'text': comment.text,
                'timestamp': comment.timestamp.isoformat(),
                'like_count': comment.like_count,
                'dislike_count': comment.dislike_count,
                'reply_count': comment.reply_count,
                'user_like_status': comment.user_like_status,
                'is_reply': False,  # This is a top-level comment
            })
        
        return JsonResponse({'comments': comments_data})
    except Campaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)

@login_required
def post_comment(request):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user.profile
            
            campaign_id = request.POST.get('campaign_id')
            parent_comment_id = request.POST.get('parent_comment_id')
            
            try:
                campaign = Campaign.objects.get(pk=campaign_id)
                comment.campaign = campaign
                
                if parent_comment_id:
                    parent_comment = Comment.objects.get(pk=parent_comment_id)
                    comment.parent_comment = parent_comment
                
                comment.save()
                
                # Return the new comment data
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'user_username': comment.user.user.username,
                        'user_profile_image': comment.user.image.url if comment.user.image else None,
                        'text': comment.text,
                        'timestamp': comment.timestamp.isoformat(),
                        'like_count': 0,
                        'dislike_count': 0,
                        'reply_count': 0,
                        'user_like_status': None,
                        'is_reply': parent_comment_id is not None,
                    }
                })
            except (Campaign.DoesNotExist, Comment.DoesNotExist):
                return JsonResponse({'error': 'Campaign or parent comment not found'}, status=404)
        else:
            return JsonResponse({'error': 'Invalid form data', 'details': form.errors}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
@require_POST
def like_dislike_comment(request):
    comment_id = request.POST.get('comment_id')
    action = request.POST.get('action')  # 'like', 'dislike', or 'remove'
    
    if not comment_id or not action:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        comment = Comment.objects.get(pk=comment_id)
        profile = request.user.profile
        
        # Check if user already liked/disliked this comment
        try:
            like = CommentLike.objects.get(user=profile, comment=comment)
            
            if action == 'remove' or (action == 'like' and like.is_like) or (action == 'dislike' and not like.is_like):
                # Remove the like/dislike
                like.delete()
                return JsonResponse({
                    'success': True, 
                    'action': 'removed',
                    'like_count': comment.likes.filter(is_like=True).count(),
                    'dislike_count': comment.likes.filter(is_like=False).count()
                })
            else:
                # Update existing like/dislike
                like.is_like = action == 'like'
                like.save()
                return JsonResponse({
                    'success': True, 
                    'action': 'updated',
                    'like_count': comment.likes.filter(is_like=True).count(),
                    'dislike_count': comment.likes.filter(is_like=False).count()
                })
        except CommentLike.DoesNotExist:
            if action in ['like', 'dislike']:
                # Create new like/dislike
                CommentLike.objects.create(
                    user=profile,
                    comment=comment,
                    is_like=(action == 'like')
                )
                return JsonResponse({
                    'success': True, 
                    'action': 'added',
                    'like_count': comment.likes.filter(is_like=True).count(),
                    'dislike_count': comment.likes.filter(is_like=False).count()
                })
            else:
                return JsonResponse({'error': 'Invalid action for new interaction'}, status=400)
    except Comment.DoesNotExist:
        return JsonResponse({'error': 'Comment not found'}, status=404)

from django.db.models import Q, Count

@login_required
def get_replies(request, comment_id):
    try:
        comment = Comment.objects.get(pk=comment_id)
        replies = comment.replies.annotate(
    like_count=Count('likes', filter=Q(likes__is_like=True)),
    dislike_count=Count('likes', filter=Q(likes__is_like=False)),
    user_like_status=Case(
        When(likes__user=request.user.profile, likes__is_like=True, then=Value('liked')),
        When(likes__user=request.user.profile, likes__is_like=False, then=Value('disliked')),
        default=Value(None),
        output_field=CharField()
    )
).order_by('timestamp')


        
        replies_data = []
        for reply in replies:
            profile_image_url = reply.user.image.url if reply.user.image else None
            replies_data.append({
                'id': reply.id,
                'user_username': reply.user.user.username,
                'user_profile_image': request.build_absolute_uri(profile_image_url) if profile_image_url else None,
                'text': reply.text,
                'timestamp': reply.timestamp.isoformat(),
                'like_count': reply.like_count,
                'dislike_count': reply.dislike_count,
                'user_like_status': reply.user_like_status,
                'is_reply': True,
            })
        
        return JsonResponse({'replies': replies_data})
    except Comment.DoesNotExist:
        return JsonResponse({'error': 'Comment not found'}, status=404)






@login_required
def home(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign_id = request.GET.get('campaign_id')
    category_filter = request.GET.get('category', '')
    
    if campaign_id:
        campaign = get_object_or_404(Campaign, pk=campaign_id)
    else:
        campaign = Campaign.objects.first()

    user = request.user
    already_loved = campaign and user != campaign.user and Love.objects.filter(campaign=campaign, user=user).exists()

    # Get campaigns, annotate whether the user marked them as "not interested"
    campaigns = Campaign.objects.annotate(
        is_not_interested=Case(
            When(not_interested_by__user=user_profile, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).filter(is_not_interested=False, visibility='public')

    if category_filter:
        campaigns = campaigns.filter(category=category_filter)

    campaigns = campaigns.order_by('-timestamp')

    # Get users the current user is following
    following_users = request.user.following.values_list('followed', flat=True)
    followed_campaigns = campaigns.filter(user__user__in=following_users)
    own_campaigns = campaigns.filter(user=user_profile)
    campaigns_to_display = followed_campaigns | own_campaigns
    # FIX: Annotate campaigns with sound community data properly
    campaigns_with_sound_data = []
    for camp in campaigns_to_display:
        sound_data = {
            'member_count': camp.get_sound_tribe_members_count(),
            'user_reaction': camp.get_user_reaction(user_profile) if request.user.is_authenticated else None,
            'campaign_id': camp.id  # Add campaign ID for JS reference
        }
        campaigns_with_sound_data.append((camp, sound_data))

    # Trending campaigns
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)\
      

    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()
    
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    ).exclude(id__in=NotInterested.objects.filter(user=user_profile).values_list('campaign_id', flat=True)).order_by('-timestamp')

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    ads = NativeAd.objects.all()
    categories = Campaign.objects.values_list('category', flat=True).distinct()

    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]

    # Top Contributors logic
    engaged_users = set()
    
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
         activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]
 
    return render(request, 'main/home.html', {
        'ads': ads,
        'public_campaigns': campaigns_to_display if campaigns_to_display.exists() else trending_campaigns,
        'campaign': Campaign.objects.last(),
        'already_loved': already_loved,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'new_campaigns_from_follows': new_campaigns_from_follows,
      
        'categories': categories,
        'selected_category': category_filter,
        'trending_campaigns': trending_campaigns,
        'suggested_users': suggested_users,
        'top_contributors': top_contributors,
    })











@login_required
def face(request):
    form = SubscriptionForm()
    following_users = [follow.followed for follow in request.user.following.all()]
    user_profile = get_object_or_404(Profile, user=request.user)
    category_filter = request.GET.get('category', '')  # Get category filter from request

    campaign = Campaign.objects.last()

    if user_profile.last_campaign_check is None:
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()

    new_private_campaigns_count = Campaign.objects.filter(
        visibility='private',
        timestamp__gt=user_profile.last_campaign_check
    ).count()

    # Debugging output
    print(f"Last Campaign Check: {user_profile.last_campaign_check}")
    print(f"New Private Campaigns Count: {new_private_campaigns_count}")

    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)\
      

    # ✅ Apply category filter before slicing
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]  # Show top 10 trending campaigns

    # Top Contributors logic
    engaged_users = set()

    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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
    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]  # Top 5

    ads = NativeAd.objects.all()
    categories = Campaign.objects.values_list('category', flat=True).distinct()  # Fetch unique categories

    return render(request, 'main/face.html', {
        'ads': ads,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'form': form,
        'new_private_campaigns_count': new_private_campaigns_count,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,  # Pass categories to template
        'selected_category': category_filter,  # Pass selected category to retain state
    })









@login_required
def campaign_comments(request, campaign_id):
    # Retrieve campaign object
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    user_profile = get_object_or_404(Profile, user=request.user)
    
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return HttpResponseForbidden("Campaign does not exist.")

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user.profile
            comment.campaign_id = campaign_id
            comment.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CommentForm()

    comments = Comment.objects.filter(campaign_id=campaign_id).order_by('-timestamp')
    
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    # Fetch unread messages for the user
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(
        chat__in=user_chats
    ).exclude(sender=request.user).count()

    # Check if there are new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]


    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
      

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic

    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'campaign': campaign,
        'comments': comments,
        'form': form,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/campaign_comments.html', context)


def campaign_support(request, campaign_id):
    # Get basic campaign and user data
    user_profile = None
    following_user_ids = []
    
    if request.user.is_authenticated:
        # Get following user IDs using the improved pattern
        current_user_following = request.user.following.all()
        following_user_ids = [follow.followed_id for follow in current_user_following]
        user_profile = get_object_or_404(Profile, user=request.user)
        # Update last campaign check time
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()

    support_campaign = SupportCampaign.objects.filter(campaign_id=campaign_id).first()
    
    # Notifications and messages
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False) if request.user.is_authenticated else []
    
    # New campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check if user_profile else timezone.now()
    ) if request.user.is_authenticated else []

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    engaged_users = set()
  
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    # Suggested users (only for authenticated users)
    suggested_users = []
    if request.user.is_authenticated:
        all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
        
        for profile in all_profiles:
            similarity_score = calculate_similarity(user_profile, profile)
            if similarity_score >= 0.5:
                followers_count = Follow.objects.filter(followed=profile.user).count()
                suggested_users.append({
                    'user': profile.user,
                    'followers_count': followers_count
                })
        suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'support_campaign': support_campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/campaign_support.html', context)







@login_required
def recreate_campaign(request, campaign_id):
    # Import Campaign at the top of the function to avoid scope issues
    from main.models import Campaign, Profile, Tag, CampaignTag, Love, Comment, CampaignView, \
                           ActivityLove, ActivityComment, Notification, NativeAd, Follow
    
    # ================ SECURITY CHECK ================
    # Get the campaign first to check ownership
    existing_campaign = get_object_or_404(Campaign, pk=campaign_id)
    
    # Check if user owns this campaign
    user_profile = get_object_or_404(Profile, user=request.user)
    if existing_campaign.user != user_profile:
        messages.error(request, "You don't have permission to edit this campaign.")
        return redirect('home')
    
    # ================ SUBSCRIPTION VALIDATION ================
    # Check if user has permission to edit campaigns
    subscription = UserSubscription.get_for_user(request.user)
    
    # If user doesn't have active subscription, check campaign count
    if not subscription.has_active_subscription():
        user_campaign_count = Campaign.objects.filter(user=user_profile).count()
        
        # Check if user has reached their free limit
        if user_campaign_count >= subscription.campaign_limit:
            messages.warning(
                request,
                "You've reached your free campaign limit. Upgrade to Rallynex Pro to edit or create more campaigns."
            )
            return redirect('subscription_required')
    
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    categories = Campaign.CATEGORY_CHOICES

    # Handle form submission
    if request.method == 'POST':
        form = CampaignForm(request.POST, request.FILES, instance=existing_campaign)
        if form.is_valid():
            # Save campaign first to get ID
            campaign = form.save(commit=False)
            
            # Handle Canva poster data (if provided)
            canva_poster_data = request.POST.get('canva_poster_data')
            if canva_poster_data:
                try:
                    canva_data = json.loads(canva_poster_data)
                    # Download and save the Canva poster
                    response = requests.get(canva_data['previewUrl'])
                    if response.status_code == 200:
                        img_name = f"canva_poster_{campaign.user.username}_{int(time.time())}.png"
                        img_content = ContentFile(response.content)
                        campaign.poster.save(img_name, img_content, save=False)
                except Exception as e:
                    print(f"Error processing Canva poster: {e}")
                    # Continue without Canva poster if there's an error
            
            # Save campaign to get ID before handling multiple images
            campaign.save()
            
            # =================== HANDLE MAIN POSTER ===================
            keep_current_poster = request.POST.get('keep_current_poster') == 'on'
            main_poster = request.FILES.get('poster')
            
            if keep_current_poster and existing_campaign.poster:
                # Keep the existing poster
                campaign.poster = existing_campaign.poster
            elif main_poster:
                # Upload new poster to Cloudinary
                try:
                    upload_result = cloudinary.uploader.upload(
                        main_poster,
                        folder="campaign_files",
                        transformation=[
                            {'width': 1200, 'crop': 'limit'},
                            {'quality': 'auto'},
                            {'format': 'auto'}
                        ]
                    )
                    campaign.poster = upload_result['secure_url']
                except Exception as e:
                    print(f"Error uploading main poster: {e}")
                    # If upload fails, keep existing poster as fallback
                    if existing_campaign.poster:
                        campaign.poster = existing_campaign.poster
            
            # =================== HANDLE ADDITIONAL IMAGES ===================
            additional_images = request.FILES.getlist('additional_images')  # Get all uploaded files
            
            # Upload new additional images for slideshow
            additional_image_urls = []
            for idx, image in enumerate(additional_images[:4]):  # Limit to 4 new images
                if image:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            image,
                            folder="campaign_files/slideshow",
                            public_id=f"{campaign.id}_{idx}_{int(time.time())}",
                            transformation=[
                                {'width': 1200, 'crop': 'limit'},
                                {'quality': 'auto'},
                                {'format': 'auto'}
                            ]
                        )
                        additional_image_urls.append(upload_result['secure_url'])
                    except Exception as e:
                        print(f"Error uploading additional image {idx}: {e}")
            
            # Check if user wants to keep existing additional images
            keep_existing_images = request.POST.get('keep_existing_images') == 'on'
            existing_additional = []
            
            if keep_existing_images and hasattr(existing_campaign, 'additional_images') and existing_campaign.additional_images:
                # Collect which existing images to keep
                idx = 0
                for existing_img_url in existing_campaign.additional_images:
                    keep_key = f'keep_existing_image_{idx}'
                    if request.POST.get(keep_key) == 'on':
                        existing_additional.append(existing_img_url)
                    idx += 1
            
            # Combine existing and new additional images (limit to 4 total)
            all_additional_images = existing_additional + additional_image_urls
            campaign.additional_images = all_additional_images[:4]  # Ensure max 4
            
            # =================== HANDLE POSTER FROM ADDITIONAL IMAGES ===================
            # If no main poster (user didn't keep current and didn't upload new)
            # but we have additional images, use first additional image as main poster
            if not campaign.poster and all_additional_images:
                # If we have existing additional images, use the first one
                if existing_additional:
                    campaign.poster = existing_additional[0]
                    # Remove first image from additional_images since it's now the main poster
                    if len(all_additional_images) > 1:
                        campaign.additional_images = all_additional_images[1:4]  # Keep next 3
                    else:
                        campaign.additional_images = []
                elif additional_image_urls:
                    campaign.poster = additional_image_urls[0]
                    # Remove first image from additional_images since it's now the main poster
                    if len(additional_image_urls) > 1:
                        campaign.additional_images = additional_image_urls[1:4]  # Keep next 3
                    else:
                        campaign.additional_images = []
            
            campaign.save()
            
            # =================== HANDLE TAGS ===================
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
                
                # Clear existing tags and add new ones
                campaign.tags.clear()
                for tag_name in tag_names:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name.lower(),
                        defaults={'slug': tag_name.lower().replace(' ', '-')}
                    )
                    CampaignTag.objects.create(
                        campaign=campaign,
                        tag=tag,
                        added_by=request.user
                    )
            
            messages.success(request, 'Campaign updated successfully!')
            return redirect('view_campaign', campaign_id=existing_campaign.id)
        else:
            messages.error(request, 'There were errors in your form. Please correct them below.')
    else:
        form = CampaignForm(instance=existing_campaign)
        # Pre-populate tags input with existing tags
        existing_tags = ', '.join([tag.name for tag in existing_campaign.tags.all()])
        form.fields['tags_input'].initial = existing_tags

    # 🔥 Trending campaigns (Only those with at least 1 love)
    from django.db.models import Count
    from itertools import chain
    from collections import defaultdict
    
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public',
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()
    
    # Prepare existing images data for template
    existing_images = []
    if existing_campaign.poster:
        existing_images.append({
            'url': existing_campaign.poster.url,
            'is_main': True,
            'index': 0
        })
    
    if hasattr(existing_campaign, 'additional_images') and existing_campaign.additional_images:
        for idx, img_url in enumerate(existing_campaign.additional_images):
            existing_images.append({
                'url': img_url,
                'is_main': False,
                'index': idx + 1
            })

    context = {
        'ads': ads,
        'form': form,
        'categories': categories,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'existing_campaign': existing_campaign,
        'existing_images': existing_images,  # Pass images to template
        'has_additional_images': hasattr(existing_campaign, 'additional_images') and 
                                existing_campaign.additional_images and 
                                len(existing_campaign.additional_images) > 0
    }
    
    return render(request, 'main/recreatecampaign_form.html', context)









def success_page(request):
    return render(request, 'main/success.html')


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
from itertools import chain
from collections import defaultdict

from .models import (
    Campaign, Profile, Notification, Follow, Love, Comment, 
    CampaignView, ActivityLove, ActivityComment, NativeAd, Tag, CampaignTag
)
from .forms import CampaignForm




# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
from itertools import chain
from collections import defaultdict
import json
import requests
from django.core.files.base import ContentFile
import time
import cloudinary
import cloudinary.uploader
from .models import *
from .forms import CampaignForm





@login_required
def create_campaign(request):
    # Get or create subscription for user
    subscription = UserSubscription.get_for_user(request.user)
    
    # Check if user can create campaign
    if not subscription.can_create_campaign():
        messages.warning(
            request,
            "You've reached your free campaign limit. Upgrade to Rallynex Pro to create unlimited campaigns."
        )
        return redirect('subscription_required')
    following_users = [follow.followed for follow in request.user.following.all()]
    user_profile = get_object_or_404(Profile, user=request.user)
    categories = Campaign.CATEGORY_CHOICES

    if request.method == 'POST':
        form = CampaignForm(request.POST, request.FILES)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user.profile
            
            # Handle Canva poster data
            canva_poster_data = request.POST.get('canva_poster_data')
            if canva_poster_data:
                try:
                    canva_data = json.loads(canva_poster_data)
                    response = requests.get(canva_data['previewUrl'])
                    if response.status_code == 200:
                        img_name = f"canva_poster_{campaign.user.username}_{int(time.time())}.png"
                        img_content = ContentFile(response.content)
                        campaign.poster.save(img_name, img_content, save=False)
                except Exception as e:
                    print(f"Error processing Canva poster: {e}")
            
            # Save to get ID (without processing audio through CloudinaryField)
            # We'll handle audio separately
            
            # Handle main poster
            main_poster = request.FILES.get('poster')
            if main_poster:
                try:
                    upload_result = cloudinary.uploader.upload(
                        main_poster,
                        folder="campaign_files",
                        transformation=[
                            {'width': 1200, 'crop': 'limit'},
                            {'quality': 'auto'},
                            {'format': 'auto'}
                        ]
                    )
                    campaign.poster = upload_result['secure_url']
                except Exception as e:
                    print(f"Error uploading main poster: {e}")
            
            # Handle additional images
            additional_images = request.FILES.getlist('additional_images')
            additional_image_urls = []
            
            for idx, image in enumerate(additional_images[:4]):
                if image:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            image,
                            folder="campaign_files/slideshow",
                            public_id=f"{campaign.id}_{idx}_{int(time.time())}",
                            transformation=[
                                {'width': 1200, 'crop': 'limit'},
                                {'quality': 'auto'},
                                {'format': 'auto'}
                            ]
                        )
                        additional_image_urls.append(upload_result['secure_url'])
                    except Exception as e:
                        print(f"Error uploading additional image {idx}: {e}")
            
            # IMPORTANT: Set audio to None initially to avoid CloudinaryField auto-upload
            campaign.audio = None
            
            # Save the campaign first
            campaign.save()
            
            # NOW handle audio upload separately
            audio_file = request.FILES.get('audio')
            if audio_file:
                try:
                    # Validate file size (10MB max)
                    if audio_file.size > 10 * 1024 * 1024:
                        messages.error(request, 'Audio file is too large. Maximum size is 10MB.')
                        # Delete the partially created campaign
                        campaign.delete()
                        return render(request, 'main/campaign_form.html', {
                            'form': form,
                            'categories': categories,
                            'user_profile': user_profile,
                            'unread_notifications': Notification.objects.filter(user=request.user, viewed=False),
                            'new_campaigns_from_follows': Campaign.objects.filter(
                                user__user__in=following_users, 
                                visibility='public', 
                                timestamp__gt=user_profile.last_campaign_check
                            ),
                            'trending_campaigns': Campaign.objects.filter(visibility='public')
                                .annotate(love_count_annotated=Count('loves'))
                                .filter(love_count_annotated__gte=1)
                                .order_by('-love_count_annotated')[:10],
                        })
                    
                    # Validate file type
                    file_name = audio_file.name.lower()
                    allowed_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
                    is_valid_extension = any(file_name.endswith(ext) for ext in allowed_extensions)
                    
                    if not is_valid_extension:
                        messages.error(request, 'Invalid audio format. Please upload MP3, WAV, OGG, M4A, or AAC files.')
                        campaign.delete()
                        return render(request, 'main/campaign_form.html', {
                            'form': form,
                            'categories': categories,
                            'user_profile': user_profile,
                            'unread_notifications': Notification.objects.filter(user=request.user, viewed=False),
                            'new_campaigns_from_follows': Campaign.objects.filter(
                                user__user__in=following_users, 
                                visibility='public', 
                                timestamp__gt=user_profile.last_campaign_check
                            ),
                            'trending_campaigns': Campaign.objects.filter(visibility='public')
                                .annotate(love_count_annotated=Count('loves'))
                                .filter(love_count_annotated__gte=1)
                                .order_by('-love_count_annotated')[:10],
                        })
                    
                    print(f"Uploading audio file: {audio_file.name}, size: {audio_file.size} bytes")
                    
                    # Upload to Cloudinary with resource_type='video' for audio
                    upload_result = cloudinary.uploader.upload(
                        audio_file,
                        resource_type='video',  # This is CRITICAL for audio files
                        folder="campaign_audio",
                        public_id=f"campaign_{campaign.id}_audio_{int(time.time())}",
                    )
                    
                    # Update campaign with audio URL
                    campaign.audio = upload_result['secure_url']
                    campaign.save()  # Save again with audio URL
                    
                    print(f"✓ Audio uploaded successfully: {upload_result['secure_url']}")
                    
                except Exception as e:
                    print(f"✗ Error uploading audio: {e}")
                    # Don't delete the campaign, just continue without audio
                    messages.warning(request, 'Audio upload failed, but campaign was created. You can add audio later.')
            
            # Handle additional images logic
            if additional_image_urls:
                campaign.additional_images = additional_image_urls
                if not main_poster and additional_image_urls:
                    campaign.poster = additional_image_urls[0]
                    if len(additional_image_urls) > 1:
                        campaign.additional_images = additional_image_urls[1:]
                    else:
                        campaign.additional_images = []
                campaign.save()
            
            # Handle tags using the form's save method
            # We need to manually handle tags since we already saved the campaign
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                # Clear existing tags
                campaign.tags.clear()
                
                # Add new tags
                tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
                for tag_name in tag_names:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name.lower(),
                        defaults={'slug': tag_name.lower().replace(' ', '-')}
                    )
                    campaign.tags.add(tag)
            
            # Update user's last campaign check
            user_profile.last_campaign_check = timezone.now()
            user_profile.save()
            
            messages.success(request, 'Campaign created successfully!')
            return redirect('view_campaign', campaign_id=campaign.pk)
        else:
            messages.error(request, 'There were errors in your form. Please correct them below.')
    else:
        form = CampaignForm()

    # Fetch unread notifications
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check for new campaigns from follows
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Trending campaigns
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    from itertools import chain
    from collections import defaultdict
    
    engaged_users = set()
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain(love_pairs, comment_pairs, view_pairs,
                      activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]

    # Suggested users logic
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
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

    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'form': form,
        'categories': categories,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'is_pro': subscription.has_active_subscription(),
        'campaign_count': subscription.get_campaign_count(),
        'campaign_limit': subscription.campaign_limit,
    }
    
    return render(request, 'main/campaign_form.html', context)





def poster_canva(request):
    return render(request, 'main/poster_canva.html', {
        'username': request.user.username
    })



def video_canva(request):
    return render(request, 'main/video_canva.html', {
        'username': request.user.username
    })



@login_required
def home(request):
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign_id = request.GET.get('campaign_id')
    category_filter = request.GET.get('category', '')
    
    if campaign_id:
        campaign = get_object_or_404(Campaign, pk=campaign_id)
    else:
        campaign = Campaign.objects.first()

    user = request.user
    already_loved = campaign and user != campaign.user and Love.objects.filter(campaign=campaign, user=user).exists()

    # Get campaigns, annotate whether the user marked them as "not interested"
    campaigns = Campaign.objects.annotate(
        is_not_interested=Case(
            When(not_interested_by__user=user_profile, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).filter(is_not_interested=False, visibility='public')

    if category_filter:
        campaigns = campaigns.filter(category=category_filter)

    campaigns = campaigns.order_by('-timestamp')

    # Get users the current user is following
    following_users = request.user.following.values_list('followed', flat=True)
    followed_campaigns = campaigns.filter(user__user__in=following_users)
    own_campaigns = campaigns.filter(user=user_profile)
    campaigns_to_display = followed_campaigns | own_campaigns

    # Trending campaigns
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)\
      

    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_chats = Chat.objects.filter(participants=request.user)
    unread_messages_count = Message.objects.filter(chat__in=user_chats).exclude(sender=request.user).count()
    
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    ).exclude(id__in=NotInterested.objects.filter(user=user_profile).values_list('campaign_id', flat=True)).order_by('-timestamp')

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    ads = NativeAd.objects.all()
    categories = Campaign.objects.values_list('category', flat=True).distinct()

    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]

    # Top Contributors logic
    engaged_users = set()
    
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
         activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]
 
    return render(request, 'main/home.html', {
        'ads': ads,
        'public_campaigns': campaigns_to_display if campaigns_to_display.exists() else trending_campaigns,
        'campaign': Campaign.objects.last(),
        'already_loved': already_loved,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,
        'new_campaigns_from_follows': new_campaigns_from_follows,
      
        'categories': categories,
        'selected_category': category_filter,
        'trending_campaigns': trending_campaigns,
        'suggested_users': suggested_users,
        'top_contributors': top_contributors,
    })





@login_required
def face(request):
    form = SubscriptionForm()
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request

    campaign = Campaign.objects.last()
    user_profile = None

    if request.user.is_authenticated:
        user_profile = get_object_or_404(Profile, user=request.user)

        if user_profile.last_campaign_check is None:
            user_profile.last_campaign_check = timezone.now()
            user_profile.save()

        new_private_campaigns_count = Campaign.objects.filter(
            visibility='private',
            timestamp__gt=user_profile.last_campaign_check
        ).count()

    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Get suggested users with followers count
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)\
     

    # ✅ Apply category filter before slicing
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]  # Show top 10 trending campaigns

    # Top Contributors logic
    engaged_users = set()
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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
    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]  # Top 5

    ads = NativeAd.objects.all()
    categories = Campaign.objects.values_list('category', flat=True).distinct()  # Fetch unique categories

    return render(request, 'main/face.html', {
        'ads': ads,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'form': form,
        'new_private_campaigns_count': new_private_campaigns_count,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,  # Pass categories to template
        'selected_category': category_filter,  # Pass selected category to retain state
    })



def follower_list(request, username):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    user = User.objects.get(username=username)
    followers = Follow.objects.filter(followed=user)
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check if there are new campaigns from follows (using consistent following_user_ids)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()  
    
    # Get suggested users with improved logic
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)\
     

    # Apply category filter if provided
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
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'user': user,
        'followers': followers,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }

    return render(request, 'main/follower_list.html', context)

def following_list(request, username):
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    user_profile = get_object_or_404(Profile, user=request.user)
    user = User.objects.get(username=username)
    following = Follow.objects.filter(follower=user)
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # Check if there are new campaigns from follows (using consistent following_user_ids)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()
    
    # Get suggested users with improved logic
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            # Get followers count for each suggested user
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)\
     

    # Apply category filter if provided
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
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'user': user,
        'following': following,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }

    return render(request, 'main/following_list.html', context)


@login_required
@require_POST
def toggle_follow(request):
    try:
        data = json.loads(request.body)
        user_to_follow_id = data.get('user_id')
        
        if not user_to_follow_id:
            return JsonResponse({'status': 'error', 'message': 'User ID required'}, status=400)

        try:
            user_to_follow = User.objects.get(pk=user_to_follow_id)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)

        if request.user == user_to_follow:
            return JsonResponse({'status': 'error', 'message': 'Cannot follow yourself'}, status=400)

        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            followed=user_to_follow
        )

        if not created:
            follow.delete()
            action = 'unfollowed'
            is_following = False
        else:
            action = 'followed'
            is_following = True

        return JsonResponse({
            'status': 'success',
            'action': action,
            'followers_count': user_to_follow.followers.count(),
            'is_following': is_following  # Explicit state
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



# views.py
from django.http import JsonResponse

@require_POST
def follow_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Login required'}, status=403)
    
    user_to_follow = get_object_or_404(User, id=user_id)
    
    if request.user == user_to_follow:
        return JsonResponse({'status': 'error', 'message': 'Cannot follow yourself'}, status=400)
    
    _, created = Follow.objects.get_or_create(
        follower=request.user,
        followed=user_to_follow
    )
    
    return JsonResponse({
        'status': 'success',
        'action': 'follow',
        'followed_id': user_id
    })

@require_POST
def unfollow_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Login required'}, status=403)
    
    user_to_unfollow = get_object_or_404(User, id=user_id)
    deleted, _ = Follow.objects.filter(
        follower=request.user,
        followed=user_to_unfollow
    ).delete()
    
    return JsonResponse({
        'status': 'success',
        'action': 'unfollow',
        'unfollowed_id': user_id
    })


@login_required
def profile_edit(request, username):
    following_users = [follow.followed for follow in request.user.following.all()]
    category_filter = request.GET.get('category', '')  # Get category filter from request
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_profile = get_object_or_404(Profile, user=request.user)
    user = get_object_or_404(User, username=username)
    profile, created = Profile.objects.get_or_create(user=user)
    
    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__in=following_users, 
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    
    ads = NativeAd.objects.all()
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('home')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    # Improved suggested users logic
    current_user_following = request.user.following.all()  # Get all Follow objects
    following_user_ids = [follow.followed_id for follow in current_user_following]  # Extract user IDs
    
    # Exclude current user and already followed users
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

    # Limit to 2 suggested users
    suggested_users = suggested_users[:2]

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
       

    # Apply category filter if provided
    if category_filter:
        trending_campaigns = trending_campaigns.filter(category=category_filter)

    trending_campaigns = trending_campaigns.order_by('-love_count_annotated')[:10]

    # Top Contributors logic
  
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
        'ads': ads,
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'username': username,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/edit_profile.html', context)






from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Profile, Follow



from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from itertools import chain
from collections import defaultdict
from .models import Profile, Follow, Campaign, Notification, Love, Comment, CampaignView, ActivityLove, ActivityComment, NativeAd

@login_required
def profile_view(request, username):
    # Get the User object, not Profile
    user_obj = get_object_or_404(User, username=username)
    
    # Get the user's profile
    user_profile = get_object_or_404(Profile, user=user_obj)
    
    # ✅ FIXED: Pass User objects, not Profile
    following_profile = Follow.objects.filter(
        follower=request.user, 
        followed=user_obj  # Use user_obj (User), not user_profile.user
    ).exists()
    
    # ✅ FIXED: Use User objects here too
    followers_count = Follow.objects.filter(followed=user_obj).count()
    following_count = Follow.objects.filter(follower=user_obj).count()
    
    # Get public campaigns (user_profile is already a Profile object)
    public_campaigns = user_profile.user_campaigns.filter(visibility='public').order_by('-timestamp')
    public_campaigns_count = public_campaigns.count()
    
    # Rest of your code remains the same...
    changemaker_campaigns = [campaign for campaign in public_campaigns if campaign.is_changemaker]
    
    # Determine the most appropriate campaign
    most_appropriate_campaign = None
    if changemaker_campaigns:
        first_campaign = min(changemaker_campaigns, key=lambda campaign: campaign.timestamp)
        most_impactful_campaign = max(changemaker_campaigns, key=lambda campaign: campaign.love_count)
        
        if most_impactful_campaign.love_count == first_campaign.love_count:
            most_appropriate_campaign = max(changemaker_campaigns, key=lambda campaign: campaign.timestamp)
        else:
            most_appropriate_campaign = most_impactful_campaign
    
    category_display = most_appropriate_campaign.get_category_display() if most_appropriate_campaign else None
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # Get suggested users with followers count
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    
    # Exclude current user and already followed users
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__id__in=following_user_ids)
    
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count_suggested = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count_suggested
            })

    # Limit to only 2 suggested users
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()
    
    # ✅ IMPORTANT: Make sure you're passing the right objects
    context = {
        'user_profile': user_profile,  # Profile object
        'user_obj': user_obj,          # User object (optional, for clarity)
        'following_profile': following_profile,
        'followers_count': followers_count,
        'following_count': following_count,
        'public_campaigns': public_campaigns,
        'public_campaigns_count': public_campaigns_count,
        'changemaker_category': category_display,
        'ads': ads,
        'unread_notifications': unread_notifications,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/user_profile.html', context)















def search_profile_results(request):
    if 'search_query' in request.GET:
        form = ProfileSearchForm(request.GET)
        if form.is_valid():
            search_query = form.cleaned_data['search_query']
            results = Profile.objects.filter(user__username__icontains=search_query)
            return render(request, 'main/search_profile_results.html', {'search_results': results, 'query': search_query})
    return render(request, 'main/search_profile_results.html', {'search_results': [], 'query': ''})




# main/views.py - UPDATED VERSION
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Blog
import json

def blog_list(request):
    """Display list of published blog posts"""
    blogs = Blog.objects.filter(status='published').order_by('-created_at')
    return render(request, 'marketing/blog_list.html', {'blogs': blogs})

def blog_detail(request, slug):
    """Display individual blog post"""
    blog_post = get_object_or_404(Blog, slug=slug, status='published')
    
    # Increment view count
    blog_post.view_count = blog_post.view_count + 1
    blog_post.save()
    
    # Get related posts (same category, exclude current)
    related_posts = Blog.objects.filter(
        category=blog_post.category,
        status='published'
    ).exclude(id=blog_post.id).order_by('-created_at')[:3]
    
    # If not enough related posts, get latest
    if len(related_posts) < 3:
        additional = Blog.objects.filter(
            status='published'
        ).exclude(id=blog_post.id).order_by('-created_at')[:3-len(related_posts)]
        related_posts = list(related_posts) + list(additional)
    
    # Get next/previous posts
    next_post = Blog.objects.filter(
        created_at__gt=blog_post.created_at,
        status='published'
    ).order_by('created_at').first()
    
    prev_post = Blog.objects.filter(
        created_at__lt=blog_post.created_at,
        status='published'
    ).order_by('-created_at').first()
    
    # Add current year for copyright
    current_year = timezone.now().year
    
    return render(request, 'marketing/blog_detail.html', {
        'blog_post': blog_post,
        'related_posts': related_posts,
        'next_post': next_post,
        'prev_post': prev_post,
        'current_year': current_year,
    })

def blog_view_increment(request, slug):
    """AJAX endpoint to increment view count"""
    if request.method == 'POST':
        try:
            blog = Blog.objects.get(slug=slug)
            blog.view_count += 1
            blog.save()
            return JsonResponse({'success': True, 'view_count': blog.view_count})
        except Blog.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Blog not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

@require_POST
@csrf_exempt
def blog_like(request, slug):
    """Handle blog post likes via AJAX"""
    blog = get_object_or_404(Blog, slug=slug)
    
    # Simple implementation - just increment
    blog.like_count = blog.like_count + 1
    blog.save()
    
    return JsonResponse({
        'success': True, 
        'like_count': blog.like_count
    })

@require_POST
@csrf_exempt
def newsletter_subscribe(request):
    """Handle newsletter subscriptions"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if email:
            # Here you would save to your newsletter database
            # For now, just return success
            return JsonResponse({
                'success': True, 
                'message': 'Subscribed successfully!'
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': 'Please provide a valid email'
            })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error: {str(e)}'
        })

def blog_share(request, slug):
    """Track social shares - redirects back to blog"""
    blog = get_object_or_404(Blog, slug=slug)
    
    # Increment share count
    blog.share_count = blog.share_count + 1
    blog.save()
    
    # Get the platform from query params
    platform = request.GET.get('platform', 'unknown')
    
    # Redirect back to blog
    return redirect('blog_detail', slug=slug)






from .models import CampaignStory

def campaign_story_list(request):
    stories = CampaignStory.objects.all().order_by('-created_at')  # Order by creation date in descending order
    return render(request, 'marketing/story_list.html', {'stories': stories})


def campaign_story_detail(request, slug):
    story = get_object_or_404(CampaignStory, slug=slug)
    return render(request, 'marketing/story_detail.html', {'story': story})



def success_stories(request):
    return render(request, 'marketing/success_stories.html')


def testimonial(request):
    return render(request, 'marketing/testimonial.html')




from .models import FAQ
# views.py
def faq_view(request):
    categories = []
    for choice in FAQ.CATEGORY_CHOICES:
        faqs = FAQ.objects.filter(category=choice[0])
        if faqs.exists():  # Only include categories with FAQs
            categories.append({
                'name': choice[1],
                'code': choice[0],
                'faqs': faqs
            })
    
    return render(request, 'marketing/faq.html', {'categories': categories})

def hiw(request):
    return render(request, 'marketing/hiw.html')

def aboutus(request):
    return render(request, 'marketing/aboutus.html')


def fund(request):
    return render(request, 'marketing/fund.html')


def geno(request):
    return render(request, 'marketing/geno.html')





from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Pledge, Campaign
from .forms import PledgeForm

@login_required
def create_pledge(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if request.method == 'POST':
        form = PledgeForm(request.POST, user=request.user, campaign=campaign)
        if form.is_valid():
            pledge = form.save(commit=False)
            pledge.user = request.user
            pledge.save()
            messages.success(request, 'Your pledge has been created successfully!')
            return redirect('view_campaign', campaign_id=campaign.id)
    else:
        form = PledgeForm(user=request.user, campaign=campaign)

    # User data and following
    user_profile = get_object_or_404(Profile, user=request.user)
    following_users = request.user.following.values_list('followed', flat=True)
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    ads = NativeAd.objects.all()

    # Suggested users
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []
    
    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })
    suggested_users = suggested_users[:2]

    # Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
 
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    # Combine all engagement pairs
    all_pairs = chain( love_pairs, comment_pairs, view_pairs,
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

    context = {
        'form': form,
        'campaign': campaign,
        'user_profile': user_profile,
        'ads': ads,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    return render(request, 'main/create_pledge.html', context)



from collections import defaultdict
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import Campaign, Pledge, Profile, NativeAd, Follow, Love, Comment, CampaignView, ActivityLove, ActivityComment


@login_required
def campaign_pledgers_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    pledges = Pledge.objects.filter(campaign=campaign).order_by('-timestamp')

    # Counts
    fulfilled_count = pledges.filter(is_fulfilled=True).count()
    pending_count = pledges.filter(is_fulfilled=False).count()
    total_count = pledges.count()

    # Clean contacts for WhatsApp links
    for pledge in pledges:
        if pledge.contact:
            pledge.cleaned_contact = ''.join(filter(str.isdigit, pledge.contact))
        else:
            pledge.cleaned_contact = ''

    # User profile + following
    user_profile = get_object_or_404(Profile, user=request.user)
    following_users = request.user.following.values_list('followed', flat=True)
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    ads = NativeAd.objects.all()

    # Suggested users
    current_user_following = user_profile.following.all()
    all_profiles = Profile.objects.exclude(user=request.user).exclude(user__in=current_user_following)
    suggested_users = []

    for profile in all_profiles:
        similarity_score = calculate_similarity(user_profile, profile)
        if similarity_score >= 0.5:
            followers_count = Follow.objects.filter(followed=profile.user).count()
            suggested_users.append({
                'user': profile.user,
                'followers_count': followers_count
            })
    suggested_users = suggested_users[:2]

    # Trending campaigns (with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top contributors
    love_pairs = Love.objects.values_list('user_id', 'campaign_id')
    comment_pairs = Comment.objects.values_list('user_id', 'campaign_id')
    view_pairs = CampaignView.objects.values_list('user_id', 'campaign_id')
    activity_love_pairs = ActivityLove.objects.values_list('user_id', 'activity__campaign_id')
    activity_comment_pairs = ActivityComment.objects.values_list('user_id', 'activity__campaign_id')

    all_pairs = chain(love_pairs, comment_pairs, view_pairs, activity_love_pairs, activity_comment_pairs)

    user_campaign_map = defaultdict(set)
    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

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

    top_contributors = sorted(contributor_data, key=lambda x: x['campaign_count'], reverse=True)[:5]

    return render(request, 'main/pledges.html', {
        'campaign': campaign,
        'pledges': pledges,
        'user_profile': user_profile,
        'ads': ads,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'fulfilled_count': fulfilled_count,
        'pending_count': pending_count,
        'total_count': total_count,
    })







# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
@login_required
def toggle_pledge_fulfillment(request, pledge_id):
    pledge = get_object_or_404(Pledge, id=pledge_id)
    
    # Verify the requesting user is the campaign owner
    if request.user != pledge.campaign.user.user:
        messages.error(request, "You don't have permission to modify this pledge.")
        return redirect('view_campaign', campaign_id=pledge.campaign.id)
    
    new_status = pledge.toggle_fulfilled()
    messages.success(request, f"Pledge has been marked as {'fulfilled' if new_status else 'unfulfilled'}.")
    return redirect('view_campaign', campaign_id=pledge.campaign.id)




def edit_gif(request):

   return render(request, 'main/edit.html', {
       
    })





@login_required
def product_manage(request, campaign_id=None, product_id=None):
    # Initialize variables
    campaign = None
    product = None

    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    user_profile = get_object_or_404(Profile, user=request.user)

    # Fetch campaign and product if IDs are provided
    if campaign_id:
        campaign = get_object_or_404(Campaign, pk=campaign_id)
    if product_id:
        product = get_object_or_404(CampaignProduct, pk=product_id)

    # Handle form submission
    if request.method == 'POST':
        form = CampaignProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.campaign = campaign
            
            # If stock quantity is 0, set is_active to False
            if product.stock_quantity == 0:
                product.is_active = False
                
            product.save()
            
            if campaign:
                return redirect('product_manage', campaign_id=campaign.id)
            else:
                return redirect('product_manage')
    else:
        form = CampaignProductForm(instance=product)
    
    # Fetch all products for the campaign
    products = CampaignProduct.objects.filter(campaign=campaign).order_by('-date_added') if campaign else None
    product_count = products.count() if products else 0

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # User notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'form': form,
        'product': product,
        'campaign': campaign,
        'products': products,
        'product_count': product_count,
        'unread_notifications': unread_notifications,
        'user_profile': user_profile,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/product_manage.html', context)





@login_required
def toggle_product_status(request, product_id):
    product = get_object_or_404(CampaignProduct, id=product_id)
    
    # Check if the user owns the campaign
    if product.campaign.user.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        # Toggle the is_active status
        product.is_active = not product.is_active
        product.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': product.is_active,
                'message': f'Product {"activated" if product.is_active else "deactivated"} successfully'
            })
    
    return redirect('product_manage', campaign_id=product.campaign.id)

@login_required
def mark_out_of_stock(request, product_id):
    product = get_object_or_404(CampaignProduct, id=product_id)
    
    # Check if the user owns the campaign
    if product.campaign.user.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        # Set stock to 0 and deactivate
        product.stock_quantity = 0
        product.is_active = False
        product.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Product marked as out of stock and removed from market'
            })
    
    return redirect('product_manage', campaign_id=product.campaign.id)



from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Cart, CartItem, CampaignProduct


@login_required
def view_cart(request):
    # Get or create cart for the current user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product').all()
    
    # Get following user IDs using the improved pattern
    current_user_following = request.user.following.all()
    following_user_ids = [follow.followed_id for follow in current_user_following]
    user_profile = get_object_or_404(Profile, user=request.user)

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter(visibility='public') \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

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

    # User notifications and follows
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    new_campaigns_from_follows = Campaign.objects.filter(
        user__user__id__in=following_user_ids,
        visibility='public', 
        timestamp__gt=user_profile.last_campaign_check
    )
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # Suggested users with improved logic
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
    suggested_users = suggested_users[:2]

    ads = NativeAd.objects.all()

    context = {
        'ads': ads,
        'cart': cart,
        'cart_items': cart_items,
        'unread_notifications': unread_notifications,
        'user_profile': user_profile,
        'new_campaigns_from_follows': new_campaigns_from_follows,
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'page_title': 'Your Shopping Cart',
    }
    
    return render(request, 'main/cart.html', context)



@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(CampaignProduct, id=product_id, is_active=True)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if product is already in cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, 
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        # Increment quantity if product already in cart
        if cart_item.quantity < product.stock_quantity:
            cart_item.quantity += 1
            cart_item.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Added {product.name} to cart',
            'total_items': cart.total_items,
            'total_price': str(cart.total_price)
        })
    
    return redirect('view_cart')

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'increase':
            if cart_item.quantity < cart_item.product.stock_quantity:
                cart_item.quantity += 1
                cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
        elif action == 'remove':
            cart_item.delete()
        elif action == 'set_quantity':
            quantity = int(request.POST.get('quantity', 1))
            if 1 <= quantity <= cart_item.product.stock_quantity:
                cart_item.quantity = quantity
                cart_item.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart = Cart.objects.get(user=request.user)
        return JsonResponse({
            'success': True,
            'item_total': str(cart_item.total_price),
            'cart_total': str(cart.total_price),
            'total_items': cart.total_items,
            'item_quantity': cart_item.quantity
        })
    
    return redirect('view_cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart = Cart.objects.get(user=request.user)
        return JsonResponse({
            'success': True,
            'cart_total': str(cart.total_price),
            'total_items': cart.total_items
        })
    
    return redirect('view_cart')






# views.py - Updated with unique function names
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from .models import Campaign, Donation
from .paypal_utils import create_donation_paypal_order, capture_donation_paypal_order, send_donation_payout, process_donation_split
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def create_donation(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                messages.error(request, "Please enter a valid donation amount.")
                return render(request, "main/donation_form.html", {"campaign": campaign})
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid donation amount.")
            return render(request, "main/donation_form.html", {"campaign": campaign})
        
        # Create a donation record
        donation = Donation.objects.create(
            user=request.user,
            campaign=campaign,
            amount=amount_float,
            fulfilled=False
        )
        
        # Create PayPal order using the unique function name
        return_url = request.build_absolute_uri(
            reverse('donation_payment_callback', kwargs={'donation_id': donation.id})
        )
        cancel_url = request.build_absolute_uri(reverse('donation_failure'))
        
        try:
            order = create_donation_paypal_order(amount_float, campaign.id, return_url, cancel_url)
            
            if order and 'id' in order:
                donation.paypal_order_id = order['id']
                donation.save()
                
                # Find approval URL
                for link in order.get('links', []):
                    if link.get('rel') == 'approve':
                        return redirect(link['href'])
            
            messages.error(request, "Failed to create PayPal order. Please try again.")
            logger.error(f"PayPal order creation failed for donation {donation.id}")
            return redirect('view_campaign', campaign_id=campaign.id)
            
        except Exception as e:
            messages.error(request, "An error occurred while processing your donation.")
            logger.error(f"Error creating PayPal order: {e}")
            return redirect('view_campaign', campaign_id=campaign.id)
    
    return render(request, "main/donation_form.html", {"campaign": campaign})

@login_required
def donation_payment_callback(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, user=request.user)
    
    if request.GET.get('token') and request.GET.get('PayerID'):
        try:
            # Capture the payment using unique function name
            capture_result = capture_donation_paypal_order(donation.paypal_order_id)
            
            if capture_result and capture_result.get('status') == 'COMPLETED':
                donation.fulfilled = True
                donation.save()
                
                # Process the payout split
                platform_share, campaign_owner_share = process_donation_split(donation.amount)
                
                # Get the campaign owner
                campaign_owner_profile = donation.campaign.user
                
                # Check if the campaign owner has a PayPal email
                if campaign_owner_profile.paypal_email:
                    payout_note = f"Donation to your campaign: {donation.campaign.title}"
                    payout_result = send_donation_payout(
                        campaign_owner_profile.paypal_email,
                        campaign_owner_share,
                        payout_note,
                        f"donation_{donation.id}_owner"
                    )
                    
                    if payout_result and payout_result.get('batch_header', {}).get('payout_batch_id'):
                        donation.paypal_payout_id = payout_result['batch_header']['payout_batch_id']
                        donation.save()
                    else:
                        logger.warning(f"Payout to campaign owner failed for donation {donation.id}")
                else:
                    logger.warning(f"Campaign owner has no PayPal email for donation {donation.id}")
                    # Store this information for manual processing later
                    donation.paypal_payout_id = "PENDING_NO_PAYPAL_EMAIL"
                    donation.save()
                
                # Send payout to platform (10%)
                if hasattr(settings, 'PAYPAL_PLATFORM_ACCOUNT') and settings.PAYPAL_PLATFORM_ACCOUNT:
                    platform_payout_result = send_donation_payout(
                        settings.PAYPAL_PLATFORM_ACCOUNT,
                        platform_share,
                        f"Platform fee for donation #{donation.id}",
                        f"donation_{donation.id}_platform"
                    )
                    
                    if not platform_payout_result:
                        logger.warning(f"Platform payout failed for donation {donation.id}")
                else:
                    logger.error("PAYPAL_PLATFORM_ACCOUNT not configured in settings")
                
                messages.success(request, "Thank you for your donation!")
                return redirect('donation_success', donation_id=donation.id)
            else:
                messages.error(request, "Payment capture failed. Please try again.")
                logger.error(f"Payment capture failed for donation {donation.id}: {capture_result}")
                return redirect('donation_failure')
                
        except Exception as e:
            messages.error(request, "An error occurred while processing your payment.")
            logger.error(f"Error processing payment callback: {e}")
            return redirect('donation_failure')
    
    messages.error(request, "Payment authorization failed.")
    return redirect('donation_failure')

@login_required
def donation_success(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, user=request.user)
    return render(request, "main/donation_success.html", {"donation": donation})

@login_required
def donation_failure(request):
    return render(request, "main/donation_failure.html")

# Additional utility view for checking donation status
@login_required
def donation_status(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, user=request.user)
    return JsonResponse({
        'donation_id': donation.id,
        'amount': str(donation.amount),
        'campaign': donation.campaign.title,
        'fulfilled': donation.fulfilled,
        'paypal_order_id': donation.paypal_order_id,
        'paypal_payout_id': donation.paypal_payout_id,
        'timestamp': donation.timestamp.isoformat()
    })



from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib.sessions.models import Session
from .models import Campaign, Pledge
from .pledge_utils import create_paypal_pledge_order, capture_paypal_order, send_paypal_payout, process_pledge_split
import json
import logging
import time

logger = logging.getLogger(__name__)

def pledge_payment_page(request, pledge_id):
    """Display the pledge payment page (works for anonymous + logged-in users)."""
    pledge = get_object_or_404(Pledge, id=pledge_id)
    campaign = pledge.campaign
    return render(request, "main/pledge_payment.html", {
        "pledge": pledge,
        "campaign": campaign,
    })

def initiate_pledge_payment(request, pledge_id):
    """Initiate PayPal payment for a pledge."""
    pledge = get_object_or_404(Pledge, id=pledge_id)

    # Save session key for anonymous tracking
    if not pledge.user and not pledge.session_key:
        pledge.session_key = request.session.session_key or request.session.create()
        pledge.save()

    return_url = request.build_absolute_uri(
        reverse('pledge_payment_callback', kwargs={'pledge_id': pledge.id})
    )
    cancel_url = request.build_absolute_uri(reverse('pledge_failure'))

    # Convert Decimal amount to float for PayPal
    amount_float = float(pledge.amount)

    # Create PayPal order with the correct function
    order = create_paypal_pledge_order(
        amount_float,           # amount (converted to float)
        pledge.campaign.id,     # campaign_id
        return_url,             # return_url
        cancel_url,             # cancel_url
        f"Pledge to campaign: {pledge.campaign.title}"  # description
    )

    if order and 'id' in order:
        pledge.paypal_order_id = order['id']
        pledge.payment_status = 'processing'
        pledge.save()

        # Find approval URL
        for link in order.get('links', []):
            if link.get('rel') == 'approve':
                return redirect(link['href'])

    messages.error(request, "Failed to create PayPal order. Please try again.")
    logger.error(f"PayPal order creation failed for pledge {pledge.id}")
    return redirect('pledge_payment_page', pledge_id=pledge.id)

def pledge_payment_callback(request, pledge_id):
    """Handle PayPal payment callback for both anonymous + logged-in users."""
    pledge = get_object_or_404(Pledge, id=pledge_id)

    if request.GET.get('token') and request.GET.get('PayerID'):
        try:
            # Capture the payment
            capture_result = capture_paypal_order(pledge.paypal_order_id)
            
            # Debug logging
            logger.info(f"Capture result type: {type(capture_result)}")
            logger.info(f"Capture result: {capture_result}")

            # Handle case where function returns a tuple (data, error)
            if isinstance(capture_result, tuple) and len(capture_result) == 2:
                capture_data, error = capture_result
                if error is not None:
                    logger.error(f"PayPal capture error: {error}")
                    capture_result = {"error": str(error), "status": "failed"}
                else:
                    capture_result = capture_data

            # Check if capture was successful
            if (capture_result and 
                isinstance(capture_result, dict) and 
                capture_result.get('status') == 'COMPLETED'):
                
                pledge.is_fulfilled = True
                pledge.payment_status = 'completed'
                pledge.save()

                # Process split
                platform_share, campaign_owner_share = process_pledge_split(pledge.amount)

                campaign_owner_profile = pledge.campaign.user

                # Simple retry mechanism for payouts (3 attempts with exponential backoff)
                max_retries = 3
                payout_success = False
                
                # Send payout to campaign owner (50%)
                if hasattr(campaign_owner_profile, "paypal_email") and campaign_owner_profile.paypal_email:
                    for attempt in range(max_retries):
                        try:
                            payout_result = send_paypal_payout(
                                campaign_owner_profile.paypal_email,
                                campaign_owner_share,
                                f"Pledge to your campaign: {pledge.campaign.title}",
                                f"pledge_{pledge.id}_owner"
                            )
                            
                            if payout_result and payout_result.get('batch_header', {}).get('payout_batch_id'):
                                pledge.paypal_payout_id = payout_result['batch_header']['payout_batch_id']
                                pledge.save()
                                payout_success = True
                                break  # Success, exit retry loop
                            elif attempt == max_retries - 1:
                                logger.warning(f"Payout to campaign owner failed after {max_retries} attempts for pledge {pledge.id}")
                        except Exception as e:
                            if attempt == max_retries - 1:
                                logger.error(f"Payout failed after {max_retries} attempts: {e}")
                            # Wait before retrying (exponential backoff: 1s, 2s, 4s)
                            time.sleep(2 ** attempt)
                else:
                    logger.warning(f"Campaign owner missing PayPal email for pledge {pledge.id}")

                # Only send platform share if campaign owner payout succeeded
                if payout_success and getattr(settings, "PAYPAL_PLATFORM_ACCOUNT", None):
                    # Retry logic for platform payout too
                    for attempt in range(max_retries):
                        try:
                            platform_payout_result = send_paypal_payout(
                                settings.PAYPAL_PLATFORM_ACCOUNT,
                                platform_share,
                                f"Platform fee for pledge #{pledge.id}",
                                f"pledge_{pledge.id}_platform"
                            )
                            if platform_payout_result:
                                break  # Success or at least we tried
                            elif attempt == max_retries - 1:
                                logger.warning(f"Platform payout failed after {max_retries} attempts for pledge {pledge.id}")
                        except Exception as e:
                            if attempt == max_retries - 1:
                                logger.error(f"Platform payout failed after {max_retries} attempts: {e}")
                            time.sleep(2 ** attempt)
                elif not getattr(settings, "PAYPAL_PLATFORM_ACCOUNT", None):
                    logger.error("PAYPAL_PLATFORM_ACCOUNT not configured in settings")

                return redirect('pledge_success', pledge_id=pledge.id)
            else:
                # Capture failed
                logger.error(f"PayPal capture failed for order {pledge.paypal_order_id}: {capture_result}")
                pledge.payment_status = 'failed'
                pledge.save()
                messages.error(request, "Payment capture failed. Please try again.")
                return redirect('pledge_failure')

        except Exception as e:
            pledge.payment_status = 'failed'
            pledge.save()
            logger.error(f"Error processing payment callback: {e}")
            messages.error(request, "An error occurred while processing your payment.")
            return redirect('pledge_failure')

    messages.error(request, "Payment authorization failed.")
    return redirect('pledge_failure')

def pledge_success(request, pledge_id):
    """Display success page with payout breakdown."""
    pledge = get_object_or_404(Pledge, id=pledge_id)
    platform_share, campaign_owner_share = process_pledge_split(pledge.amount)

    return render(request, "main/pledge_success.html", {
        'pledge': pledge,
        'platform_share': platform_share,
        'campaign_owner_share': campaign_owner_share
    })

def pledge_failure(request):
    """Display failure page."""
    return render(request, "main/pledge_failure.html")








# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings

from .models import CampaignProduct, Transaction
from .products_utils import create_paypal_order, capture_paypal_order, send_product_payout
import logging

logger = logging.getLogger(__name__)

@login_required
def initiate_paypal_payment(request, product_id):
    """
    Create a PayPal order for a product purchase
    """
    product = get_object_or_404(CampaignProduct, id=product_id)

    if not product.can_be_purchased():
        messages.error(request, "This product is not available for purchase.")
        return redirect('product_detail', product_id=product_id)

    # Get quantity from request
    try:
        quantity = int(request.POST.get("quantity", 1))
        if quantity < 1 or quantity > product.stock_quantity:
            messages.error(request, "Invalid quantity selected.")
            return redirect('product_detail', product_id=product_id)
    except (ValueError, TypeError):
        quantity = 1

    order, error = create_paypal_order(product, request.user, quantity, request)

    if error:
        messages.error(request, f"Payment Error: {error}")
        return redirect('payment_failure')

    # Redirect user to PayPal approval URL
    for link in order.get("links", []):
        if link.get("rel") == "approve":
            return redirect(link["href"])

    messages.error(request, "No PayPal approval link found.")
    return redirect('payment_failure')

@csrf_exempt
def paypal_payment_callback(request):
    """
    Handle PayPal callback after approval - SIMPLIFIED for redirect flow
    """
    order_id = request.GET.get("token")
    
    if not order_id:
        # Try to get from POST data (some PayPal flows might use POST)
        order_id = request.POST.get("token")
    
    if not order_id:
        logger.error("PayPal callback: Missing order ID")
        messages.error(request, "Missing payment information. Please contact support.")
        return redirect("payment_failure")

    # Capture the payment
    capture_data, error = capture_paypal_order(order_id)
    
    if error:
        logger.error(f"PayPal capture failed: {error}")
        messages.error(request, "Payment failed. Please try again.")
        return redirect("payment_failure")

    # Check if capture was successful
    if capture_data.get('status') != 'COMPLETED':
        logger.error(f"PayPal capture not completed: {capture_data}")
        messages.error(request, "Payment was not completed successfully.")
        return redirect("payment_failure")

    # Find transaction in our DB
    try:
        transaction = Transaction.objects.get(tx_ref=order_id)
    except Transaction.DoesNotExist:
        logger.error(f"Transaction not found for order ID: {order_id}")
        messages.error(request, "Transaction not found. Please contact support.")
        return redirect("payment_failure")

    # Update transaction status
    capture_id = None
    try:
        capture_id = capture_data.get('purchase_units', [{}])[0].get('payments', {}).get('captures', [{}])[0].get('id')
    except (IndexError, KeyError, AttributeError):
        logger.warning("Could not extract capture ID from PayPal response")

    transaction.mark_as_successful(capture_id)

    # Trigger payout to seller (optional - can be done manually later)
    if settings.PAYPAL_ENABLE_PAYOUTS:
        try:
            success, payout_error = send_product_payout(transaction)
            if not success:
                logger.warning(f"Payout failed: {payout_error}")
                # Don't show this error to user - it's a backend issue
        except Exception as e:
            logger.error(f"Payout error: {str(e)}")

    messages.success(request, "Payment successful! Thank you for your purchase.")
    return redirect("payment_success", transaction_id=transaction.id)

@login_required
def payment_success(request, transaction_id):
    """
    Show success page after payment.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id, buyer=request.user)
    return render(request, "main/payment_success.html", {
        "transaction": transaction,
        "product": transaction.product
    })

@login_required
def payment_failure(request):
    """
    Show failure page
    """
    return render(request, "main/payment_failure.html")

@login_required
def transaction_history(request):
    """
    Show user's transaction history
    """
    transactions = Transaction.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, "main/transaction_history.html", {"transactions": transactions})



# views.py - Add these imports
import json
import time
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib import messages

# ==================== PAYPAL VIEWS ====================
@login_required
def subscription_required(request):
    """Display subscription upgrade page with PayPal payment option"""
    from main.models import UserSubscription
    
    # Get user's subscription
    subscription = UserSubscription.get_for_user(request.user)
    
    context = {
        'paypal_business_email': getattr(settings, 'PAYPAL_BUSINESS_EMAIL', ''),
        'paypal_button_id': getattr(settings, 'PAYPAL_SUBSCRIPTION_BUTTON_ID', ''),
        'subscription': subscription,
        'campaign_count': subscription.get_campaign_count(),
    }
    
    return render(request, 'main/subscription_required.html', context)
# views.py - PAYPAL SECTION
@csrf_exempt
def paypal_webhook(request):
    """
    Handle PayPal IPN (Instant Payment Notification) webhook
    """
    try:
        # Verify the IPN is genuine
        data = request.POST.copy()
        data['cmd'] = '_notify-validate'
        
        # Use PayPal's IPN URL (use sandbox for testing)
        paypal_url = 'https://ipnpb.paypal.com/cgi-bin/webscr'  # LIVE
        
        # Post back to PayPal for verification
        response = requests.post(
            paypal_url,
            data=data,
            timeout=10
        )
        
        if response.text == 'VERIFIED':
            # Payment was verified
            txn_type = data.get('txn_type')
            payer_email = data.get('payer_email')
            subscr_id = data.get('subscr_id')
            custom_field = data.get('custom')  # This contains user ID
            
            print(f"\n{'='*60}")
            print(f"🔔 PayPal IPN verified: {txn_type}")
            print(f"📧 Payer email: {payer_email}")
            print(f"🔢 Subscription ID: {subscr_id}")
            print(f"👤 Custom field (user ID): {custom_field}")
            print(f"{'='*60}")
            
            if txn_type in ['subscr_signup', 'subscr_payment']:
                # New subscription or payment - USE CUSTOM FIELD FOR USER ID
                subscription = UserSubscription.handle_paypal_subscription(
                    payer_email=payer_email,
                    subscr_id=subscr_id,
                    custom_data=custom_field  # Pass user ID from custom field
                )
                if subscription:
                    print(f"🎉 PayPal subscription activated for {subscription.user.username}")
                else:
                    print(f"⚠️ Failed to activate PayPal subscription")
            
            elif txn_type in ['subscr_cancel', 'subscr_eot', 'subscr_failed']:
                # Subscription cancelled, ended, or failed
                try:
                    subscription = UserSubscription.objects.get(
                        paypal_subscription_id=subscr_id
                    )
                    if txn_type == 'subscr_failed':
                        subscription.status = 'payment_failed'
                    else:
                        subscription.status = 'cancelled'
                    subscription.save()
                    print(f"📝 PayPal subscription {subscr_id} status updated to: {subscription.status}")
                except UserSubscription.DoesNotExist:
                    print(f"⚠️ PayPal subscription not found: {subscr_id}")
            
            # Log the full data for debugging
            print(f"📦 Full IPN data (first 10 items):")
            for key, value in list(data.items())[:10]:
                print(f"   {key}: {value}")
        
        elif response.text == 'INVALID':
            print(f"❌ Invalid PayPal IPN")
            return HttpResponse(status=400)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        print(f"❌ PayPal webhook error: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse(status=400)

@login_required
def paypal_return(request):
    """
    Handle return from PayPal after payment
    """
    # For testing: Get subscription ID from URL if available
    subscr_id = request.GET.get('subscr_id', f'LOCAL-TEST-{int(time.time())}')
    
    subscription = UserSubscription.get_for_user(request.user)
    
    # AUTO-ACTIVATE FOR LOCALHOST TESTING
    subscription.status = 'active'
    subscription.payment_provider = 'paypal'
    subscription.paypal_subscription_id = subscr_id
    subscription.campaign_limit = 9999
    subscription.save()
    
    print(f"✅ Manual activation via paypal_return for {request.user.username}")
    messages.success(request, "✅ Subscription activated successfully!")
    return redirect('success_page')

@login_required
def paypal_cancel(request):
    """
    Handle cancellation from PayPal
    """
    messages.info(request, "Your PayPal payment was cancelled.")
    return redirect('subscription_required')
# ==================== COMMON VIEWS ====================
@login_required
def success_page(request):
    # Get user's subscription
    subscription = UserSubscription.get_for_user(request.user)
    
    context = {
        'is_pro': subscription.has_active_subscription(),
        'subscription': subscription,
        'payment_provider': subscription.payment_provider,
    }
    
    return render(request, 'main/success-page.html', context)





from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
import json

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q

# CORRECTED: DM View Functions
@login_required
def start_dm(request, user_id):
    """Start or go to a direct message conversation"""
    # Get the User object from user_id
    other_user = get_object_or_404(User, id=user_id)
    
    # Find existing conversation
    conversation = Conversation.objects.filter(
        Q(user1=request.user, user2=other_user) |
        Q(user1=other_user, user2=request.user)
    ).first()
    
    # Create new conversation if doesn't exist
    if not conversation:
        # Always store user1 as the one with smaller ID to avoid duplicates
        user1, user2 = sorted([request.user, other_user], key=lambda u: u.id)
        conversation = Conversation.objects.create(
            user1=user1,
            user2=user2
        )
    
    return redirect('dm_page', dm_id=conversation.id)



@login_required
def dm_page(request, dm_id):
    """Display the DM conversation page"""
    conversation = get_object_or_404(
        Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ),
        id=dm_id
    )
    
    # Get other user
    other_user = conversation.user2 if conversation.user1 == request.user else conversation.user1
    
    # ✅ FIX: MARK ALL MESSAGES AS READ when user opens conversation
    DirectMessage.objects.filter(
        conversation=conversation,
        recipient=request.user,
        read=False
    ).update(
        read=True,
        read_at=timezone.now()
    )
    
    # Get messages (exclude deleted ones)
    messages = conversation.direct_messages.filter(
        Q(deleted_by_sender=False) & 
        Q(deleted_by_recipient=False)
    ).order_by('timestamp')
    
    # Update current user's last activity
    request.user.profile.update_last_activity()
    
    return render(request, 'dm/dm_page.html', {
        'conversation': conversation,
        'other_user': other_user,
        'messages': messages,
        'timezone': timezone
    })





# VIEW 3: Send a DM message (AJAX compatible)
@login_required
def send_dm_message(request, dm_id):
    """Handle sending a DM message"""
    if request.method == 'POST':
        conversation = get_object_or_404(
            Conversation.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ),
            id=dm_id
        )
        
        # Get other user
        other_user = conversation.user2 if conversation.user1 == request.user else conversation.user1
        
        # Get message content
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request
            data = json.loads(request.body)
            message_content = data.get('message', '').strip()
        else:
            # Regular form submission
            message_content = request.POST.get('message', '').strip()
        
        # Create message if not empty
        if message_content:
            dm = DirectMessage.objects.create(
                conversation=conversation,
                sender=request.user,
                recipient=other_user,
                content=message_content
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message_id': dm.id,
                    'sender': request.user.username,
                    'content': message_content,
                    'timestamp': dm.timestamp.strftime('%H:%M')
                })
        
        return redirect('dm_page', dm_id=dm_id)









@login_required
def dm_inbox(request):
    """Show all DM conversations for the current user"""
    # Get all conversations where user is participant
    conversations = Conversation.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).order_by('-updated_at')
    
    # Add unread count for each conversation
    for conv in conversations:
        conv.unread_count = DirectMessage.objects.filter(
            conversation=conv,
            recipient=request.user,
            read=False,
            deleted_by_recipient=False
        ).count()
    
    # Total unread count for badge
    total_unread = DirectMessage.objects.filter(
        recipient=request.user,
        read=False,
        deleted_by_recipient=False
    ).count()
    
    return render(request, 'dm/inbox.html', {
        'conversations': conversations,
        'total_unread': total_unread
    })


from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

@login_required
def update_activity(request):
    """Update current user's activity"""
    # Update cache
    cache.set(f'user_activity_{request.user.id}', timezone.now(), 300)
    
    # Update profile's last_activity field
    request.user.profile.last_activity = timezone.now()
    request.user.profile.save(update_fields=['last_activity'])
    
    return JsonResponse({'status': 'updated'})

@login_required
def check_status(request, user_id):
    """Check if a user is online"""
    # Try to get other user
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'is_online': False, 'last_seen': 'unknown'})
    
    # Check cache first
    last_activity_cache = cache.get(f'user_activity_{user_id}')
    
    # Check profile's last_activity field
    last_activity_profile = other_user.profile.last_activity
    
    # Use the most recent one
    if last_activity_cache and last_activity_cache > last_activity_profile:
        last_activity = last_activity_cache
    else:
        last_activity = last_activity_profile
    
    is_online = False
    last_seen_text = 'a while ago'
    
    if last_activity:
        # Calculate how long ago
        time_diff = timezone.now() - last_activity
        seconds_diff = time_diff.total_seconds()
        
        # User is online if active in last 2 minutes
        is_online = seconds_diff < 120
        
        if is_online:
            last_seen_text = 'just now'
        else:
            # Show human-readable time
            if seconds_diff < 60:  # 1 minute
                last_seen_text = 'just now'
            elif seconds_diff < 3600:  # 1 hour
                minutes = int(seconds_diff / 60)
                last_seen_text = f'{minutes} minute{"s" if minutes > 1 else ""} ago'
            elif seconds_diff < 86400:  # 1 day
                hours = int(seconds_diff / 3600)
                last_seen_text = f'{hours} hour{"s" if hours > 1 else ""} ago'
            else:
                days = int(seconds_diff / 86400)
                last_seen_text = f'{days} day{"s" if days > 1 else ""} ago'
    
    return JsonResponse({
        'is_online': is_online,
        'last_seen': last_seen_text
    })