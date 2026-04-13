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

from .models import (
    Profile, SocialConnection, ImportedContent,
    Journey, Activity, JourneyFollow, Tag, JourneyTag,
    ActivityLove, ActivityComment, JourneySave, Share,
    Donation, Notification, PostJourneyProduct,
    Report, Blog, FAQ
)
from .forms import (
    SignUpForm, LoginForm, ProfileForm,
    JourneyForm, JourneySettingsForm, ActivityForm, QuickImportForm,
    SocialConnectForm, SocialSettingsForm,
    CommentForm, DonationForm, JourneySearchForm,
    ReportForm, PostJourneyProductForm
)




def welcome_view(request):
    """Welcome page for creators coming from DMs"""
    return render(request, 'welcome.html')

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
import json

@login_required
@require_POST
def api_quick_create_journey(request):
    """API endpoint to quickly create a journey during onboarding"""
    try:
        data = json.loads(request.body)
        
        profile = request.user.profile
        
        # Create journey
        journey = Journey.objects.create(
            creator=profile,
            title=data.get('title', 'My Journey'),
            description=f"Documenting my {data.get('title', 'journey')} day by day.",
            category=data.get('category', 'personal'),
            journey_type='daily',
            duration=int(data.get('duration', 30)),
            is_public=True,
            is_active=True,
            published_at=timezone.now(),
        )
        
        # Generate slug
        journey.slug = slugify(journey.title)
        journey.save()
        
        # If they provided current_day > 1, create placeholder activities
        current_day = int(data.get('current_day', 1))
        if current_day > 1:
            for day in range(1, current_day):
                Activity.objects.get_or_create(
                    journey=journey,
                    day_number_field=day,
                    defaults={
                        'content': f'Day {day} of {journey.title}',
                        'published_at': timezone.now() - timezone.timedelta(days=current_day-day),
                    }
                )
        
        return JsonResponse({
            'success': True,
            'slug': journey.slug,
            'journey_url': request.build_absolute_uri(f'/j/{journey.slug}/'),
            'post_update_url': f'/dashboard/journeys/{journey.slug}/post/{current_day}/',
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)




@login_required
def onboarding_wizard_view(request):
    """Onboarding wizard for new users"""
    return render(request, 'onboarding/wizard.html')





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
    user = request.user if request.user.is_authenticated else None
    
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
    if 'tiktok.com' in url:
        return 'tiktok'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    return None


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def signup_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Rallynex, {user.username}!')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Handle remember me
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
    """Landing page"""
    # Get featured journeys
    featured_journeys = Journey.objects.filter(
        is_public=True,
        is_active=True,
        is_featured=True
    ).select_related('creator__user').prefetch_related('activities')[:6]
    
    # Get trending journeys (most views in last 7 days)
    trending_journeys = Journey.objects.filter(
        is_public=True,
        is_active=True
    ).order_by('-view_count')[:6]
    
    # Get recent blog posts
    recent_blogs = Blog.objects.filter(
        status='published'
    ).order_by('-published_at')[:3]
    
    context = {
        'featured_journeys': featured_journeys,
        'trending_journeys': trending_journeys,
        'recent_blogs': recent_blogs,
    }
    
    return render(request, 'landing.html', context)

def discover_view(request):
    """Browse and discover journeys"""
    form = JourneySearchForm(request.GET)
    journeys = Journey.objects.filter(is_public=True, is_active=True)
    
    if form.is_valid():
        # Search query
        q = form.cleaned_data.get('q')
        if q:
            journeys = journeys.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(creator__user__username__icontains=q)
            )
        
        # Category filter
        category = form.cleaned_data.get('category')
        if category:
            journeys = journeys.filter(category=category)
        
        # Journey type filter
        journey_type = form.cleaned_data.get('journey_type')
        if journey_type:
            journeys = journeys.filter(journey_type=journey_type)
        
        # Funding filter
        if form.cleaned_data.get('funding_enabled'):
            journeys = journeys.filter(funding_enabled=True)
        
        # Sort - FIXED: ensure valid sort field
        sort = form.cleaned_data.get('sort')
        allowed_sorts = ['-created_at', 'created_at', '-view_count', 'view_count', 'title', '-title']
        
        if sort and sort in allowed_sorts:
            journeys = journeys.order_by(sort)
        else:
            journeys = journeys.order_by('-created_at')
    else:
        journeys = journeys.order_by('-created_at')
    
    # Handle sort from GET parameter directly (for filter chips)
    sort_param = request.GET.get('sort')
    if sort_param:
        allowed_sorts = ['-created_at', 'created_at', '-view_count', 'view_count', 'title', '-title']
        if sort_param in allowed_sorts:
            journeys = journeys.order_by(sort_param)
    
    # Pagination
    paginator = Paginator(journeys, 12)
    page = request.GET.get('page')
    
    try:
        journeys_page = paginator.page(page)
    except PageNotAnInteger:
        journeys_page = paginator.page(1)
    except EmptyPage:
        journeys_page = paginator.page(paginator.num_pages)
    
    # Get categories for filter sidebar
    categories = Journey.CATEGORY_CHOICES
    
    context = {
        'form': form,
        'journeys': journeys_page,
        'categories': categories,
        'total_count': journeys.count(),
    }
    
    return render(request, 'discover.html', context)

def journey_detail_view(request, slug):
    """View a single journey"""
    journey = get_object_or_404(
        Journey.objects.select_related('creator__user').prefetch_related(
            'activities', 'tags', 'followers'
        ),
        slug=slug,
        is_public=True,
        is_active=True
    )
    
    # Track view
    track_journey_view(request, journey)
    
    # Get activities organized by day
    activities_by_day = journey.get_all_activities_by_day()
    
    # Get current day and activity
    current_day = journey.get_current_day()
    current_activity = activities_by_day.get(current_day)
    
    # Check if user is following
    is_following = False
    if request.user.is_authenticated:
        is_following = JourneyFollow.objects.filter(
            user=request.user,
            journey=journey
        ).exists()
    
    # Check if user has saved
    is_saved = False
    if request.user.is_authenticated:
        is_saved = JourneySave.objects.filter(
            user=request.user,
            journey=journey
        ).exists()
    
    # Get recent comments
    recent_comments = ActivityComment.objects.filter(
        activity__journey=journey
    ).select_related('user', 'activity').order_by('-created_at')[:10]
    
    # Get related journeys
    related_journeys = Journey.objects.filter(
        category=journey.category,
        is_public=True,
        is_active=True
    ).exclude(id=journey.id).order_by('-view_count')[:4]
    
    # Prepare activities JSON for JavaScript
    activities_json = {}
    for day, activity in activities_by_day.items():
        activities_json[day] = {
            'id': activity.id,
            'content': activity.content,
            'fileUrl': activity.file.url if activity.file else None,
            'isVideo': activity.is_video,
            'loveCount': activity.get_love_count(),
            'commentCount': activity.get_comment_count(),
        }
    
    context = {
        'journey': journey,
        'activities_by_day': activities_by_day,
        'activities_json': json.dumps(activities_json),
        'current_day': current_day,
        'current_activity': current_activity,
        'is_following': is_following,
        'is_saved': is_saved,
        'recent_comments': recent_comments,
        'related_journeys': related_journeys,
        'total_days_range': range(1, journey.duration + 1),
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
    
    # Pagination
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
    
    # Get user's journeys
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    # Stats
    total_journeys = journeys.count()
    active_journeys = journeys.filter(is_active=True).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    # Recent activity
    recent_activities = Activity.objects.filter(
        journey__creator=profile
    ).select_related('journey').order_by('-created_at')[:10]
    
    # Recent comments
    recent_comments = ActivityComment.objects.filter(
        activity__journey__creator=profile
    ).select_related('user', 'activity__journey').order_by('-created_at')[:5]
    
    # Recent donations
    recent_donations = Donation.objects.filter(
        journey__creator=profile,
        status='completed'
    ).order_by('-created_at')[:5]
    
    # Pending imports
    pending_imports = ImportedContent.objects.filter(
        social_connection__user=request.user,
        status='pending'
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
        'recent_donations': recent_donations,
        'pending_imports': pending_imports,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def my_journeys_view(request):
    """List all user's journeys"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    # Calculate stats
    active_count = journeys.filter(is_active=True).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    # Add stats to each journey
    for journey in journeys:
        journey.activity_count = journey.activities.count()
        journey.follower_count = journey.get_follower_count()
        journey.donation_total = journey.get_total_donations()
    
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
            journey = form.save(commit=False)
            journey.creator = profile
            journey.save()
            
            # Save tags from form
            form.save()
            
            messages.success(request, f'Journey "{journey.title}" created successfully!')
            return redirect('journey_content', slug=journey.slug)
    else:
        form = JourneyForm()
    
    context = {
        'form': form,
        'is_editing': False,
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
            journey = form.save()
            messages.success(request, f'Journey "{journey.title}" updated!')
            return redirect('my_journeys')
    else:
        form = JourneyForm(instance=journey)
    
    context = {
        'form': form,
        'journey': journey,
        'is_editing': True,
    }
    
    return render(request, 'dashboard/journey_form.html', context)


@login_required
def journey_settings_view(request, slug):
    """Quick settings for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        form = JourneySettingsForm(request.POST, instance=journey)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated!')
            return redirect('journey_detail', slug=journey.slug)
    else:
        form = JourneySettingsForm(instance=journey)
    
    return render(request, 'dashboard/journey_settings.html', {
        'form': form,
        'journey': journey,
    })


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
    
    context = {
        'journey': journey,
        'activities': activities,
        'current_day': current_day,
        'day_range': range(1, journey.duration + 1),
    }
    
    return render(request, 'dashboard/content_manager.html', context)


@login_required
def post_activity_view(request, slug, day_number=None):
    """Post an activity for a specific day"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if day_number is None:
        day_number = journey.get_current_day()
    
    # Check if day is locked
    if journey.is_day_locked(day_number):
        messages.error(request, f'Day {day_number} is not available yet.')
        return redirect('journey_detail', slug=journey.slug)
    
    # Get existing activity if any
    existing_activity = journey.get_activity_for_day(day_number)
    
    if request.method == 'POST':
        form = ActivityForm(
            request.POST, 
            request.FILES, 
            instance=existing_activity,
            journey=journey,
            day_number=day_number
        )
        if form.is_valid():
            activity = form.save()
            messages.success(request, f'Day {day_number} posted successfully!')
            return redirect('journey_detail', slug=journey.slug)
    else:
        form = ActivityForm(
            instance=existing_activity,
            journey=journey,
            day_number=day_number,
            initial={'content': existing_activity.content if existing_activity else ''}
        )
    
    context = {
        'form': form,
        'journey': journey,
        'day_number': day_number,
        'existing_activity': existing_activity,
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
# SOCIAL IMPORT VIEWS
# ============================================================================

@login_required
def social_connections_view(request):
    """Manage social media connections"""
    connections = SocialConnection.objects.filter(user=request.user)
    
    context = {
        'connections': connections,
        'platforms': SocialConnection.PLATFORMS,
    }
    
    return render(request, 'dashboard/social_connections.html', context)


@login_required
def connect_social_view(request, platform):
    """Initiate OAuth connection to social platform"""
    # Store platform in session for callback
    request.session['connecting_platform'] = platform
    
    if platform == 'tiktok':
        # TikTok OAuth URL
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
        # Instagram OAuth URL
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
    
    # Exchange code for token (implementation depends on platform)
    # This is a simplified example - you'll need platform-specific logic
    
    if platform == 'tiktok':
        # Exchange code for token
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
            messages.success(request, 'TikTok connected successfully!')
    
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
def import_queue_view(request):
    """View and manage imported content queue"""
    profile = get_user_profile(request.user)
    
    # Get user's journeys for filter
    journeys = Journey.objects.filter(creator=profile)
    
    # Get pending imports
    imports = ImportedContent.objects.filter(
        social_connection__user=request.user,
        status='pending'
    ).select_related('social_connection').order_by('-posted_at')
    
    # Filter by journey if specified
    journey_id = request.GET.get('journey')
    if journey_id:
        imports = imports.filter(assigned_journey_id=journey_id)
    
    context = {
        'imports': imports,
        'journeys': journeys,
        'selected_journey': journey_id,
    }
    
    return render(request, 'dashboard/import_queue.html', context)


@login_required
def quick_import_view(request):
    """Quick import from social media via paste link"""
    profile = get_user_profile(request.user)
    
    if request.method == 'POST':
        form = QuickImportForm(request.POST, user=request.user)
        if form.is_valid():
            url = form.cleaned_data['url']
            journey = form.cleaned_data['journey']
            day_number = form.cleaned_data['day_number']
            platform = form.cleaned_data.get('detected_platform')
            
            # Create imported content record
            imported = ImportedContent.objects.create(
                social_connection=None,  # Manual import
                platform=platform,
                platform_post_id=f"manual_{timezone.now().timestamp()}",
                platform_url=url,
                caption=f"Imported from {platform}",
                media_url=url,
                media_type='video' if 'video' in url else 'image',
                posted_at=timezone.now(),
                detected_day=day_number,
                assigned_journey=journey,
                assigned_day=day_number,
                status='assigned',
                processed_at=timezone.now()
            )
            
            # Create activity
            activity = Activity.objects.create(
                journey=journey,
                content=imported.caption,
                source_url=url,
                day_number_field=day_number,
                imported_from=imported
            )
            
            imported.created_activity = activity
            imported.save()
            
            messages.success(request, f'Content imported to Day {day_number}!')
            return redirect('journey_content', slug=journey.slug)
    else:
        form = QuickImportForm(user=request.user)
    
    return render(request, 'dashboard/quick_import.html', {'form': form})


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


def exchange_tiktok_code(code):
    """Exchange TikTok authorization code for access token"""
    # This is a placeholder - implement actual TikTok API call
    # TikTok OAuth documentation: https://developers.tiktok.com/doc/oauth-user-access-token-management/
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


@login_required
@require_POST
def comment_activity_view(request, activity_id):
    """Add a comment to an activity"""
    activity = get_object_or_404(Activity, id=activity_id)
    
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.activity = activity
        comment.user = request.user
        comment.save()
        
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
    
    return JsonResponse({'success': False, 'errors': form.errors})


@login_required
@require_POST
def share_journey_view(request, slug):
    """Track a journey share"""
    journey = get_object_or_404(Journey, slug=slug)
    platform = request.POST.get('platform', 'other')
    
    Share.objects.create(
        journey=journey,
        user=request.user if request.user.is_authenticated else None,
        platform=platform
    )
    
    return JsonResponse({
        'success': True,
        'share_count': journey.get_share_count(),
    })


# ============================================================================
# DONATION VIEWS
# ============================================================================

def donation_view(request, slug):
    """Make a donation to a journey"""
    journey = get_object_or_404(Journey, slug=slug, funding_enabled=True)
    
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.journey = journey
            donation.donor = request.user if request.user.is_authenticated else None
            donation.save()
            
            # Redirect to payment processor
            request.session['donation_id'] = donation.id
            return redirect('process_donation', donation_id=donation.id)
    else:
        form = DonationForm()
    
    context = {
        'journey': journey,
        'form': form,
        'total_raised': journey.get_total_donations(),
        'donation_percentage': journey.get_donation_percentage(),
        'donor_count': journey.donations.filter(status='completed').values('donor').distinct().count(),
    }
    
    return render(request, 'donation/donate.html', context)


def process_donation_view(request, donation_id):
    """Process donation payment"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # This would integrate with PayPal/Stripe
    # For now, we'll simulate a successful payment
    
    context = {
        'donation': donation,
        'journey': donation.journey,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
    }
    
    return render(request, 'donation/process.html', context)


@csrf_exempt
def donation_success_view(request):
    """Donation success callback"""
    donation_id = request.session.get('donation_id')
    
    if donation_id:
        donation = Donation.objects.get(id=donation_id)
        donation.status = 'completed'
        donation.completed_at = timezone.now()
        donation.save()
        
        request.session.pop('donation_id', None)
        
        messages.success(request, 'Thank you for your donation!')
        return redirect('journey_detail', slug=donation.journey.slug)
    
    return redirect('landing')


def donation_cancel_view(request):
    """Donation cancelled"""
    messages.info(request, 'Donation cancelled.')
    return redirect('landing')


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
    
    # Pagination
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
# POST-JOURNEY PRODUCT VIEWS
# ============================================================================

@login_required
def create_product_view(request, slug):
    """Create a post-journey product"""
    journey = get_object_or_404(Journey, slug=slug, creator__user=request.user)
    
    if request.method == 'POST':
        form = PostJourneyProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.journey = journey
            product.save()
            
            messages.success(request, f'Product "{product.title}" created!')
            return redirect('journey_detail', slug=journey.slug)
    else:
        form = PostJourneyProductForm()
    
    context = {
        'form': form,
        'journey': journey,
    }
    
    return render(request, 'dashboard/product_form.html', context)


@login_required
def edit_product_view(request, product_id):
    """Edit a post-journey product"""
    product = get_object_or_404(
        PostJourneyProduct,
        id=product_id,
        journey__creator__user=request.user
    )
    
    if request.method == 'POST':
        form = PostJourneyProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.title}" updated!')
            return redirect('journey_detail', slug=product.journey.slug)
    else:
        form = PostJourneyProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'journey': product.journey,
    }
    
    return render(request, 'dashboard/product_form.html', context)


# ============================================================================
# BLOG VIEWS
# ============================================================================

def blog_list_view(request):
    """List all blog posts"""
    blogs = Blog.objects.filter(status='published').order_by('-published_at')
    
    # Pagination
    paginator = Paginator(blogs, 9)
    page = request.GET.get('page')
    
    try:
        blogs_page = paginator.page(page)
    except PageNotAnInteger:
        blogs_page = paginator.page(1)
    except EmptyPage:
        blogs_page = paginator.page(paginator.num_pages)
    
    context = {
        'blogs': blogs_page,
        'categories': Blog.CATEGORY_CHOICES,
    }
    
    return render(request, 'blog/list.html', context)


def blog_detail_view(request, slug):
    """View a single blog post"""
    blog = get_object_or_404(Blog, slug=slug, status='published')
    
    # Increment view count
    blog.view_count += 1
    blog.save(update_fields=['view_count'])
    
    # Get related posts
    related_posts = Blog.objects.filter(
        status='published',
        category=blog.category
    ).exclude(id=blog.id).order_by('-published_at')[:3]
    
    context = {
        'blog': blog,
        'related_posts': related_posts,
    }
    
    return render(request, 'blog/detail.html', context)


# ============================================================================
# FAQ VIEWS
# ============================================================================

def faq_view(request):
    """FAQ page"""
    faqs = FAQ.objects.filter(is_active=True).order_by('category', 'order')
    
    # Group by category
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
# API VIEWS (for AJAX)
# ============================================================================

@login_required
def api_journey_stats_view(request, slug):
    """API endpoint for journey stats"""
    journey = get_object_or_404(Journey, slug=slug, creator__user=request.user)
    
    # Daily stats for last 30 days
    from django.db.models.functions import TruncDate
    
    daily_views = Activity.objects.filter(
        journey=journey
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('-date')[:30]
    
    return JsonResponse({
        'total_views': journey.view_count,
        'unique_viewers': journey.unique_viewers,
        'follower_count': journey.get_follower_count(),
        'love_count': journey.get_love_count(),
        'comment_count': journey.get_comment_count(),
        'share_count': journey.get_share_count(),
        'save_count': journey.get_save_count(),
        'daily_views': list(daily_views),
    })


@login_required
def api_activity_stats_view(request, activity_id):
    """API endpoint for activity stats"""
    activity = get_object_or_404(
        Activity,
        id=activity_id,
        journey__creator__user=request.user
    )
    
    return JsonResponse({
        'view_count': activity.view_count,
        'love_count': activity.get_love_count(),
        'comment_count': activity.get_comment_count(),
    })


# ============================================================================
# STATIC PAGES
# ============================================================================

def about_view(request):
    """About page"""
    return render(request, 'about.html')


def privacy_view(request):
    """Privacy policy"""
    return render(request, 'privacy.html')


def terms_view(request):
    """Terms of service"""
    return render(request, 'terms.html')


def contact_view(request):
    """Contact page"""
    if request.method == 'POST':
        # Handle contact form
        messages.success(request, 'Thank you for your message. We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'contact.html')



# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handler404(request, exception):
    """Custom 404 page"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 page"""
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    """Custom 403 page"""
    return render(request, 'errors/403.html', status=403)