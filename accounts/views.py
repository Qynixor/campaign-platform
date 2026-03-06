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


def index(request):
    """
    Homepage view (clean + safe version)
    """

    # Ensure database connection
    try:
        connection.close_if_unusable_or_obsolete()
        connection.ensure_connection()
    except:
        pass

    user_profile = None
    unread_notifications = []
    unread_messages_count = 0
    show_login_button = not request.user.is_authenticated

    category_filter = request.GET.get('category', '')

    # -------------------------
    # AUTHENTICATED USER DATA
    # -------------------------

    if request.user.is_authenticated:
        try:
            with transaction.atomic():
                user_profile = get_object_or_404(Profile, user=request.user)

                user_profile.last_campaign_check = timezone.now()
                user_profile.save()

                unread_notifications = list(
                    Notification.objects.filter(
                        user=request.user,
                        viewed=False
                    )
                )

        except OperationalError as e:
            print(f"Database error in authenticated section: {e}")

    # -------------------------
    # CAMPAIGNS
    # -------------------------

    campaigns = []
    trending_campaigns = []

    try:

        connection.close_if_unusable_or_obsolete()

        for attempt in range(3):
            try:

                campaigns_query = Campaign.objects.all()

                if category_filter:
                    campaigns_query = campaigns_query.filter(
                        category=category_filter
                    )

                campaigns = list(

                    campaigns_query
                    .select_related('user')
                    .prefetch_related('tags')
                    .annotate(love_count_annotated=Count('loves'))
                    .filter(love_count_annotated__gte=1)
                    .order_by('-love_count_annotated')[:50]

                )

                break

            except OperationalError:

                if attempt < 2:
                    print(f"Retrying campaigns query {attempt+2}/3")
                    connection.close()
                    time.sleep(1)
                else:
                    raise

        # -------------------------
        # TRENDING CAMPAIGNS
        # -------------------------

        for attempt in range(3):
            try:

                trending_query = Campaign.objects.annotate(
                    love_count_annotated=Count('loves')
                ).filter(
                    love_count_annotated__gte=1
                )

                if category_filter:
                    trending_query = trending_query.filter(
                        category=category_filter
                    )

                trending_campaigns = list(
                    trending_query.order_by('-love_count_annotated')[:10]
                )

                break

            except OperationalError:

                if attempt < 2:
                    print(f"Retrying trending query {attempt+2}/3")
                    connection.close()
                    time.sleep(1)
                else:
                    raise

    except OperationalError as e:

        print(f"Database error loading campaigns: {e}")

        context = {
            'campaigns': [],
            'trending_campaigns': [],
            'user_profile': user_profile,
            'unread_notifications': unread_notifications,
            'unread_messages_count': unread_messages_count,
            'show_login_button': show_login_button,
            'selected_category': category_filter,
            'top_contributors': [],
            'campaign_tags_json': "{}",
            'error_message': "Temporary connection issue. Please refresh."
        }

        return render(request, 'accounts/index.html', context)

    # -------------------------
    # TOP CONTRIBUTORS
    # -------------------------

    top_contributors = []

    try:

        contributor_data = (
            Profile.objects
            .annotate(
                campaign_count=Count('user__love')
            )
            .order_by('-campaign_count')[:5]
        )

        top_contributors = contributor_data

    except Exception as e:
        print(f"Contributor error: {e}")

    # -------------------------
    # CAMPAIGN TAGS JSON
    # -------------------------

    campaign_tags_dict = {}

    for camp in campaigns:

        try:
            campaign_tags_dict[str(camp.id)] = list(
                camp.tags.values_list('name', flat=True)
            )
        except:
            campaign_tags_dict[str(camp.id)] = []

    campaign_tags_json = json.dumps(campaign_tags_dict)

    # -------------------------
    # CONTEXT
    # -------------------------

    context = {

        'campaigns': campaigns,
        'trending_campaigns': trending_campaigns,

        'campaign_tags_json': campaign_tags_json,

        'user_profile': user_profile,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_messages_count,

        'show_login_button': show_login_button,

        'selected_category': category_filter,

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
