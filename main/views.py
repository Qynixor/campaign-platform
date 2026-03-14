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
    SupportForm, CampaignSearchForm, ProfileSearchForm
)

from .models import (
    Profile, Campaign, Comment,Activity, SupportCampaign,
    User, Love, CampaignView, Notification
)

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

from django.views.decorators.http import require_POST


from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import mimetypes

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
from .models import Campaign, Profile, Notification, NotInterested, Love
from django.contrib.auth.models import AnonymousUser


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from itertools import chain
from collections import defaultdict
from .models import (
    Profile, Notification, Campaign, Love, Comment, 
    CampaignView, ActivityLove, ActivityComment, 
   
)
from .utils import calculate_similarity  # Make sure this import matches your project structure

from django.http import HttpResponse


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
from itertools import chain
from collections import defaultdict

from .models import (
    Campaign, Profile, Notification,  Love, Comment, 
    CampaignView, ActivityLove, ActivityComment,  CampaignTag
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




from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from .models import Profile
import json
import logging




from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Profile



from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from itertools import chain
from collections import defaultdict


from collections import defaultdict
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.utils import timezone








def robots_txt(request):
    content = """User-agent: *
Allow: /

Disallow: /admin/
Disallow: /accounts/
Disallow: /tinymce/


Sitemap: https://rallynex.com/sitemap.xml

"""
    return HttpResponse(content, content_type="text/plain")
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def supporters_view(request, username):
    """
    Empty template for now - will add dynamic data later
    """
    return render(request, 'main/supporters.html')


@login_required
def following_causes_view(request, username):
    """
    Empty template for now - will add dynamic data later
    """
    return render(request, 'main/following_causes.html')



from django.shortcuts import render

def new_causes_view(request):
    """
    Demo view for new causes
    """
    return render(request, 'main/new_causes.html')

def trending_causes_view(request):
    """
    Demo view for trending causes
    """
    return render(request, 'main/trending_causes.html')





















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
   
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
  
 
    # Pass data to the template



    # Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
    trending_campaigns = Campaign.objects.filter() \
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



    # Other template data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
 

    context = {
        'campaign': campaign,
        'top_participants': top_participants,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
      
        'form': form,
      
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/top_participants.html', context)


def explore_campaigns(request):
        # Fetch all public campaigns
    public_campaigns = Campaign.objects.filter()  # Adjust this query to match your actual filtering criteria
    
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


    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
 

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
    trending_campaigns = Campaign.objects.filter() \
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




    context = {
        'form': form,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
      
        'ads': ads,
     
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



class CampaignDeleteView(LoginRequiredMixin, DeleteView):
    model = Campaign
    template_name = 'main/campaign_confirm_delete.html'
    success_url = reverse_lazy('index')

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

        

        # User profile
        context['user_profile'] = user_profile

     
        # Update campaign check timestamp
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()


     

        # 🔥 Trending campaigns (Only those with at least 1 love)
        trending_campaigns = Campaign.objects.filter() \
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








    


def privacy_policy(request):
    return render(request, 'revenue/privacy_policy.html')

def terms_of_service(request):
    return render(request, 'revenue/terms_of_service.html')



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
    return redirect('index')

@login_required
def report_campaign(request, campaign_id):
    
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
    trending_campaigns = Campaign.objects.filter() \
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
    
    context = {
       
        'form': form,
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
    
     
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






def activity_detail(request, activity_id):
    # Get basic objects
    user_profile = get_object_or_404(Profile, user=request.user)
    activity = get_object_or_404(Activity, id=activity_id)
   
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Notification and messaging data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
     
        'activity': activity,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
    
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/activity_detail.html', context)






def add_activity_comment(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    user_profile = get_object_or_404(Profile, user=request.user)
   
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
          
    
            'trending_campaigns': trending_campaigns,
            'top_contributors': top_contributors,
            'categories': categories,
            'selected_category': category_filter,
        }
        
        return render(request, 'main/add_activity_comment.html', context)



@login_required
def suggest(request):
    
    return render(request, 'main/suggest.html', {
       
    })




@login_required
def support(request, campaign_id):
   
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
    
    # Update last check time
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
  

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
       
        'campaign': campaign,
        'support_campaign': support_campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
   
        'products': products,
   
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
   
    category_filter = request.GET.get('category', '')  # Get category filter from request
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    
    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
  
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
    
        'campaign': campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
   
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
    
    user_profile = get_object_or_404(Profile, user=request.user)
    query = request.GET.get('search_query')
    
    # Initialize empty querysets for all searchable models
    campaigns = Campaign.objects.none()
    profiles = Profile.objects.none()
  
    
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
        
    # Notifications handling
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    unread_notifications = notifications.filter(viewed=False)
    unread_notifications.update(viewed=True)
    unread_count = unread_notifications.count()
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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


    context = {
       
        'campaigns': campaigns,
        'profiles': profiles,
      
        'user_profile': user_profile,
        'unread_count': unread_count,
        'unread_notifications': unread_notifications,
     
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'search_query': query,  # Pass the search query back to template
    }
    
    return render(request, 'main/search_results.html', context)






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
    
    user_profile = get_object_or_404(Profile, user=request.user)
    category_filter = request.GET.get('category', '')  # Get category filter from request
    
    # Retrieve only active notifications for the logged-in user
    notifications = Notification.objects.filter(user=request.user, is_active=True).order_by('-timestamp')

    # Mark notifications as viewed
    unread_notifications = notifications.filter(viewed=False)
    unread_notifications.update(viewed=True)

    # Count unread notifications
    unread_count = unread_notifications.count()
    

    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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

    categories = Campaign.objects.values_list('category', flat=True).distinct()

    context = {
     
        'notifications': notifications,
        'user_profile': user_profile,
        'unread_count': unread_count,
        'unread_notifications': unread_notifications,
   
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    return render(request, 'main/notification_list.html', context)





from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from collections import defaultdict
from itertools import chain
import json
from django.core import serializers

def view_campaign(request, campaign_id):
    category_filter = request.GET.get('category', '')  # Get category filter from request
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    user_profile = None
    already_loved = False


        # Profile and loves
    user_profile = request.user.profile
    already_loved = Love.objects.filter(user=request.user, campaign=campaign).exists()

        # Track campaign view
    if not CampaignView.objects.filter(user=user_profile, campaign=campaign).exists():
        CampaignView.objects.create(user=user_profile, campaign=campaign)

        # Unread notifications
        unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    # 🔥 Trending campaigns
    trending_campaigns = Campaign.objects.filter() \
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

    # ====== FIX: Get campaign tags ======
    # Get all tags for this campaign
    campaign_tags = list(campaign.tags.all().values_list('name', flat=True))
    
    # Create a dictionary with this campaign's tags (for consistency with the previous approach)
    # But since this is a single campaign view, we can just pass the tags directly
    campaign_tags_dict = {
        str(campaign.id): campaign_tags
    }
    
    # Convert to JSON for JavaScript
    campaign_tags_json = json.dumps(campaign_tags_dict)
    # Fetch public campaigns, filter by category if selected
    campaigns = Campaign.objects.filter()
    # Create a dictionary to store join status for each campaign

    context = {
        'campaign': campaign,
        'campaign_tags': campaign_tags,  # Direct list of tags for Django template
        'campaign_tags_json': campaign_tags_json,  # JSON for JavaScript
    
        'user_profile': user_profile,
        'already_loved': already_loved,
        'unread_notifications': unread_notifications,
   
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
      

    }

    return render(request, 'main/campaign_detail.html', context)

def campaign_detail(request, pk):
    # Retrieve the campaign object using its primary key (pk)
    campaign = get_object_or_404(Campaign, pk=pk)
    
    # Pass the campaign object to the template for rendering
    return render(request, 'main/campaign_detail.html', {'campaign': campaign,'form':form})



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import json

# ==================== SOUND TRIBE VIEWS ====================


def thank_you(request):
    
    return render(request, 'main/thank_you.html')

@login_required
def load_more_activities(request):
    """Load more activities for infinite scroll"""
    campaign_id = request.GET.get('campaign_id')
    cursor = request.GET.get('cursor')  # Last activity ID
    
    activities = Activity.objects.filter(
        campaign_id=campaign_id,
        id__lt=cursor  # Get activities older than cursor
    ).order_by('-timestamp')[:5]  # Load 5 at a time
    
    data = [{
        'id': a.id,
        'day_number': a.day_number,
        'content': a.content,
        'file': a.file.url if a.file else None,
        'screenshots': [s.image.url for s in a.screenshots.all()],
        'love_count': a.loves.count(),
        'comment_count': a.comments.count(),
        'timestamp': a.timestamp.isoformat(),
        'time_ago': timesince(a.timestamp),
    } for a in activities]
    
    return JsonResponse({
        'activities': data,
        'next_cursor': activities.last().id if activities else None,
        'has_more': activities.count() == 5,
    })




@login_required
def activity_list(request, campaign_id):
   
    category_filter = request.GET.get('category', '')  # Get category filter from request
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Get all activities associated with the campaign with prefetch for screenshots
    activities = Activity.objects.filter(campaign=campaign).prefetch_related(
        'video_screenshots'
    ).order_by('-timestamp')
    
    # Add comment count for each activity and screenshot info
    for activity in activities:
        activity.comment_count = ActivityComment.objects.filter(activity=activity).count()
        # FIX: Don't try to set properties - use regular attributes instead
        activity.has_screenshots_var = activity.video_screenshots.exists()
        activity.screenshots_list = activity.video_screenshots.all().order_by('order')
        activity.screenshot_count_total = activity.screenshots_list.count()
    
    # List of image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    activity_count = activities.count()
    
    # Calculate progress percentage based on real-time duration
    if campaign.duration and campaign.duration > 0:
        if campaign.duration_unit == 'minutes':
            total_duration = campaign.duration
            elapsed = min(activity_count, total_duration)
            progress_percentage = (elapsed / total_duration) * 100
        else:
            # For days, use the days_left property for real-time tracking
            if campaign.days_left is not None:
                elapsed_days = campaign.duration - campaign.days_left
                progress_percentage = (elapsed_days / campaign.duration) * 100
            else:
                progress_percentage = (activity_count / campaign.duration) * 100
    else:
        # Ongoing campaign with no set duration
        progress_percentage = activity_count * 10  # Just a placeholder
        if progress_percentage > 100:
            progress_percentage = 100
    
    # Ensure progress percentage doesn't exceed 100
    progress_percentage = min(progress_percentage, 100)
    
    # Notification and messaging data
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1)
     

    # Apply category filter if provided
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

    # ===== NEW: Check if journey is completed =====
    from django.utils import timezone
    
    # Check if journey is completed (today > end_date)
    journey_completed = True
    post_products = []
    
    if campaign.end_date and timezone.now().date() > campaign.end_date.date():
        journey_completed = True
        # Get any products creator has added
        post_products = campaign.post_journey_products.filter(is_active=True)
    
    # Also check if all days are completed
    elif campaign.duration and activities.count() >= campaign.duration:
        journey_completed = True
        post_products = campaign.post_journey_products.filter(is_active=True)
    
    # Add video-specific context
    context = {
      
        'campaign': campaign, 
        'activities': activities, 
        'image_extensions': image_extensions,
        'user_profile': user_profile,
        'activity_count': activity_count,
        'progress_percentage': progress_percentage,
        'unread_notifications': unread_notifications,
            'journey_completed': journey_completed,
        'post_products': post_products,
      
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
        # Video processing context
        'video_processing_enabled': True,
        'supported_video_formats': ['mp4', 'mov', 'avi', 'webm', 'mkv'],
    }
    
    return render(request, 'main/activity_list.html', context)






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
from django.db import transaction, connection
from django.db.utils import InternalError, OperationalError
from django import forms
from django.urls import reverse
from cloudinary.models import CloudinaryResource
from django.http import JsonResponse
import time
import traceback

@login_required
def create_activity(request, campaign_id):
    """
    PROGRESSIVE ACTIVITY CREATION VIEW WITH DAY LOCKING AND VIDEO PROCESSING
    FIXED: Added proper database connection handling and transaction management
    """
    
    category_filter = request.GET.get('category', '')
    user_profile = get_object_or_404(Profile, user=request.user)
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # 🔒 Ensure user owns the campaign
    if campaign.user != user_profile:
        messages.error(request, "You can only create activities for your own campaigns.")
        return redirect('activity_list', campaign_id=campaign_id)

    # Get existing activities for this campaign, ordered by timestamp
    existing_activities = Activity.objects.filter(campaign=campaign).order_by('timestamp')
    existing_count = existing_activities.count()
    
    # ===== REAL-TIME DAY CALCULATION =====
    current_real_day = campaign.get_current_day()
    next_available_day = existing_count + 1
    is_next_day_locked = next_available_day > current_real_day
    
    if is_next_day_locked:
        days_until_unlock = next_available_day - current_real_day
    else:
        days_until_unlock = 0
    
    # Calculate how many forms to show
    MAX_FORMS = 10
    
    if existing_count >= MAX_FORMS:
        forms_to_show = MAX_FORMS
        empty_forms = 0
    else:
        forms_to_show = existing_count + 1
        empty_forms = 1
    
    # Create the formset
    ActivityFormSet = inlineformset_factory(
        Campaign,
        Activity,
        form=ActivityForm,
        extra=empty_forms,
        can_delete=True,
        max_num=MAX_FORMS,
        fields=['content', 'file', 'screenshot_count']
    )

    if request.method == 'POST':
        formset = ActivityFormSet(
            request.POST, 
            request.FILES, 
            instance=campaign,
            queryset=existing_activities
        )
        
        if formset.is_valid():
            try:
                # Close any stale connections before starting
                connection.close_if_unusable_or_obsolete()
                
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    
                    saved_count = 0
                    new_count = 0
                    updated_count = 0
                    video_activities = []  # Track activities that need video processing
                    
                    # Track if user tried to post a locked day
                    locked_day_attempt = False
                    
                    for idx, instance in enumerate(instances):
                        # Check if this is a new activity (no pk)
                        if not instance.pk:
                            # This is a new activity - check if its day is locked
                            activity_day = existing_count + 1
                            
                            if campaign.is_day_locked(activity_day):
                                locked_day_attempt = True
                                continue
                        
                        # Skip completely empty forms
                        if not instance.content and not instance.file:
                            if instance.pk:
                                original = Activity.objects.get(pk=instance.pk)
                                if (instance.content == original.content and 
                                    str(instance.file) == str(original.file)):
                                    continue
                            else:
                                continue
                            
                        # If there's a file but no content, add default content
                        if instance.file and not instance.content:
                            instance.content = f"Shared a file for Day {activity_day if not instance.pk else 'update'}"
                        
                        # ===== IMPROVED VIDEO DETECTION =====
                        if instance.file:
                            is_video = False
                            
                            # Method 1: Check if it's a Cloudinary video
                            if hasattr(instance.file, 'resource_type'):
                                is_video = instance.file.resource_type == 'video'
                                print(f"Video detection - resource_type: {instance.file.resource_type} -> {is_video}")
                            
                            # Method 2: Check content type
                            if not is_video and hasattr(instance.file, 'content_type'):
                                content_type = instance.file.content_type
                                is_video = content_type and content_type.startswith('video/')
                                print(f"Video detection - content_type: {content_type} -> {is_video}")
                            
                            # Method 3: Check URL/file name
                            if not is_video:
                                try:
                                    # Get string representation
                                    file_str = str(instance.file).lower()
                                    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v', '.mpg', '.mpeg']
                                    is_video = any(ext in file_str for ext in video_extensions)
                                    print(f"Video detection - filename: {file_str} -> {is_video}")
                                    
                                    # Check URL if available
                                    if not is_video and hasattr(instance.file, 'url'):
                                        url = instance.file.url.lower()
                                        is_video = any(ext in url for ext in video_extensions)
                                        print(f"Video detection - URL: {url} -> {is_video}")
                                except (AttributeError, TypeError):
                                    pass
                            
                            instance.is_video = is_video
                            
                            if is_video:
                                instance.video_processed = False
                                
                                # Get screenshot count from form data
                                screenshot_count_key = f'form-{idx}-screenshot_count'
                                if screenshot_count_key in request.POST:
                                    try:
                                        instance.screenshot_count = int(request.POST[screenshot_count_key])
                                    except (ValueError, TypeError):
                                        instance.screenshot_count = 5  # Default
                                print(f"Video activity detected - screenshot count: {instance.screenshot_count}")
                        
                        # Save the instance
                        instance.save()
                        saved_count += 1
                        
                        if not instance.pk:
                            new_count += 1
                            if instance.is_video:
                                video_activities.append(instance.id)
                        else:
                            updated_count += 1
                            if instance.is_video and not instance.video_processed:
                                video_activities.append(instance.id)
                    
                    # Handle deleted forms
                    deleted_count = 0
                    for form in formset.deleted_forms:
                        if form.instance.pk:
                            if hasattr(form.instance, 'video_screenshots'):
                                form.instance.video_screenshots.all().delete()
                            form.instance.delete()
                            deleted_count += 1
                    
                    # IMPORTANT: The transaction is committed here automatically
                    
                # ===== VIDEO PROCESSING (AFTER TRANSACTION COMMIT) =====
                # Use transaction.on_commit to ensure processing happens after commit
                if video_activities:
                    # Process videos in a separate connection/transaction
                    transaction.on_commit(lambda: process_videos_in_background(video_activities, request))
                    
                    # Provide immediate feedback to user
                    messages.info(request, "Video uploaded successfully. Screenshots will be created in the background and appear shortly.")
                    
                # Create appropriate messages
                if locked_day_attempt:
                    messages.warning(
                        request, 
                        f"Day {next_available_day} is locked. It will be available in {days_until_unlock} day{'s' if days_until_unlock > 1 else ''}. Your other changes were saved."
                    )
                elif saved_count > 0 or deleted_count > 0:
                    action_messages = []
                    if new_count > 0:
                        action_messages.append(f"Created Day {next_available_day - 1}")
                    if updated_count > 0:
                        action_messages.append(f"Updated {updated_count} existing day{'s' if updated_count > 1 else ''}")
                    if deleted_count > 0:
                        action_messages.append(f"Deleted {deleted_count} day{'s' if deleted_count > 1 else ''}")
                    
                    messages.success(request, ' • '.join(action_messages))
                else:
                    messages.info(request, 'No changes were made.')
                
                return redirect('activity_list', campaign_id=campaign_id)
                    
            except (InternalError, OperationalError) as e:
                if "idle-in-transaction" in str(e):
                    messages.error(request, 'Database timeout occurred. Please try again.')
                else:
                    messages.error(request, f'Database error: {str(e)}')
                print(f"Database error in create_activity: {e}")
                traceback.print_exc()
            except Exception as e:
                messages.error(request, f'Error saving activities: {str(e)}')
                print(f"Error in create_activity: {e}")
                traceback.print_exc()
        else:
            error_count = sum(len(form.errors) for form in formset)
            messages.error(request, f'Please correct the {error_count} error{"s" if error_count > 1 else ""} below.')
    else:
        formset = ActivityFormSet(
            instance=campaign,
            queryset=existing_activities
        )

    # Calculate campaign progress information
    if campaign.duration and campaign.days_left is not None:
        if campaign.duration_unit == 'days':
            total_duration = campaign.duration
            progress_percentage = (current_real_day / total_duration) * 100 if total_duration > 0 else 0
        else:
            total_duration = campaign.duration
            progress_percentage = (current_real_day / total_duration) * 100 if total_duration > 0 else 0
    else:
        progress_percentage = existing_count * 10
        if progress_percentage > 100:
            progress_percentage = 100
    
    progress_percentage = min(progress_percentage, 100)
    
    # Calculate if user is ahead/behind schedule
    if campaign.duration and campaign.days_left is not None:
        if existing_count > current_real_day:
            schedule_status = "ahead"
            schedule_diff = existing_count - current_real_day
        elif existing_count < current_real_day:
            schedule_status = "behind"
            schedule_diff = current_real_day - existing_count
        else:
            schedule_status = "on_track"
            schedule_diff = 0
    else:
        schedule_status = "ongoing"
        schedule_diff = 0

    next_day_status = campaign.get_day_status(next_available_day) if hasattr(campaign, 'get_day_status') else None

    # Emojis
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

    context = {
        'formset': formset,
        'campaign': campaign,
        'user_profile': user_profile,
        'initial_emojis': initial_emojis,
        'existing_activities_count': existing_count,
        'max_forms': MAX_FORMS,
        'is_at_max': existing_count >= MAX_FORMS,
        'next_available_day': next_available_day,
        'current_real_day': current_real_day,
        'is_next_day_locked': is_next_day_locked,
        'days_until_unlock': days_until_unlock,
        'progress_percentage': progress_percentage,
        'schedule_status': schedule_status,
        'schedule_diff': schedule_diff,
        'next_day_status': next_day_status,
        'screenshot_count_options': [3, 5, 7, 10],
        'supported_video_formats': ['mp4', 'mov', 'avi', 'webm', 'mkv'],
    }

    return render(request, 'main/activity_create.html', context)


def process_videos_in_background(activity_ids, request=None):
    """
    Helper function to process videos after transaction commit
    Uses a fresh database connection
    """
    try:
        from .tasks import process_video_screenshots
        
        # Close any existing connection and get a fresh one
        connection.close()
        
        processed_count = 0
        for activity_id in activity_ids:
            try:
                print(f"🚀 Starting video processing for activity {activity_id}")
                # Process with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        result = process_video_screenshots(activity_id)
                        print(f"✅ Video processing result: {result}")
                        
                        # Check if screenshots were actually created
                        from .models import Activity
                        activity = Activity.objects.get(id=activity_id)
                        screenshot_count = activity.screenshots.count()
                        
                        if screenshot_count > 0:
                            processed_count += 1
                            print(f"✅ Activity {activity_id} now has {screenshot_count} screenshots")
                            break
                        else:
                            if attempt < max_retries - 1:
                                print(f"⚠️ No screenshots created, retrying ({attempt + 2}/{max_retries})...")
                                time.sleep(2)
                                continue
                    except Exception as e:
                        print(f"❌ Error on attempt {attempt + 1}: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        else:
                            raise
                
            except Exception as e:
                print(f"❌ Error processing video {activity_id}: {e}")
                traceback.print_exc()
        
        print(f"✅ Background processing complete: {processed_count}/{len(activity_ids)} videos processed")
        
    except Exception as e:
        print(f"❌ Error in background video processing: {e}")
        traceback.print_exc()


@login_required
def debug_video_processing(request, activity_id):
    """Debug view to manually trigger video processing with detailed output"""
    from .models import Activity, VideoScreenshot
    from .tasks import process_video_screenshots
    import json
    import io
    import sys
    
    activity = get_object_or_404(Activity, id=activity_id)
    
    if request.user != activity.campaign.user.user:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        try:
            # Close stale connection
            connection.close_if_unusable_or_obsolete()
            
            # Capture print output
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            # Process with timeout handling
            result = process_video_screenshots(activity_id)
            
            # Get captured output
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            # Check screenshots with fresh connection
            screenshots = VideoScreenshot.objects.filter(activity=activity)
            
            return JsonResponse({
                'success': True,
                'result': result,
                'debug_output': output,
                'screenshots_count': screenshots.count(),
                'screenshots': [
                    {
                        'order': s.order,
                        'url': s.image.url if s.image else None,
                        'timestamp': s.timestamp
                    } for s in screenshots
                ]
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'activity_id': activity_id,
        'is_video': activity.is_video,
        'video_processed': activity.video_processed,
        'screenshot_count': activity.screenshots.count(),
        'file_url': activity.file.url if activity.file else None
    })


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
    

    # Fetch available categories
    categories = Campaign.objects.filter(user=user_profile).values_list('category', flat=True).distinct()

    return render(request, 'main/manage_campaigns.html', {
     
        'campaigns': all_campaigns,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
      
        'categories': categories,  # Pass categories to template
        'selected_category': category_filter,  # Retain selected category
          'suggested_users': suggested_users,
 
    })


import time


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
    return redirect('index')








def success_page(request):
    return render(request, 'main/success_page.html')


# views.py
from django.http import JsonResponse

def record_campaign_view(request, campaign_id):
    if request.method == 'POST':
        # Handle logic (e.g., increment views)
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Campaign, Love, CampaignFollow, Comment, Notification
@login_required
def journey(request, campaign_id=None):
    """Main journey feed view - displays campaigns in a reel format"""
    try:
        # Base queryset - only active campaigns
        campaigns_query = Campaign.objects.filter(is_active=True).select_related(
            'user', 'user__user'
        ).prefetch_related(
            'loves', 'followers', 'pledges', 'donations', 'comments', 'activity_set'
        )
        
        # If campaign_id is provided, filter to that specific campaign
        if campaign_id:
            campaigns_query = campaigns_query.filter(id=campaign_id)
            # If no campaign found, 404
            if not campaigns_query.exists():
                from django.http import Http404
                raise Http404("Campaign not found")
            campaigns = campaigns_query
        else:
            # ===== FOLLOWED CAMPAIGNS FIRST =====
            if request.user.is_authenticated:
                # Get IDs of campaigns this user follows
                followed_campaign_ids = list(CampaignFollow.objects.filter(
                    user=request.user
                ).values_list('campaign_id', flat=True))
                
                # Split into followed and not followed
                followed_campaigns = campaigns_query.filter(id__in=followed_campaign_ids)
                other_campaigns = campaigns_query.exclude(id__in=followed_campaign_ids).order_by('-timestamp')
                
                # Combine: followed first, then others
                campaigns = list(followed_campaigns) + list(other_campaigns)
            else:
                # For non-authenticated users, show all by timestamp
                campaigns = campaigns_query.order_by('-timestamp')
        
        campaign_data = []
        
        for campaign in campaigns:
            try:
                # ===== BASIC INFO (SAME AS YOUR WORKING VIEW) =====
                images = []
                if campaign.poster:
                    images.append(campaign.poster.url)
                
                if campaign.additional_images:
                    try:
                        if isinstance(campaign.additional_images, list):
                            images.extend(campaign.additional_images)
                        elif isinstance(campaign.additional_images, str):
                            additional = json.loads(campaign.additional_images)
                            if isinstance(additional, list):
                                images.extend(additional)
                    except:
                        pass
                
                # Audio URL
                audio_url = None
                if campaign.audio:
                    audio_url = campaign.audio.url
                else:
                    audio_url = campaign.get_default_audio()
                
                # User interaction flags
                user_loved = False
                user_following = False
                is_campaign_owner = False
                
                if request.user.is_authenticated:
                    user_loved = campaign.loves.filter(user=request.user).exists()
                    user_following = campaign.is_followed_by(request.user)
                    is_campaign_owner = request.user == campaign.user.user
                
                # Calculate totals safely
                total_pledges = campaign.pledges.aggregate(total=Sum('amount'))['total'] or 0
                total_donations = campaign.donations.filter(fulfilled=True).aggregate(total=Sum('amount'))['total'] or 0
                
                # ===== BASIC STATS (YOUR WORKING STRUCTURE) =====
                stats = {
                    'love_count': campaign.love_count,
                    'comment_count': campaign.comments.count(),
                    'follower_count': campaign.follower_count,
                    'activity_count': campaign.activity_set.count(),
                    'total_pledges': float(total_pledges),
                    'total_donations': float(total_donations),
                    'funding_goal': float(campaign.funding_goal) if campaign.funding_goal else 0,
                    'donation_percentage': campaign.donation_percentage,
                    'days_left': campaign.days_left if campaign.days_left is not None else 0,
                    'current_day': campaign.get_current_day(),
                    'total_days': campaign.duration or 30,
                    
                    # ===== PREMIUM STATS WITH SAFE DEFAULTS =====
                    'avg_donation': 0,
                    'total_donors': 0,
                    'total_pledgers': 0,
                    'new_followers_7d': 0,
                    'new_followers_30d': 0,
                    'follower_growth': 0,
                    'activity_completion': 0,
                    'engagement_score': 0,
                    'donation_conversion': 0,
                    'repeat_donors': 0,
                    'follower_chart': [],
                    'donor_demographics': {'locations': {}, 'brackets': {}, 'repeat_donors': 0},
                    'predictive': {
                        'projected_final': 0,
                        'success_probability': 'N/A',
                        'recommendations': ['Keep up the great work!'],
                        'estimated_completion_date': 'N/A'
                    },
                    'benchmarks': None,
                    'conversion_funnel': {
                        'view_to_follower': 0,
                        'follower_to_pledger': 0,
                        'pledger_to_donor': 0
                    }
                }
                
                # ===== CHECK IF USER CAN VIEW PREMIUM =====
                can_view_premium = False
                
                # Campaign owner gets premium stats automatically
                if is_campaign_owner:
                    try:
                        if campaign.premium_activated:
                            can_view_premium = True
                    except:
                        pass
                
                # ===== ONLY CALCULATE PREMIUM STATS IF NEEDED =====
                if can_view_premium:
                    try:
                        # Follower stats
                        from django.utils import timezone
                        from datetime import timedelta
                        
                        seven_days_ago = timezone.now() - timedelta(days=7)
                        thirty_days_ago = timezone.now() - timedelta(days=30)
                        
                        stats['new_followers_7d'] = campaign.campaign_follows.filter(
                            followed_at__gte=seven_days_ago
                        ).count()
                        
                        stats['new_followers_30d'] = campaign.campaign_follows.filter(
                            followed_at__gte=thirty_days_ago
                        ).count()
                        
                        if stats['follower_count'] > 0:
                            stats['follower_growth'] = round(
                                (stats['new_followers_7d'] / stats['follower_count']) * 100, 1
                            )
                        
                        # Donor stats
                        donors_qs = campaign.donations.filter(fulfilled=True)
                        stats['total_donors'] = donors_qs.values('user').distinct().count()
                        
                        donations_sum = donors_qs.aggregate(total=Sum('amount'))['total'] or 0
                        if stats['total_donors'] > 0:
                            stats['avg_donation'] = round(donations_sum / stats['total_donors'], 2)
                        
                        # Pledgers
                        stats['total_pledgers'] = campaign.pledges.values('user').distinct().count()
                        
                        # Activity completion
                        if campaign.duration and campaign.duration > 0:
                            stats['activity_completion'] = round(
                                (stats['activity_count'] / campaign.duration) * 100, 1
                            )
                        
                        # Engagement score
                        if stats['follower_count'] > 0:
                            love_ratio = stats['love_count'] / stats['follower_count']
                            comment_ratio = stats['comment_count'] / stats['follower_count']
                            stats['engagement_score'] = min(
                                round((love_ratio * 40) + (comment_ratio * 30) + 30), 100
                            )
                        
                        # Donation conversion
                        if stats['follower_count'] > 0 and stats['total_donors'] > 0:
                            stats['donation_conversion'] = round(
                                (stats['total_donors'] / stats['follower_count']) * 100, 1
                            )
                        
                    except Exception as e:
                        print(f"Error calculating premium stats for campaign {campaign.id}: {e}")
                        # Keep the default values, don't let this crash
                
                # ===== ADD ENGAGEMENT TRACKING STATS =====
                try:
                    stats['watch_time'] = getattr(campaign, 'total_watch_time', 0)
                    stats['avg_watch_time'] = getattr(campaign, 'avg_watch_time', 0)
                    stats['completion_rate'] = getattr(campaign, 'completion_rate', 0)
                    stats['save_count'] = getattr(campaign, 'save_count', 0)
                    stats['share_count'] = getattr(campaign, 'share_count', 0)
                    
                    if 'engagement_score' not in stats or stats['engagement_score'] == 0:
                        stats['engagement_score'] = getattr(campaign, 'get_engagement_score', lambda: 0)()
                except Exception as e:
                    print(f"Error adding engagement stats: {e}")
                    stats['watch_time'] = 0
                    stats['avg_watch_time'] = 0
                    stats['completion_rate'] = 0
                    stats['save_count'] = 0
                    stats['share_count'] = 0

                # ===== ADD CAMPAIGN DATA =====
                campaign_data.append({
                    'id': campaign.id,
                    'title': campaign.title,
                    'content': campaign.content,
                    'images': images[:5],
                    'audio_url': audio_url,
                    'user': {
                        'username': campaign.user.user.username,
                        'profile_image': campaign.user.image.url if campaign.user.image else None,
                        'verified': campaign.user.profile_verified,
                    },
                    'stats': stats,
                    'location': campaign.user.location or 'Unknown',
                    'timestamp': campaign.timestamp.isoformat(),
                    'time_ago': get_time_ago(campaign.timestamp),
                    'category': campaign.category,
                    'user_loved': user_loved,
                    'user_following': user_following,
                    'is_campaign_owner': is_campaign_owner,
                    'can_view_premium': can_view_premium,
                })
                
            except Exception as e:
                print(f"Error processing campaign {campaign.id}: {e}")
                continue

        # ===== JSON SERIALIZATION =====
        context = {
            'campaigns': campaign_data,
            'campaigns_json': json.dumps(campaign_data, default=str),
            'is_single_campaign': campaign_id is not None,
            'campaign_id': campaign_id,
        }
        
        return render(request, 'main/journey.html', context)
        
    except Exception as e:
        print(f"Critical error: {e}")
        return render(request, 'main/journey.html', {
            'campaigns': [],
            'campaigns_json': '[]',
            'is_single_campaign': False,
        })

# Add these to your views.py

@login_required
@require_POST
def track_watch_time(request):
    """Track watch time for a campaign"""
    try:
        data = json.loads(request.body)
        campaign_id = data.get('campaign_id')
        watch_time = data.get('watch_time', 0)  # in seconds
        completed = data.get('completed', False)
        
        campaign = get_object_or_404(Campaign, id=campaign_id)
        
        # Get or create watch time record
        watch_record, created = CampaignWatchTime.objects.get_or_create(
            user=request.user if request.user.is_authenticated else None,
            campaign=campaign,
            defaults={'watch_time_seconds': watch_time, 'completed': completed}
        )
        
        if not created:
            # Update existing record
            watch_record.watch_time_seconds = watch_time
            if completed:
                watch_record.completed = True
            watch_record.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def toggle_save_campaign(request, campaign_id):
    """Save or unsave a campaign"""
    try:
        campaign = get_object_or_404(Campaign, id=campaign_id)
        
        # Check if already saved
        saved = CampaignSave.objects.filter(user=request.user, campaign=campaign).first()
        
        if saved:
            saved.delete()
            saved_status = False
        else:
            CampaignSave.objects.create(user=request.user, campaign=campaign)
            saved_status = True
        
        return JsonResponse({
            'success': True,
            'saved': saved_status,
            'save_count': campaign.save_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def track_share(request, campaign_id):
    """Track when a campaign is shared"""
    try:
        data = json.loads(request.body)
        platform = data.get('platform', '')
        
        campaign = get_object_or_404(Campaign, id=campaign_id)
        
        CampaignShare.objects.create(
            user=request.user if request.user.is_authenticated else None,
            campaign=campaign,
            platform=platform
        )
        
        return JsonResponse({'success': True, 'share_count': campaign.share_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def get_rising_campaigns(request):
    """API endpoint for rising campaigns (high growth rate)"""
    try:
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        campaigns = Campaign.objects.filter(
            is_active=True,
            timestamp__gte=seven_days_ago
        ).annotate(
            growth_score=(
                Count('followers', filter=Q(campaign_follows__followed_at__gte=seven_days_ago)) * 3 +
                Count('loves', filter=Q(loves__timestamp__gte=seven_days_ago)) * 2 +
                Count('saves', filter=Q(saves__saved_at__gte=seven_days_ago)) * 4
            )
        ).order_by('-growth_score')[:20]
        
        # Format for response
        data = [{
            'id': c.id,
            'title': c.title,
            'follower_count': c.follower_count,
            'love_count': c.love_count,
            'save_count': c.save_count,
            'growth_score': c.growth_score
        } for c in campaigns]
        
        return JsonResponse({'success': True, 'campaigns': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def activate_premium(request, campaign_id):
    """Activate premium stats for a campaign"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        
        # Check if user is the owner
        if request.user != campaign.user.user:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        
        # Activate premium
        campaign.premium_activated = True
        campaign.save()
        
        return JsonResponse({'success': True})
        
    except Campaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaign not found'}, status=404)






from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def activate_owner_premium(request, campaign_id):
    """Activate free premium for campaign owners (temporary promotion)"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        
        # Verify the user is the campaign owner
        if request.user != campaign.user.user:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        
        # Here you would typically create a PremiumSubscription or set a flag
        # For now, we'll just return success and let the frontend reload
        
        # You could store this in session or create a temporary record
        request.session[f'premium_activated_{campaign_id}'] = True
        
        return JsonResponse({'success': True})
        
    except Campaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaign not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

@login_required
def get_campaign_comments_simple(request, campaign_id):
    """Get comments for a campaign - returns HTML directly"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    comments = campaign.comments.filter(parent_comment=None).select_related(
        'user', 'user__user'
    ).order_by('-timestamp')[:50]
    
    # Prepare comment data
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'user': {
                'username': comment.user.user.username,
                'profile_image': comment.user.image.url if comment.user.image else None,
                'verified': comment.user.profile_verified,
            },
            'text': comment.text,
            'time_ago': get_time_ago(comment.timestamp),
        })
    
    # Render HTML directly
    html = render_to_string('main/comments_partial.html', {'comments': comments_data})
    return HttpResponse(html)

@require_POST
@login_required
def add_campaign_comment_simple(request, campaign_id):
    """Add a comment - returns HTML directly"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    text = request.POST.get('text', '').strip()
    
    if text:
        Comment.objects.create(
            user=request.user.profile,
            campaign=campaign,
            text=text
        )
    
    # Return updated comments HTML
    comments = campaign.comments.filter(parent_comment=None).select_related(
        'user', 'user__user'
    ).order_by('-timestamp')[:50]
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'user': {
                'username': comment.user.user.username,
                'profile_image': comment.user.image.url if comment.user.image else None,
                'verified': comment.user.profile_verified,
            },
            'text': comment.text,
            'time_ago': get_time_ago(comment.timestamp),
        })
    
    html = render_to_string('main/comments_partial.html', {'comments': comments_data})
    return HttpResponse(html)

def get_time_ago(timestamp):
    """Helper function to get human readable time ago"""
    from django.utils import timezone
    now = timezone.now()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years}y ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months}mo ago"
    elif diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "Just now"

@require_POST
@login_required
def toggle_campaign_love(request, campaign_id):
    """Toggle love on a campaign"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    love, created = Love.objects.get_or_create(
        campaign=campaign,
        user=request.user
    )
    
    if not created:
        love.delete()
        loved = False
    else:
        loved = True
    
    return JsonResponse({
        'success': True,
        'loved': loved,
        'love_count': campaign.love_count
    })

@require_POST
@login_required
def toggle_campaign_follow(request, campaign_id):
    """Toggle follow on a campaign"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if campaign.is_followed_by(request.user):
        # Unfollow
        CampaignFollow.objects.filter(
            user=request.user,
            campaign=campaign
        ).delete()
        following = False
    else:
        # Follow
        CampaignFollow.objects.create(
            user=request.user,
            campaign=campaign
        )
        following = True
    
    return JsonResponse({
        'success': True,
        'following': following,
        'follower_count': campaign.follower_count
    })

@login_required
def get_campaign_stats(request, campaign_id):
    """Get updated stats for a campaign"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    return JsonResponse({
        'love_count': campaign.love_count,
        'comment_count': campaign.comments.count(),
        'follower_count': campaign.follower_count,
        'total_pledges': float(campaign.total_pledges),
        'total_donations': float(campaign.total_donations),
        'donation_percentage': campaign.donation_percentage,
        'days_left': campaign.days_left,
        'current_day': campaign.get_current_day(),
    })

# Add this to your views.py
def load_more_activities(request):
    """Load more activities for infinite scroll"""
    campaign_id = request.GET.get('campaign_id')
    cursor = request.GET.get('cursor')
    
    activities = Activity.objects.filter(
        campaign_id=campaign_id,
        id__lt=cursor
    ).order_by('-id')[:10]
    
    # Prepare activities data
    activities_data = []
    for activity in activities:
        activities_data.append({
            'id': activity.id,
            'content': activity.content,
            'day_number': activity.day_number,
            'file_url': activity.file.url if activity.file else None,
            'screenshots': [s.image.url for s in activity.video_screenshots.all()],
            'love_count': activity.loves.count(),
            'comment_count': activity.comments.count(),
        })
    
    return JsonResponse({
        'activities': activities_data,
        'next_cursor': activities.last().id if activities.exists() else None,
        'has_more': activities.count() == 10
    })



def face(request):
   
   
    user_profile = get_object_or_404(Profile, user=request.user)
    category_filter = request.GET.get('category', '')  # Get category filter from request

    campaign = Campaign.objects.last()

    if user_profile.last_campaign_check is None:
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()

    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
      
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,  # Pass categories to template
        'selected_category': category_filter,  # Pass selected category to retain state
    })









@login_required
def campaign_comments(request, campaign_id):
    # Retrieve campaign object
   
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

    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
       
        'campaign': campaign,
        'comments': comments,
        'form': form,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
          
       
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/campaign_comments.html', context)


def campaign_support(request, campaign_id):
    # Get basic campaign and user data
    user_profile = None

    
    if request.user.is_authenticated:
      
        user_profile = get_object_or_404(Profile, user=request.user)
        # Update last campaign check time
        user_profile.last_campaign_check = timezone.now()
        user_profile.save()

   
    # Notifications and messages
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False) if request.user.is_authenticated else []
    
    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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

    context = {
       
        'support_campaign': support_campaign,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
      
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
    }
    
    return render(request, 'main/campaign_support.html', context)






@login_required
def recreate_campaign(request, campaign_id):

    
    # ================ SECURITY CHECK ================
    # Get the campaign first to check ownership
    existing_campaign = get_object_or_404(Campaign, pk=campaign_id)
    
    # Check if user owns this campaign
    user_profile = get_object_or_404(Profile, user=request.user)
    if existing_campaign.user != user_profile:
        messages.error(request, "You don't have permission to edit this campaign.")
        return redirect('index')
    
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
            
            # =================== HANDLE IMAGE REMOVAL LOGIC ===================
            # DEFAULT BEHAVIOR: All existing images are kept unless explicitly removed
            
            # Prepare lists for images to keep
            images_to_keep = []
            
            # 1. Handle main poster
            remove_current_poster = request.POST.get('remove_current_poster') == 'on'
            new_main_poster = request.FILES.get('poster')
            
            if remove_current_poster:
                # User wants to remove current main poster
                campaign.poster = None
            elif new_main_poster:
                # User uploaded new main poster - replace existing
                try:
                    upload_result = cloudinary.uploader.upload(
                        new_main_poster,
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
                    # Keep existing poster if upload fails
                    if existing_campaign.poster and not remove_current_poster:
                        campaign.poster = existing_campaign.poster
            else:
                # User didn't check "remove" and didn't upload new - KEEP EXISTING
                campaign.poster = existing_campaign.poster
            
            # 2. Handle additional images
            # Start with ALL existing additional images
            existing_additional = []
            if hasattr(existing_campaign, 'additional_images') and existing_campaign.additional_images:
                existing_additional = list(existing_campaign.additional_images)
            
            # Check which ones to remove
            images_to_remove_indices = []
            for i in range(len(existing_additional)):
                remove_key = f'remove_existing_image_{i+1}'
                if request.POST.get(remove_key) == 'on':
                    images_to_remove_indices.append(i)
            
            # Also check "remove all additional" checkbox
            remove_all_additional = request.POST.get('remove_all_additional') == 'on'
            
            if remove_all_additional:
                # Remove all additional images
                images_to_keep = []
            else:
                # Keep all except those marked for removal
                images_to_keep = [
                    img for idx, img in enumerate(existing_additional)
                    if idx not in images_to_remove_indices
                ]
            
            # 3. Add NEW additional images uploaded by user
            new_additional_images = request.FILES.getlist('additional_images')
            new_image_urls = []
            
            for idx, image in enumerate(new_additional_images[:4]):  # Limit to 4 new
                if image:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            image,
                            folder="campaign_files/slideshow",
                            public_id=f"{campaign.id}_{len(images_to_keep)+idx}_{int(time.time())}",
                            transformation=[
                                {'width': 1200, 'crop': 'limit'},
                                {'quality': 'auto'},
                                {'format': 'auto'}
                            ]
                        )
                        new_image_urls.append(upload_result['secure_url'])
                    except Exception as e:
                        print(f"Error uploading additional image: {e}")
            
            # Combine kept existing images with new ones (max 4 total)
            all_images = images_to_keep + new_image_urls
            campaign.additional_images = all_images[:4]
            
            # 4. Fallback: If no main poster but we have additional images
            # Use first additional image as main poster
            if not campaign.poster and campaign.additional_images:
                campaign.poster = campaign.additional_images[0]
                campaign.additional_images = campaign.additional_images[1:4]  # Keep next 3
            
            # 5. Handle audio
            remove_current_audio = request.POST.get('remove_current_audio') == 'on'
            new_audio = request.FILES.get('audio')
            
            if remove_current_audio:
                # User wants to remove current audio
                campaign.audio = None
            elif new_audio:
                # User uploaded new audio - replace existing
                try:
                    # Upload to Cloudinary
                    audio_upload_result = cloudinary.uploader.upload(
                        new_audio,
                        resource_type='auto',
                        folder="campaign_files/audio",
                        allowed_formats=['mp3', 'wav', 'ogg', 'm4a', 'mp4', 'aac']
                    )
                    campaign.audio = audio_upload_result['secure_url']
                except Exception as e:
                    print(f"Error uploading audio: {e}")
                    # Keep existing audio if upload fails
                    if existing_campaign.audio and not remove_current_audio:
                        campaign.audio = existing_campaign.audio
            else:
                # No new audio and no removal requested - KEEP EXISTING
                campaign.audio = existing_campaign.audio
            
            # =================== SAVE CAMPAIGN ===================
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
            print(f"DEBUG - Form errors: {form.errors}")
            messages.error(request, 'There were errors in your form. Please correct them below.')
    else:
        form = CampaignForm(instance=existing_campaign)
        # Pre-populate tags input with existing tags
        existing_tags = ', '.join([tag.name for tag in existing_campaign.tags.all()])
        form.fields['tags_input'].initial = existing_tags

    # Trending campaigns
    from django.db.models import Count
    from itertools import chain
    from collections import defaultdict
    
    trending_campaigns = Campaign.objects.filter() \
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
   
    # Prepare existing images data for template
    existing_images = []
    if existing_campaign.poster:
        poster_url = existing_campaign.poster.url if hasattr(existing_campaign.poster, 'url') else existing_campaign.poster
        existing_images.append({
            'url': poster_url,
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
    
    # Convert to JSON for JavaScript
    import json
    existing_images_json = json.dumps(existing_images)
    
    # Check if campaign has audio
    has_audio = bool(existing_campaign.audio)

    context = {
     
        'form': form,
        'categories': categories,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
   
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'existing_campaign': existing_campaign,
        'existing_images': existing_images,
        'existing_images_json': existing_images_json,
        'has_additional_images': hasattr(existing_campaign, 'additional_images') and 
                                existing_campaign.additional_images and 
                                len(existing_campaign.additional_images) > 0,
        'has_audio': has_audio
    }
    
    return render(request, 'main/recreatecampaign_form.html', context)









def success_page(request):
    return render(request, 'main/success.html')


@login_required
def create_campaign(request):

    user_profile = get_object_or_404(Profile, user=request.user)
    categories = Campaign.CATEGORY_CHOICES

    if request.method == "POST":
        form = CampaignForm(request.POST, request.FILES)

        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user.profile
            campaign.audio = None

            # SAVE FIRST (IMPORTANT: generates campaign.id)
            campaign.save()

            # -----------------------------
            # Canva Poster
            # -----------------------------
            canva_poster_data = request.POST.get("canva_poster_data")

            if canva_poster_data:
                try:
                    canva_data = json.loads(canva_poster_data)
                    response = requests.get(canva_data["previewUrl"])

                    if response.status_code == 200:
                        upload_result = cloudinary.uploader.upload(
                            response.content,
                            folder="campaign_files",
                            public_id=f"campaign_{campaign.id}_canva_{int(time.time())}",
                        )
                        campaign.poster = upload_result["secure_url"]

                except Exception as e:
                    print("Canva poster error:", e)

            # -----------------------------
            # Main Poster Upload
            # -----------------------------
            main_poster = request.FILES.get("poster")

            if main_poster:
                try:
                    upload_result = cloudinary.uploader.upload(
                        main_poster,
                        folder="campaign_files",
                        public_id=f"campaign_{campaign.id}_poster",
                        transformation=[
                            {"width": 1200, "crop": "limit"},
                            {"quality": "auto"},
                            {"format": "auto"},
                        ],
                    )

                    campaign.poster = upload_result["secure_url"]

                except Exception as e:
                    print("Poster upload error:", e)

            # -----------------------------
            # Additional Images
            # -----------------------------
            additional_images = request.FILES.getlist("additional_images")
            additional_image_urls = []

            for idx, image in enumerate(additional_images[:4]):
                try:
                    upload_result = cloudinary.uploader.upload(
                        image,
                        folder="campaign_files/slideshow",
                        public_id=f"campaign_{campaign.id}_img_{idx}_{int(time.time())}",
                        transformation=[
                            {"width": 1200, "crop": "limit"},
                            {"quality": "auto"},
                            {"format": "auto"},
                        ],
                    )

                    additional_image_urls.append(upload_result["secure_url"])

                except Exception as e:
                    print("Additional image upload error:", e)

            if additional_image_urls:
                campaign.additional_images = additional_image_urls

                if not campaign.poster:
                    campaign.poster = additional_image_urls[0]
                    campaign.additional_images = additional_image_urls[1:]

            # -----------------------------
            # Audio Upload
            # -----------------------------
            audio_file = request.FILES.get("audio")

            if audio_file:
                try:
                    if audio_file.size > 10 * 1024 * 1024:
                        messages.error(request, "Audio must be under 10MB")
                        campaign.delete()
                        return redirect("create_campaign")

                    allowed_extensions = [
                        ".mp3",
                        ".wav",
                        ".ogg",
                        ".m4a",
                        ".aac",
                        ".flac",
                    ]

                    if not any(audio_file.name.lower().endswith(ext) for ext in allowed_extensions):
                        messages.error(request, "Invalid audio format")
                        campaign.delete()
                        return redirect("create_campaign")

                    upload_result = cloudinary.uploader.upload(
                        audio_file,
                        resource_type="video",
                        folder="campaign_audio",
                        public_id=f"campaign_{campaign.id}_audio_{int(time.time())}",
                    )

                    campaign.audio = upload_result["secure_url"]

                except Exception as e:
                    print("Audio upload error:", e)
                    messages.warning(
                        request,
                        "Campaign created but audio upload failed. You can add it later.",
                    )

            # -----------------------------
            # Tags
            # -----------------------------
            tags_input = form.cleaned_data.get("tags_input", "")

            if tags_input:
                campaign.tags.clear()

                tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]

                for tag_name in tag_names:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name.lower(),
                        defaults={"slug": tag_name.lower().replace(" ", "-")},
                    )
                    campaign.tags.add(tag)

            # -----------------------------
            # Save Campaign Updates
            # -----------------------------
            campaign.save()

            # -----------------------------
            # Update Profile
            # -----------------------------
            user_profile.last_campaign_check = timezone.now()
            user_profile.save()

            messages.success(request, "Campaign created successfully!")

            return redirect("index")

        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = CampaignForm()

    # -----------------------------
    # Notifications
    # -----------------------------
    unread_notifications = Notification.objects.filter(
        user=request.user, viewed=False
    )

    # -----------------------------
    # Trending Campaigns
    # -----------------------------
    trending_campaigns = (
        Campaign.objects.annotate(love_count_annotated=Count("loves"))
        .filter(love_count_annotated__gte=1)
        .order_by("-love_count_annotated")[:10]
    )

    # -----------------------------
    # Top Contributors
    # -----------------------------
    from itertools import chain
    from collections import defaultdict

    love_pairs = Love.objects.values_list("user_id", "campaign_id")
    comment_pairs = Comment.objects.values_list("user_id", "campaign_id")
    view_pairs = CampaignView.objects.values_list("user_id", "campaign_id")
    activity_love_pairs = ActivityLove.objects.values_list(
        "user_id", "activity__campaign_id"
    )
    activity_comment_pairs = ActivityComment.objects.values_list(
        "user_id", "activity__campaign_id"
    )

    all_pairs = chain(
        love_pairs,
        comment_pairs,
        view_pairs,
        activity_love_pairs,
        activity_comment_pairs,
    )

    user_campaign_map = defaultdict(set)

    for user_id, campaign_id in all_pairs:
        user_campaign_map[user_id].add(campaign_id)

    contributor_data = []

    for user_id, campaign_set in user_campaign_map.items():
        try:
            profile = Profile.objects.get(user__id=user_id)

            contributor_data.append(
                {
                    "user": profile.user,
                    "image": profile.image,
                    "campaign_count": len(campaign_set),
                }
            )
        except Profile.DoesNotExist:
            pass

    top_contributors = sorted(
        contributor_data,
        key=lambda x: x["campaign_count"],
        reverse=True,
    )[:5]

    context = {
        "form": form,
        "categories": categories,
        "user_profile": user_profile,
        "unread_notifications": unread_notifications,
        "trending_campaigns": trending_campaigns,
        "top_contributors": top_contributors,
    }

    return render(request, "main/campaign_form.html", context)


def poster_canva(request):
    return render(request, 'main/poster_canva.html', {
        'username': request.user.username
    })



def video_canva(request):
    return render(request, 'main/video_canva.html', {
        'username': request.user.username
    })




@login_required
def face(request):
 
   
    category_filter = request.GET.get('category', '')  # Get category filter from request

    campaign = Campaign.objects.last()
    user_profile = None

    if request.user.is_authenticated:
        user_profile = get_object_or_404(Profile, user=request.user)

        if user_profile.last_campaign_check is None:
            user_profile.last_campaign_check = timezone.now()
            user_profile.save()


    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)

    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
      
        'suggested_users': suggested_users,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,  # Pass categories to template
        'selected_category': category_filter,  # Pass selected category to retain state
    })


def project_support(request):
    """
    Project support page view
    """
    return render(request, 'main/project_support.html', {
       
        # Add any other context data needed by your template
    })











@login_required
def profile_edit(request, username):
   
    category_filter = request.GET.get('category', '')  # Get category filter from request
    unread_notifications = Notification.objects.filter(user=request.user, viewed=False)
    user_profile = get_object_or_404(Profile, user=request.user)
    user = get_object_or_404(User, username=username)
    profile, created = Profile.objects.get_or_create(user=user)
    
    # Update last_campaign_check for the user's profile
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()
    
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('index')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
   
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'username': username,
        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
    
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        'categories': categories,
        'selected_category': category_filter,
    }
    
    return render(request, 'main/edit_profile.html', context)


@login_required
def profile_view(request, username):
    # Get the User object
    user_obj = get_object_or_404(User, username=username)
    
    # Get the user's profile
    user_profile = get_object_or_404(Profile, user=user_obj)
    
    # ===== FIXED: Get ALL campaigns (no public/private filter) =====
    user_campaigns = user_profile.user_campaigns.filter(is_active=True).order_by('-timestamp')
    user_campaigns_count = user_campaigns.count()
    
    # ===== COMPLETED JOURNEYS (for Store Manager) =====
    from django.utils import timezone
    
    completed_journeys = []
    for campaign in user_campaigns:
        # Check if journey is completed
        is_completed = False
        if campaign.end_date and timezone.now().date() > campaign.end_date.date():
            is_completed = True
        elif campaign.duration and campaign.activity_set.count() >= campaign.duration:
            is_completed = True
            
        if is_completed:
            # Get activity count
            activity_count = campaign.activity_set.count()
            
            # Mock products for now (you'll replace with real Product model later)
            products = []
            # Example products - remove when you have real data
            if campaign.id % 3 == 0:  # Just for demo
                products = [
                    {'id': 1, 'type': 'blueprint', 'name': 'The Blueprint', 'price': 9.99, 'sold': 12},
                    {'id': 2, 'type': 'video', 'name': 'Behind the Scenes', 'price': 19.99, 'sold': 8},
                ]
            
            completed_journeys.append({
                'id': campaign.id,
                'title': campaign.title,
                'end_date': campaign.end_date or campaign.timestamp,
                'follower_count': campaign.follower_count,
                'activity_count': activity_count,
                'products': products,
            })
    
    completed_journeys_count = len(completed_journeys)
    
    # ===== EARNINGS DATA (mock for now) =====
    total_revenue = 1240.50
    your_earnings = total_revenue * 0.7  # 70%
    total_sales = 45
    
    recent_sales = [
        {'product_name': 'The Blueprint', 'journey_title': '30 Days to Fitness', 'amount': 9.99, 'date': timezone.now() - timedelta(hours=2)},
        {'product_name': 'Behind the Scenes', 'journey_title': 'Learn Python', 'amount': 19.99, 'date': timezone.now() - timedelta(days=1)},
        {'product_name': 'Coaching Session', 'journey_title': '30 Days to Fitness', 'amount': 49.99, 'date': timezone.now() - timedelta(days=2)},
    ]
    
    # Rest of your code remains the same...
    changemaker_campaigns = [campaign for campaign in user_campaigns if campaign.is_changemaker]
    
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
    
    # 🔥 Trending campaigns
    trending_campaigns = Campaign.objects.filter(is_active=True) \
        .annotate(love_count_annotated=Count('loves')) \
        .filter(love_count_annotated__gte=1) \
        .order_by('-love_count_annotated')[:10]

    # Top Contributors logic
    from itertools import chain
    from collections import defaultdict
    
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

    context = {
        'user_profile': user_profile,
        'user_obj': user_obj,
        'user_campaigns': user_campaigns,  # FIXED: renamed from public_campaigns
        'user_campaigns_count': user_campaigns_count,  # FIXED: renamed
        'changemaker_category': category_display,
        'unread_notifications': unread_notifications,
        'trending_campaigns': trending_campaigns,
        'top_contributors': top_contributors,
        # NEW: Store Manager data
        'completed_journeys': completed_journeys,
        'completed_journeys_count': completed_journeys_count,
        'total_revenue': total_revenue,
        'your_earnings': your_earnings,
        'total_sales': total_sales,
        'recent_sales': recent_sales,
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

    # Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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

    # Trending campaigns (with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
    trending_campaigns = Campaign.objects.filter() \
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
   

    context = {
      
        'form': form,
        'product': product,
        'campaign': campaign,
        'products': products,
        'product_count': product_count,
        'unread_notifications': unread_notifications,
        'user_profile': user_profile,
     
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
    
    user_profile = get_object_or_404(Profile, user=request.user)

    # 🔥 Trending campaigns (Only those with at least 1 love)
    trending_campaigns = Campaign.objects.filter() \
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
   
    user_profile.last_campaign_check = timezone.now()
    user_profile.save()

    

    context = {
    
        'cart': cart,
        'cart_items': cart_items,
        'unread_notifications': unread_notifications,
        'user_profile': user_profile,
      
       
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