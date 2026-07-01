from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.urls import reverse
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify
import json
import requests
import re
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import (
    Profile, SocialConnection, ImportedContent,
    Journey, Activity, JourneyFollow, Tag, JourneyTag,
    ActivityLove, ActivityComment, JourneySave, Share,
    Notification, Report, FAQ, ContactMessage, Subscriber,
    SocialPostTemplate, ReferralTracking, QuickAddTracker
)
from .forms import (
    SignUpForm, LoginForm, ProfileForm,
    JourneyForm, JourneySettingsForm, ActivityForm, QuickImportForm,
    SocialConnectForm, SocialSettingsForm, SocialPostTemplateForm,
    CommentForm, JourneySearchForm,
    ReportForm
)

User = get_user_model()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_or_create_session_key(request):
    """Get or create session key for anonymous users"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_user_profile(user):
    """Get or create user profile"""
    try:
        return user.profile
    except Profile.DoesNotExist:
        return Profile.objects.create(user=user)


def track_journey_view(request, journey):
    """Track journey view for analytics"""
    session_key = get_or_create_session_key(request)
    
    # Update view counts
    journey.view_count += 1
    journey.save(update_fields=['view_count'])
    
    # Track unique viewers (simplified - use cache for production)
    cache_key = f'journey_view_{journey.id}_{session_key}'
    if not cache.get(cache_key):
        journey.unique_viewers += 1
        journey.save(update_fields=['unique_viewers'])
        cache.set(cache_key, True, 3600)  # 1 hour


def parse_day_from_caption(caption):
    """Extract day number from caption text"""
    patterns = [
        r'[Dd]ay\s*(\d+)',
        r'#Day(\d+)',
        r'Journey\s*Day\s*(\d+)',
        r'Update\s*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption)
        if match:
            day = int(match.group(1))
            if 1 <= day <= 365:
                return day
    return None


def detect_platform_from_url(url):
    """Detect social platform from URL"""
    if not url:
        return None
    url = url.lower()
    if 'tiktok.com' in url:
        return 'tiktok'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'facebook.com' in url or 'fb.com' in url:
        return 'facebook'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'linkedin.com' in url:
        return 'linkedin'
    return None


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def signup_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Rallynex, {user.username}!')
            
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'auth/signup.html', {
        'form': form,
        'next_url': next_url
    })


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)
            
            messages.success(request, f'Welcome back, {user.username}!')
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('landing')


# ============================================================================
# PUBLIC VIEWS
# ============================================================================

def landing_view(request):
    """Landing page with dynamic journeys from database"""
    featured_journeys = Journey.objects.filter(
        is_public=True,
        is_active=True,
        is_featured=True
    ).select_related('creator__user').prefetch_related('activities', 'followers')[:6]
    
    trending_journeys = Journey.objects.filter(
        is_public=True,
        is_active=True
    ).order_by('-view_count')[:6]
    
    context = {
        'featured_journeys': featured_journeys,
        'trending_journeys': trending_journeys,
    }
    
    # ========== ADD USER-SPECIFIC DATA FOR LOGGED-IN USERS ==========
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            user_journeys = Journey.objects.filter(creator=profile, is_active=True)
            
            context.update({
                'user_journeys': user_journeys[:3],
                'user_journey_count': user_journeys.count(),
                'user_completed_journeys': user_journeys.filter(is_completed=True).count() if hasattr(Journey, 'is_completed') else 0,
                'user_following': JourneyFollow.objects.filter(user=request.user).count(),
                'user_notifications': Notification.objects.filter(user=request.user, viewed=False).count(),
            })
        except Profile.DoesNotExist:
            context.update({
                'user_journeys': [],
                'user_journey_count': 0,
                'user_completed_journeys': 0,
                'user_following': 0,
                'user_notifications': 0,
            })
    
    return render(request, 'landing.html', context)


def discover_view(request):
    """Browse and discover journeys"""
    form = JourneySearchForm(request.GET)
    journeys = Journey.objects.filter(is_public=True, is_active=True)
    
    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            journeys = journeys.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(creator__user__username__icontains=q)
            )
        
        category = form.cleaned_data.get('category')
        if category:
            journeys = journeys.filter(category=category)
        
        journey_type = form.cleaned_data.get('journey_type')
        if journey_type:
            journeys = journeys.filter(journey_type=journey_type)
        
        sort = form.cleaned_data.get('sort')
        allowed_sorts = ['-created_at', 'created_at', '-view_count', 'view_count', 'title', '-title']
        if sort and sort in allowed_sorts:
            journeys = journeys.order_by(sort)
        else:
            journeys = journeys.order_by('-created_at')
    else:
        journeys = journeys.order_by('-created_at')
    
    total_count = journeys.count()
    
    paginator = Paginator(journeys, 10)
    page = request.GET.get('page')
    
    try:
        journeys_page = paginator.page(page)
    except PageNotAnInteger:
        journeys_page = paginator.page(1)
    except EmptyPage:
        journeys_page = paginator.page(paginator.num_pages)
    
    context = {
        'form': form,
        'journeys': journeys_page,
        'categories': Journey.CATEGORY_CHOICES,
        'total_count': total_count,
    }
    
    return render(request, 'discover.html', context)


def journey_detail_view(request, slug):
    """View a single journey"""
    journey_qs = Journey.objects.select_related('creator__user').prefetch_related(
        'activities', 'tags', 'followers'
    ).filter(
        slug=slug,
        is_active=True
    )
    
    journey = get_object_or_404(journey_qs)
    
    if not journey.is_public:
        if not request.user.is_authenticated or (
            request.user != journey.creator.user and not request.user.is_superuser
        ):
            raise Http404("Journey not found")
    
    track_journey_view(request, journey)
    
    activities_by_day = journey.get_all_activities_by_day()
    current_day = journey.get_current_day()
    current_activity = activities_by_day.get(current_day)
    
    is_following = False
    if request.user.is_authenticated:
        is_following = JourneyFollow.objects.filter(
            user=request.user,
            journey=journey
        ).exists()
    
    is_saved = False
    if request.user.is_authenticated:
        is_saved = JourneySave.objects.filter(
            user=request.user,
            journey=journey
        ).exists()
    
    recent_comments = ActivityComment.objects.filter(
        activity__journey=journey
    ).select_related('user', 'activity').order_by('-created_at')[:10]
    
    related_journeys = Journey.objects.filter(
        category=journey.category,
        is_public=True,
        is_active=True
    ).exclude(id=journey.id).order_by('-view_count')[:4]
    
    context = {
        'journey': journey,
        'activities_by_day': activities_by_day,
        'current_day': current_day,
        'current_activity': current_activity,
        'is_following': is_following,
        'is_saved': is_saved,
        'recent_comments': recent_comments,
        'related_journeys': related_journeys,
        'total_days_range': range(1, journey.duration + 1),
        'social_share_text': journey.get_social_share_text(),
        'share_url': journey.get_share_url(),
    }
    
    return render(request, 'journey/detail.html', context)


def creator_profile_view(request, username):
    """View a creator's profile and their journeys"""
    profile = get_object_or_404(
        Profile.objects.select_related('user'),
        user__username=username
    )
    
    journeys = Journey.objects.filter(
        creator=profile,
        is_public=True,
        is_active=True
    ).order_by('-created_at')
    
    paginator = Paginator(journeys, 9)
    page = request.GET.get('page')
    
    try:
        journeys_page = paginator.page(page)
    except PageNotAnInteger:
        journeys_page = paginator.page(1)
    except EmptyPage:
        journeys_page = paginator.page(paginator.num_pages)
    
    context = {
        'profile': profile,
        'journeys': journeys_page,
    }
    
    return render(request, 'creator/profile.html', context)


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def dashboard_view(request):
    """Creator dashboard home"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    total_journeys = journeys.count()
    active_journeys = journeys.filter(is_active=True).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    recent_activities = Activity.objects.filter(
        journey__creator=profile
    ).select_related('journey').order_by('-created_at')[:10]
    
    recent_comments = ActivityComment.objects.filter(
        activity__journey__creator=profile
    ).select_related('user', 'activity__journey').order_by('-created_at')[:5]
    
    pending_imports = ImportedContent.objects.filter(
        social_connection__user=request.user,
        status='pending'
    ).count()
    
    # NEW: Social stats
    social_connections = SocialConnection.objects.filter(user=request.user)
    total_social_posts = ImportedContent.objects.filter(
        social_connection__user=request.user
    ).count()
    
    context = {
        'profile': profile,
        'journeys': journeys[:5],
        'total_journeys': total_journeys,
        'active_journeys': active_journeys,
        'total_views': total_views,
        'total_followers': total_followers,
        'recent_activities': recent_activities,
        'recent_comments': recent_comments,
        'pending_imports': pending_imports,
        'social_connections': social_connections,
        'total_social_posts': total_social_posts,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def my_journeys_view(request):
    """List all user's journeys"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    active_count = journeys.filter(is_active=True).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    for journey in journeys:
        journey.activity_count = journey.activities.count()
        journey.follower_count = journey.get_follower_count()
    
    context = {
        'journeys': journeys,
        'active_count': active_count,
        'total_views': total_views,
        'total_followers': total_followers,
    }
    
    return render(request, 'dashboard/journeys.html', context)


# ============================================================================
# JOURNEY CREATION & EDITING
# ============================================================================

@login_required
def create_journey_view(request):
    """Create a new journey"""
    profile = get_user_profile(request.user)
    
    if request.method == 'POST':
        form = JourneyForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                journey = form.save(commit=False)
                journey.creator = profile
                
                cover_image_url = request.POST.get('cover_image_url')
                cover_image_public_id = request.POST.get('cover_image_public_id')
                
                if cover_image_url and cover_image_public_id:
                    journey.cover_image = cover_image_public_id
                
                journey.save()
                
                # Save tags
                tags_input = form.cleaned_data.get('tags_input', '')
                if tags_input:
                    tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                    for tag_name in tag_names[:10]:
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        journey.tags.add(tag)
                
                messages.success(request, f'Journey "{journey.title}" created successfully!')
                return redirect('journey_content', slug=journey.slug)
                
            except Exception as e:
                messages.error(request, f'Error creating journey: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    else:
        form = JourneyForm()
    
    context = {
        'form': form,
        'is_editing': False,
        'CLOUDINARY_CLOUD_NAME': settings.CLOUDINARY_CLOUD_NAME,
        'social_connections': SocialConnection.objects.filter(user=request.user),
    }
    
    return render(request, 'dashboard/journey_form.html', context)


@login_required
def edit_journey_view(request, slug):
    """Edit an existing journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        form = JourneyForm(request.POST, request.FILES, instance=journey)
        if form.is_valid():
            journey = form.save(commit=False)
            
            cover_image_url = request.POST.get('cover_image_url')
            cover_image_public_id = request.POST.get('cover_image_public_id')
            
            if cover_image_url and cover_image_public_id:
                journey.cover_image = cover_image_public_id
            
            journey.save()
            form.save()
            
            messages.success(request, f'Journey "{journey.title}" updated!')
            return redirect('my_journeys')
    else:
        form = JourneyForm(instance=journey)
    
    context = {
        'form': form,
        'journey': journey,
        'is_editing': True,
        'CLOUDINARY_CLOUD_NAME': settings.CLOUDINARY_CLOUD_NAME,
        'social_connections': SocialConnection.objects.filter(user=request.user),
    }
    
    return render(request, 'dashboard/journey_form.html', context)


@login_required
def journey_settings_view(request, slug):
    """Quick settings for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        journey.is_public = request.POST.get('is_public') == 'on'
        journey.allow_comments = request.POST.get('allow_comments') == 'on'
        journey.auto_import_enabled = request.POST.get('auto_import_enabled') == 'on'
        journey.import_hashtag = request.POST.get('import_hashtag', '')
        journey.social_share_url = request.POST.get('social_share_url', '')
        journey.social_share_text = request.POST.get('social_share_text', '')
        journey.auto_post_to_social = request.POST.get('auto_post_to_social') == 'on'
        journey.save()
        
        messages.success(request, 'Settings updated!')
        return redirect('my_journeys')
    
    context = {
        'journey': journey,
    }
    
    return render(request, 'dashboard/journey_settings.html', context)


@login_required
def delete_journey_view(request, slug):
    """Delete a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        title = journey.title
        journey.delete()
        messages.success(request, f'Journey "{title}" deleted.')
        return redirect('my_journeys')
    
    return render(request, 'dashboard/journey_confirm_delete.html', {
        'journey': journey,
    })


# ============================================================================
# ACTIVITY / CONTENT VIEWS
# ============================================================================

@login_required
def journey_content_view(request, slug):
    """Manage content for a journey (day by day)"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    activities = journey.get_all_activities_by_day()
    current_day = journey.get_current_day()
    
    # ===== SOCIAL-FIRST: Context =====
    imported_count = 0
    manual_count = 0
    platform_counts = {}
    
    for activity in activities.values():
        if activity and activity.imported_from:
            imported_count += 1
            platform = activity.source_platform
            if platform:
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
        elif activity:
            manual_count += 1
    
    context = {
        'journey': journey,
        'activities': activities,
        'current_day': current_day,
        'day_range': range(1, journey.duration + 1),
        'imported_count': imported_count,
        'manual_count': manual_count,
        'platform_counts': platform_counts,
    }
    
    return render(request, 'dashboard/content_manager.html', context)


@login_required
def post_activity_view(request, slug, day_number=None):
    """Post or edit an activity for a specific day"""
    journey = get_object_or_404(Journey, slug=slug, creator__user=request.user)
    
    if day_number is None:
        day_number = journey.get_current_day()
    
    existing_activity = journey.get_activity_for_day(day_number)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        file_url = request.POST.get('file_url')
        is_video = request.POST.get('is_video') == 'true'
        actual_date = request.POST.get('actual_date')
        source_url = request.POST.get('source_url', '')
        source_platform = request.POST.get('source_platform', '')
        embed_html = request.POST.get('embed_html', '')
        social_post_id = request.POST.get('social_post_id', '')
        social_likes = request.POST.get('social_likes', 0)
        social_comments = request.POST.get('social_comments', 0)
        day = request.POST.get('day_number_field') or day_number
        
        if content:
            # Build social engagement dict
            social_engagement = {}
            if social_likes or social_comments:
                social_engagement = {
                    'likes': int(social_likes) if social_likes else 0,
                    'comments': int(social_comments) if social_comments else 0,
                }
            
            activity, created = Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day or day_number,
                defaults={
                    'content': content,
                    'file': file_url if file_url else None,
                    'is_video': is_video,
                    'actual_date': actual_date if actual_date else None,
                    'source_url': source_url,
                    'source_platform': source_platform,
                    'embed_html': embed_html,
                    'social_post_id': social_post_id,
                    'social_engagement': social_engagement,
                }
            )
            
            if created:
                messages.success(request, '✅ Activity posted!')
            else:
                messages.success(request, '✅ Activity updated!')
            
            return redirect('journey_content', slug=slug)
        else:
            messages.error(request, 'Please provide content for your update.')
    
    context = {
        'journey': journey,
        'day_number': day_number,
        'existing_activity': existing_activity,
        'form': ActivityForm(initial={'day_number_field': day_number}),
        'CLOUDINARY_CLOUD_NAME': settings.CLOUDINARY_CLOUD_NAME,
    }
    
    return render(request, 'dashboard/post_activity.html', context)


@login_required
def delete_activity_view(request, activity_id):
    """Delete an activity"""
    activity = get_object_or_404(
        Activity.objects.select_related('journey'),
        id=activity_id,
        journey__creator__user=request.user
    )
    
    journey_slug = activity.journey.slug
    day_number = activity.day_number_field
    
    if request.method == 'POST':
        activity.delete()
        messages.success(request, f'Day {day_number} content deleted.')
    
    return redirect('journey_content', slug=journey_slug)


# ============================================================================
# SOCIAL IMPORT VIEWS - CRITICAL FOR SOCIAL-FIRST
# ============================================================================

@login_required
def social_connections_view(request):
    """Manage social connections"""
    connections = SocialConnection.objects.filter(user=request.user)
    
    # Get import stats
    total_imported = ImportedContent.objects.filter(
        social_connection__user=request.user
    ).count()
    
    pending_imports = ImportedContent.objects.filter(
        social_connection__user=request.user,
        status='pending'
    ).count()
    
    context = {
        'connections': connections,
        'total_imported': total_imported,
        'pending_imports': pending_imports,
        'platforms': SocialConnection.PLATFORMS,
    }
    
    return render(request, 'dashboard/social_connections.html', context)


@login_required
def connect_social_view(request, platform):
    """Initiate OAuth connection to social platform"""
    request.session['connecting_platform'] = platform
    
    if platform == 'tiktok':
        auth_url = (
            f"https://www.tiktok.com/auth/authorize/"
            f"?client_key={settings.TIKTOK_CLIENT_KEY}"
            f"&scope=user.info.basic,video.list"
            f"&response_type=code"
            f"&redirect_uri={settings.TIKTOK_REDIRECT_URI}"
            f"&state={request.session.session_key}"
        )
        return redirect(auth_url)
    
    elif platform == 'instagram':
        auth_url = (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={settings.INSTAGRAM_CLIENT_ID}"
            f"&redirect_uri={settings.INSTAGRAM_REDIRECT_URI}"
            f"&scope=user_profile,user_media"
            f"&response_type=code"
        )
        return redirect(auth_url)
    
    messages.error(request, f'Connection to {platform} is not available yet.')
    return redirect('social_connections')


@login_required
def social_callback_view(request):
    """OAuth callback from social platforms"""
    code = request.GET.get('code')
    platform = request.session.get('connecting_platform')
    
    if not code or not platform:
        messages.error(request, 'Authorization failed.')
        return redirect('social_connections')
    
    if platform == 'tiktok':
        token_data = exchange_tiktok_code(code)
        if token_data:
            SocialConnection.objects.update_or_create(
                user=request.user,
                platform='tiktok',
                defaults={
                    'platform_user_id': token_data['open_id'],
                    'platform_username': token_data['username'],
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token', ''),
                    'token_expires': timezone.now() + timezone.timedelta(seconds=token_data.get('expires_in', 86400)),
                }
            )
            messages.success(request, '✅ TikTok connected successfully!')
    
    request.session.pop('connecting_platform', None)
    return redirect('social_connections')


@login_required
def disconnect_social_view(request, connection_id):
    """Disconnect a social account"""
    connection = get_object_or_404(SocialConnection, id=connection_id, user=request.user)
    
    if request.method == 'POST':
        platform = connection.get_platform_display()
        connection.delete()
        messages.success(request, f'{platform} disconnected.')
    
    return redirect('social_connections')


@login_required
def quick_import_view(request):
    """Quick import from social media - CRITICAL FOR SOCIAL-FIRST"""
    profile = get_user_profile(request.user)
    
    if request.method == 'POST':
        form = QuickImportForm(request.POST, user=request.user)
        if form.is_valid():
            url = form.cleaned_data['url']
            journey = form.cleaned_data['journey']
            day_number = form.cleaned_data['day_number']
            platform = form.cleaned_data.get('detected_platform') or detect_platform_from_url(url)
            caption = request.POST.get('caption', '').strip()
            embed_html = request.POST.get('embed_html', '').strip()
            thumbnail_url = request.POST.get('thumbnail_url', '').strip()
            media_url = request.POST.get('media_url', '').strip()
            media_type = request.POST.get('media_type', '').strip()
            platform_post_id = request.POST.get('platform_post_id', '').strip()
            posted_at_str = request.POST.get('posted_at', '')
            like_count = request.POST.get('like_count', 0)
            comment_count = request.POST.get('comment_count', 0)
            
            if not caption:
                caption = f"Imported from {platform.title() if platform else 'Social Media'}"
            
            # Parse posted_at
            posted_at = timezone.now()
            if posted_at_str:
                try:
                    posted_at = timezone.datetime.fromisoformat(posted_at_str.replace('Z', '+00:00'))
                except:
                    pass
            
            # Build social engagement
            social_engagement = {}
            if like_count or comment_count:
                social_engagement = {
                    'likes': int(like_count) if like_count else 0,
                    'comments': int(comment_count) if comment_count else 0,
                    'posted_at': posted_at.isoformat(),
                }
            
            # Create or update activity
            activity, created = Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day_number,
                defaults={
                    'content': caption,
                    'source_url': url,
                    'source_platform': platform or '',
                    'embed_html': embed_html,
                    'social_engagement': social_engagement,
                    'social_post_id': platform_post_id,
                    'published_at': posted_at,
                }
            )
            
            # Also save as imported content for tracking
            ImportedContent.objects.get_or_create(
                platform=platform or 'other',
                platform_post_id=platform_post_id or url,
                defaults={
                    'social_connection': SocialConnection.objects.filter(user=request.user, platform=platform).first(),
                    'platform_url': url,
                    'caption': caption,
                    'media_url': media_url,
                    'media_type': media_type,
                    'thumbnail_url': thumbnail_url,
                    'posted_at': posted_at,
                    'like_count': int(like_count) if like_count else 0,
                    'comment_count': int(comment_count) if comment_count else 0,
                    'detected_day': day_number,
                    'assigned_journey': journey,
                    'assigned_day': day_number,
                    'status': 'assigned',
                    'created_activity': activity,
                    'processed_at': timezone.now(),
                }
            )
            
            # Track quick add
            QuickAddTracker.objects.create(
                journey=journey,
                user=request.user,
                source_url=url,
                source_platform=platform or 'other',
                detected_day=day_number,
                created_activity=activity,
            )
            
            if created:
                messages.success(request, f'✅ Content imported to Day {day_number}!')
            else:
                messages.success(request, f'✅ Day {day_number} updated!')
            
            return redirect('journey_detail', slug=journey.slug)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = QuickImportForm(user=request.user)
    
    # Get user's journeys for the form
    journeys = Journey.objects.filter(creator=profile, is_active=True)
    
    context = {
        'form': form,
        'journeys': journeys,
    }
    
    return render(request, 'dashboard/quick_import.html', context)


def exchange_tiktok_code(code):
    """Exchange TikTok authorization code for access token"""
    try:
        response = requests.post(
            'https://open-api.tiktok.com/oauth/access_token/',
            data={
                'client_key': settings.TIKTOK_CLIENT_KEY,
                'client_secret': settings.TIKTOK_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': settings.TIKTOK_REDIRECT_URI,
            }
        )
        data = response.json()
        if data.get('data'):
            return {
                'access_token': data['data']['access_token'],
                'refresh_token': data['data'].get('refresh_token'),
                'open_id': data['data']['open_id'],
                'username': data['data'].get('username', ''),
                'expires_in': data['data'].get('expires_in', 86400),
            }
    except Exception as e:
        print(f"TikTok token exchange error: {e}")
    return None


@login_required
def import_queue_view(request):
    """View and manage imported content queue"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile)
    
    imports = ImportedContent.objects.filter(
        Q(social_connection__user=request.user) | Q(social_connection__isnull=True),
        status='pending'
    ).select_related('social_connection').order_by('-posted_at')
    
    journey_id = request.GET.get('journey')
    if journey_id:
        imports = imports.filter(assigned_journey_id=journey_id)
    
    # Stats
    total_imports = ImportedContent.objects.filter(social_connection__user=request.user).count()
    pending_count = ImportedContent.objects.filter(social_connection__user=request.user, status='pending').count()
    approved_count = ImportedContent.objects.filter(social_connection__user=request.user, status='approved').count()
    assigned_count = ImportedContent.objects.filter(social_connection__user=request.user, status='assigned').count()
    
    context = {
        'imports': imports,
        'journeys': journeys,
        'selected_journey': journey_id,
        'total_imports': total_imports,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'assigned_count': assigned_count,
    }
    
    return render(request, 'dashboard/import_queue.html', context)


@login_required
@require_POST
def process_import_view(request, import_id):
    """Approve or ignore an imported item"""
    imported = get_object_or_404(
        ImportedContent,
        id=import_id,
        social_connection__user=request.user
    )
    
    action = request.POST.get('action')
    assigned_day = request.POST.get('assigned_day')
    journey_id = request.POST.get('journey_id')
    
    if action == 'approve':
        if journey_id and assigned_day:
            journey = get_object_or_404(Journey, id=journey_id, creator__user=request.user)
            imported.approve_and_assign(journey, int(assigned_day))
            messages.success(request, f'Content assigned to Day {assigned_day}!')
        else:
            imported.status = 'approved'
            imported.processed_at = timezone.now()
            imported.save()
            messages.success(request, 'Content approved!')
    
    elif action == 'ignore':
        imported.status = 'ignored'
        imported.processed_at = timezone.now()
        imported.save()
        messages.info(request, 'Content ignored.')
    
    return redirect('import_queue')


# ============================================================================
# API VIEWS FOR SOCIAL IMPORT - CRITICAL
# ============================================================================

@login_required
def api_preview_url(request):
    """Preview social media content from URL - CRITICAL FOR SOCIAL-FIRST"""
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'success': False, 'error': 'No URL provided'})
    
    platform = detect_platform_from_url(url)
    if not platform:
        return JsonResponse({'success': False, 'error': 'Unsupported platform'})
    
    # Try oEmbed first
    oembed_data = fetch_oembed_data(url, platform)
    
    if oembed_data and (oembed_data.get('thumbnail_url') or oembed_data.get('html')):
        embed_html = oembed_data.get('html', '')
        
        # Sanitize embed
        import re
        embed_html = re.sub(r'<script[^>]*>.*?</script>', '', embed_html, flags=re.DOTALL)
        
        # For Instagram, use placeholder
        if platform == 'instagram':
            embed_html = f'<div class="instagram-placeholder" data-instgrm-permalink="{url}"><div style="background:var(--bg-secondary);padding:40px;text-align:center;border-radius:12px;"><i class="fab fa-instagram" style="font-size:32px;margin-bottom:8px;display:block;"></i><span>Instagram Post</span><a href="{url}" target="_blank" style="display:block;margin-top:8px;color:var(--accent);">View on Instagram →</a></div></div>'
        
        # For TikTok
        elif platform == 'tiktok':
            embed_html = f'<div class="tiktok-placeholder" style="background:var(--bg-secondary);padding:40px;text-align:center;border-radius:12px;"><i class="fab fa-tiktok" style="font-size:32px;margin-bottom:8px;display:block;"></i><span>TikTok Video</span><a href="{url}" target="_blank" style="display:block;margin-top:8px;color:var(--accent);">Watch on TikTok →</a></div>'
        
        # For Twitter
        elif platform == 'twitter':
            embed_html = f'<div class="twitter-placeholder" style="background:var(--bg-secondary);padding:40px;text-align:center;border-radius:12px;"><i class="fab fa-twitter" style="font-size:32px;margin-bottom:8px;display:block;"></i><span>Tweet</span><a href="{url}" target="_blank" style="display:block;margin-top:8px;color:var(--accent);">View on X →</a></div>'
        
        # For Facebook
        elif platform == 'facebook':
            embed_html = f'<div class="facebook-placeholder" style="background:var(--bg-secondary);padding:40px;text-align:center;border-radius:12px;"><i class="fab fa-facebook" style="font-size:32px;margin-bottom:8px;display:block;"></i><span>Facebook Post</span><a href="{url}" target="_blank" style="display:block;margin-top:8px;color:var(--accent);">View on Facebook →</a></div>'
        
        # For YouTube
        elif platform == 'youtube':
            video_id = extract_youtube_video_id(url)
            if video_id:
                embed_html = f'<div class="youtube-embed-wrapper" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;background:#000;"><iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&playsinline=1" frameborder="0" allowfullscreen></iframe></div>'
        
        return JsonResponse({
            'success': True,
            'platform': platform,
            'title': oembed_data.get('title', f'{platform.title()} Post'),
            'thumbnail_url': oembed_data.get('thumbnail_url', ''),
            'author_name': oembed_data.get('author_name', ''),
            'html': embed_html,
        })
    
    # Fallback: use safe placeholders
    safe_placeholders = {
        'tiktok': ('fa-tiktok', 'TikTok Video', 'Watch on TikTok'),
        'instagram': ('fa-instagram', 'Instagram Post', 'View on Instagram'),
        'youtube': ('fa-youtube', 'YouTube Video', 'Watch on YouTube'),
        'facebook': ('fa-facebook', 'Facebook Post', 'View on Facebook'),
        'twitter': ('fa-twitter', 'Tweet', 'View on X'),
        'linkedin': ('fa-linkedin', 'LinkedIn Post', 'View on LinkedIn'),
    }
    
    icon, label, action = safe_placeholders.get(platform, ('fa-link', 'Content', 'View Original'))
    
    embed_html = f'<div style="background:var(--bg-secondary);padding:40px;text-align:center;border-radius:12px;"><i class="fab {icon}" style="font-size:32px;margin-bottom:8px;display:block;"></i><span>{label}</span><a href="{url}" target="_blank" style="display:block;margin-top:8px;color:var(--accent);">{action} →</a></div>'
    
    return JsonResponse({
        'success': True,
        'platform': platform,
        'title': f'{platform.title()} Post',
        'thumbnail_url': '',
        'author_name': '',
        'html': embed_html,
    })


def fetch_oembed_data(url, platform):
    """Fetch oEmbed data for a URL"""
    import requests
    
    oembed_endpoints = {
        'tiktok': 'https://www.tiktok.com/oembed',
        'youtube': 'https://www.youtube.com/oembed',
        'instagram': 'https://graph.facebook.com/v18.0/instagram_oembed',
        'facebook': 'https://graph.facebook.com/v18.0/oembed_post',
        'twitter': 'https://publish.twitter.com/oembed',
    }
    
    endpoint = oembed_endpoints.get(platform)
    if not endpoint:
        return None
    
    request_url = url
    if platform == 'twitter':
        request_url = url.replace('x.com', 'twitter.com')
    
    try:
        params = {'url': request_url, 'omit_script': '1'}
        
        if platform == 'twitter':
            params['dnt'] = '1'
            params['hide_thread'] = '1'
            params['theme'] = 'dark'
        
        response = requests.get(endpoint, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', ''),
                'thumbnail_url': data.get('thumbnail_url', ''),
                'author_name': data.get('author_name', ''),
                'html': data.get('html', ''),
            }
    except Exception as e:
        print(f"oEmbed fetch error for {platform}: {e}")
    
    return None


def extract_youtube_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ============================================================================
# SOCIAL POST TEMPLATES - NEW (Social-First)
# ============================================================================

@login_required
def social_template_view(request, slug):
    """Manage social post templates for a journey"""
    journey = get_object_or_404(Journey, slug=slug, creator__user=request.user)
    templates = SocialPostTemplate.objects.filter(journey=journey)
    
    if request.method == 'POST':
        form = SocialPostTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.journey = journey
            template.save()
            messages.success(request, f'Template for {template.get_platform_display()} created!')
            return redirect('social_template', slug=slug)
    else:
        form = SocialPostTemplateForm()
    
    context = {
        'journey': journey,
        'templates': templates,
        'form': form,
    }
    
    return render(request, 'dashboard/social_templates.html', context)


@login_required
@require_POST
def delete_social_template_view(request, template_id):
    """Delete a social post template"""
    template = get_object_or_404(SocialPostTemplate, id=template_id, journey__creator__user=request.user)
    journey_slug = template.journey.slug
    template.delete()
    messages.success(request, 'Template deleted.')
    return redirect('social_template', slug=journey_slug)


@login_required
def api_social_template(request, template_id):
    """Get a single social template for editing"""
    template = get_object_or_404(SocialPostTemplate, id=template_id, journey__creator__user=request.user)
    
    return JsonResponse({
        'success': True,
        'id': template.id,
        'platform': template.platform,
        'template_text': template.template_text,
        'auto_post': template.auto_post,
    })


# ============================================================================
# API SOCIAL SETTINGS - FIXED (Moved to proper location)
# ============================================================================

@login_required
def api_social_settings(request, connection_id):
    """Get or update social connection settings"""
    connection = get_object_or_404(SocialConnection, id=connection_id, user=request.user)
    
    if request.method == 'GET':
        return JsonResponse({
            'auto_import': connection.auto_import,
            'import_hashtag': connection.import_hashtag,
        })
    
    elif request.method == 'POST':
        connection.auto_import = request.POST.get('auto_import') == 'on'
        connection.import_hashtag = request.POST.get('import_hashtag', '')
        connection.save()
        return JsonResponse({'success': True})


# ============================================================================
# ENGAGEMENT VIEWS
# ============================================================================

@login_required
@require_POST
def follow_journey_view(request, slug):
    """Follow/unfollow a journey"""
    journey = get_object_or_404(Journey, slug=slug)
    
    follow, created = JourneyFollow.objects.get_or_create(
        user=request.user,
        journey=journey
    )
    
    if not created:
        follow.delete()
        following = False
    else:
        following = True
    
    return JsonResponse({
        'following': following,
        'follower_count': journey.get_follower_count(),
    })


@login_required
@require_POST
def save_journey_view(request, slug):
    """Save/unsave a journey"""
    journey = get_object_or_404(Journey, slug=slug)
    
    saved, created = JourneySave.objects.get_or_create(
        user=request.user,
        journey=journey
    )
    
    if not created:
        saved.delete()
        is_saved = False
    else:
        is_saved = True
    
    return JsonResponse({
        'saved': is_saved,
        'save_count': journey.get_save_count(),
    })


@login_required
@require_POST
def love_activity_view(request, activity_id):
    """Love/unlove an activity"""
    activity = get_object_or_404(Activity, id=activity_id)
    
    love, created = ActivityLove.objects.get_or_create(
        user=request.user,
        activity=activity
    )
    
    if not created:
        love.delete()
        loved = False
    else:
        loved = True
    
    return JsonResponse({
        'loved': loved,
        'love_count': activity.get_love_count(),
    })


@require_POST
def comment_activity_view(request, activity_id):
    """Add a comment to an activity"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Please log in to comment'}, status=401)
    
    activity = get_object_or_404(Activity, id=activity_id)
    content = request.POST.get('content', '').strip()
    
    if not content:
        return JsonResponse({'success': False, 'error': 'Comment cannot be empty'}, status=400)
    
    comment = ActivityComment.objects.create(
        activity=activity,
        user=request.user,
        content=content
    )
    
    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'user': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.strftime('%b %d, %Y'),
        },
        'comment_count': activity.get_comment_count(),
    })


@login_required
@require_POST
def share_journey_view(request, slug):
    """Track a journey share"""
    journey = get_object_or_404(Journey, slug=slug)
    platform = request.POST.get('platform', 'other')
    
    Share.objects.create(
        journey=journey,
        user=request.user,
        platform=platform
    )
    
    # Update traffic sources
    if platform in ['twitter', 'instagram', 'facebook', 'linkedin', 'tiktok']:
        journey.record_traffic_source(platform)
    
    return JsonResponse({
        'success': True,
        'share_count': journey.get_share_count(),
    })


# ============================================================================
# PROFILE VIEWS
# ============================================================================

@login_required
def profile_settings_view(request):
    """Edit profile settings"""
    profile = get_user_profile(request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_settings')
    else:
        form = ProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'dashboard/profile_settings.html', context)


@login_required
def saved_journeys_view(request):
    """View saved/bookmarked journeys"""
    saves = JourneySave.objects.filter(
        user=request.user
    ).select_related('journey', 'journey__creator__user').order_by('-saved_at')
    
    context = {
        'saves': saves,
    }
    
    return render(request, 'dashboard/saved_journeys.html', context)


# ============================================================================
# NOTIFICATION VIEWS
# ============================================================================

@login_required
def notifications_view(request):
    """View all notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    
    try:
        notifications_page = paginator.page(page)
    except PageNotAnInteger:
        notifications_page = paginator.page(1)
    except EmptyPage:
        notifications_page = paginator.page(paginator.num_pages)
    
    context = {
        'notifications': notifications_page,
        'unread_count': notifications.filter(viewed=False).count(),
    }
    
    return render(request, 'dashboard/notifications.html', context)


@login_required
@require_POST
def mark_notification_read_view(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.viewed = True
    notification.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_notifications_read_view(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, viewed=False).update(viewed=True)
    
    return JsonResponse({'success': True})


@login_required
def unread_notification_count(request):
    """API endpoint for unread notification count"""
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0})
    
    try:
        unread_count = Notification.objects.filter(
            user=request.user, 
            viewed=False
        ).count()
        return JsonResponse({'unread_count': unread_count})
    except Exception:
        return JsonResponse({'unread_count': 0})


# ============================================================================
# REPORT VIEWS
# ============================================================================

@login_required
@require_POST
def report_journey_view(request, slug):
    """Report a journey"""
    journey = get_object_or_404(Journey, slug=slug)
    
    form = ReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.journey = journey
        report.reported_by = request.user
        report.save()
        
        messages.success(request, 'Thank you for your report. We will review it shortly.')
    else:
        messages.error(request, 'Please select a reason for your report.')
    
    return redirect('journey_detail', slug=slug)


@login_required
@require_POST
def report_activity_view(request, activity_id):
    """Report an activity"""
    activity = get_object_or_404(Activity, id=activity_id)
    
    form = ReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.activity = activity
        report.reported_by = request.user
        report.save()
        
        messages.success(request, 'Thank you for your report. We will review it shortly.')
    else:
        messages.error(request, 'Please select a reason for your report.')
    
    return redirect('journey_detail', slug=activity.journey.slug)


# ============================================================================
# FAQ VIEWS
# ============================================================================

def faq_view(request):
    """FAQ page"""
    faqs = FAQ.objects.filter(is_active=True).order_by('category', 'order')
    
    faqs_by_category = {}
    for faq in faqs:
        if faq.category not in faqs_by_category:
            faqs_by_category[faq.category] = []
        faqs_by_category[faq.category].append(faq)
    
    context = {
        'faqs_by_category': faqs_by_category,
        'categories': FAQ.CATEGORY_CHOICES,
    }
    
    return render(request, 'faq.html', context)


# ============================================================================
# CONTACT VIEWS
# ============================================================================

def contact_view(request):
    """Contact form with AI response"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', 'general')
        message = request.POST.get('message', '').strip()
        
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        if not email:
            errors['email'] = 'Email is required'
        elif '@' not in email or '.' not in email:
            errors['email'] = 'Enter a valid email'
        if not message:
            errors['message'] = 'Message is required'
        
        if errors:
            return render(request, 'contact.html', {
                'errors': errors,
                'form_data': request.POST,
                'submitted': False
            })
        
        # Generate AI response (simplified)
        ai_response = f"Thanks {name}! We'll get back to you soon about your question."
        
        # Save to database
        try:
            contact = ContactMessage(
                user=request.user if request.user.is_authenticated else None,
                name=name,
                email=email,
                subject=subject,
                message=message,
                ai_response=ai_response,
                ip_address=get_client_ip(request)
            )
            contact.save()
        except Exception as e:
            print(f"Contact save error: {e}")
        
        return render(request, 'contact.html', {
            'submitted': True,
            'ai_response': ai_response,
            'name': name
        })
    
    return render(request, 'contact.html', {'submitted': False})


# ============================================================================
# CONVERSION / NEWSLETTER VIEWS
# ============================================================================

def conversion_start_view(request):
    """Conversion page for email capture"""
    if request.session.get('subscribed', False):
        show_form = False
        show_downloads = True
    else:
        show_form = True
        show_downloads = False
    
    if request.method == 'POST' and show_form:
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            return render(request, 'conversion/start.html', {
                'errors': {'email': 'Email is required'},
                'show_form': True,
                'show_downloads': False,
            })
        
        subscriber, created = Subscriber.objects.get_or_create(
            email=email,
            defaults={
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            }
        )
        
        request.session['subscribed'] = True
        request.session['subscriber_email'] = email
        
        return render(request, 'conversion/start.html', {
            'show_form': False,
            'show_downloads': True,
            'just_subscribed': True,
            'subscriber_email': email,
        })
    
    return render(request, 'conversion/start.html', {
        'show_form': show_form,
        'show_downloads': show_downloads,
        'just_subscribed': False,
    })


# ============================================================================
# STATIC PAGES
# ============================================================================

def about_view(request):
    return render(request, 'about.html')


def privacy_view(request):
    return render(request, 'privacy.html')


def terms_view(request):
    return render(request, 'terms.html')


# ============================================================================
# BLOG VIEWS
# ============================================================================

def blog_index(request):
    return render(request, 'blog/index.html')


def blog_instagram(request):
    return render(request, 'blog/why-instagram.html')


def blog_posts_not_journeys(request):
    return render(request, 'blog/posts-not-journeys.html')


def blog_challenge_product(request):
    return render(request, 'blog/challenge-to-product.html')


def blog_journey_content(request):
    return render(request, 'blog/journey-50-pieces.html')


def blog_scattered_posts(request):
    return render(request, 'blog/scattered-to-structured.html')


def blog_buried_asset(request):
    return render(request, 'blog/buried-asset.html')


def blog_blind_spot(request):
    return render(request, 'blog/blind-spot.html')


def blog_challenge_fails(request):
    return render(request, 'blog/30-day-challenge-fails.html')


def blog_journey_page(request):
    return render(request, 'blog/journey-page-for-coaches.html')


def blog_challenge_lost(request):
    return render(request, 'blog/challenge-lost-after-day-7.html')


# ============================================================================
# THEME TOGGLE
# ============================================================================

@require_POST
def toggle_theme(request):
    """Single endpoint for all templates to toggle theme"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        
        response = JsonResponse({'success': True, 'theme': theme})
        response.set_cookie('theme', theme, max_age=365*24*60*60, httponly=True, samesite='Lax')
        return response
    except:
        return JsonResponse({'success': False}, status=400)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    return render(request, 'errors/403.html', status=403)


# ============================================================================
# TEMPLATE STORE VIEW - ADD THIS
# ============================================================================

def template_store_view(request):
    """Template store page - placeholder for now"""
    # This is a placeholder view. Later you can add actual template logic.
    return render(request, 'templates/store.html', {
        'templates': [],  # Empty for now
        'user_journeys': Journey.objects.filter(creator__user=request.user, is_active=True) if request.user.is_authenticated else [],
    })


# ============================================================================
# ONBOARDING WIZARD - ADD THIS
# ============================================================================

def onboarding_wizard_view(request):
    """Onboarding wizard for new users"""
    return render(request, 'onboarding/wizard.html', {})


# ============================================================================
# WELCOME VIEW - ADD THIS
# ============================================================================

def welcome_view(request):
    """Welcome page for creators coming from DMs"""
    return render(request, 'welcome.html', {})


# ============================================================================
# PREVIEW & CLAIM VIEWS - ADD THESE
# ============================================================================

def preview_journey_view(request, slug):
    """Public preview page - no login required"""
    journey = get_object_or_404(
        Journey.objects.select_related('creator__user').prefetch_related('activities'),
        slug=slug,
        is_active=True
    )
    
    if not journey.is_public:
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404("Journey not found")
    
    is_claimed = not journey.creator.user.username.startswith('rallynex')
    activities_by_day = journey.get_all_activities_by_day()
    current_day = journey.get_current_day()
    current_activity = activities_by_day.get(current_day)
    
    context = {
        'journey': journey,
        'activities_by_day': activities_by_day,
        'current_day': current_day,
        'current_activity': current_activity,
        'is_claimed': is_claimed,
        'total_days_range': range(1, journey.duration + 1),
    }
    
    return render(request, 'journey/preview.html', context)


@login_required
def claim_journey_view(request, slug):
    """Claim a preview journey after signup"""
    journey = get_object_or_404(Journey, slug=slug)
    
    if not journey.creator.user.username.startswith('rallynex'):
        messages.warning(request, 'This journey has already been claimed.')
        return redirect('journey_detail', slug=slug)
    
    profile = get_user_profile(request.user)
    journey.creator = profile
    journey.is_public = True
    journey.save()
    
    messages.success(request, f'🎉 You now own "{journey.title}"! Start adding more content.')
    return redirect('journey_detail', slug=slug)



@login_required
def toolbox_view(request):
    """Creator Toolbox - Central hub for all tools"""
    profile = get_user_profile(request.user)
    
    # Get stats
    journeys = Journey.objects.filter(creator=profile)
    total_journeys = journeys.count()
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    
    # Import stats
    total_imported = ImportedContent.objects.filter(
        social_connection__user=request.user
    ).count()
    
    pending_imports = ImportedContent.objects.filter(
        social_connection__user=request.user,
        status='pending'
    ).count()
    
    # Recent activity (last 5)
    recent_activities = Activity.objects.filter(
        journey__creator=profile
    ).select_related('journey').order_by('-created_at')[:5]
    
    context = {
        'total_journeys': total_journeys,
        'total_followers': total_followers,
        'total_views': total_views,
        'total_imported': total_imported,
        'pending_imports': pending_imports,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'toolbox/index.html', context)




    