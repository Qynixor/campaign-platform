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
    Report, Blog, FAQ, JourneyTemplate  
)
from .forms import (
    SignUpForm, LoginForm, ProfileForm,
    JourneyForm, JourneySettingsForm, ActivityForm, QuickImportForm,
    SocialConnectForm, SocialSettingsForm,
    CommentForm, DonationForm, JourneySearchForm,
    ReportForm, PostJourneyProductForm
)


from django.http import Http404

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



from django.core.serializers import json
from django.core.serializers.json import DjangoJSONEncoder

def onboarding_wizard_view(request):
    """Onboarding wizard for new users with template recommendations"""
    
    # Get all active templates for recommendations
    templates = JourneyTemplate.objects.filter(is_active=True)
    
    # Prepare template data for JavaScript
    template_data = []
    for t in templates:
        template_data.append({
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'category': t.category,
            'duration': t.duration,
            'price': 'FREE' if t.is_free else f'${t.price:.2f}' if hasattr(t, 'price') and t.price else '$9.99',
            'difficulty': getattr(t, 'difficulty', 'medium'),
            'icon': get_template_icon(t.category),
        })
    
    context = {
        'template_data': json.dumps(template_data, cls=DjangoJSONEncoder),
    }
    
    return render(request, 'onboarding/wizard.html', context)

def get_template_icon(category):
    """Get emoji icon for template category"""
    icons = {
        'fitness': '💪',
        'health': '🧘',
        'learning': '📚',
        'creative': '🎨',
        'business': '📈',
        'mindfulness': '🧘',
        'money': '💰',
        'relationships': '💕',
        'career': '💼',
    }
    return icons.get(category, '🎯')

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
    return None
# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def signup_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Get the next URL from query parameters
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Rallynex, {user.username}!')
            
            # Redirect to next URL if provided, otherwise onboarding
            if next_url:
                return redirect(next_url)
            return redirect('onboarding')
    else:
        form = SignUpForm()
    
    # Pass next_url to template to preserve it in the form
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
import json
from django.core.serializers.json import DjangoJSONEncoder
def journey_detail_view(request, slug):
    """View a single journey"""
    journey_qs = Journey.objects.select_related('creator__user').prefetch_related(
        'activities', 'tags', 'followers'
    ).filter(
        slug=slug,
        is_active=True
    )
    
    journey = get_object_or_404(journey_qs)
    
    # Allow viewing if public OR if user is the creator OR if user is superuser
    if not journey.is_public:
        if not request.user.is_authenticated or (
            request.user != journey.creator.user and not request.user.is_superuser
        ):
            raise Http404("Journey not found")
    
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
            'thumbnailUrl': activity.thumbnail.url if activity.thumbnail else None,
            'source_url': activity.source_url or '',
            'source_platform': getattr(activity, 'source_platform', ''),
            'embedHtml': activity.embed_html or '',
            'loveCount': activity.get_love_count(),
            'commentCount': activity.get_comment_count(),
        }
    
    # Use DjangoJSONEncoder to handle special characters
    activities_json_str = json.dumps(activities_json, cls=DjangoJSONEncoder)
    
    context = {
        'journey': journey,
        'activities_by_day': activities_by_day,
        'activities_json': activities_json_str,
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
    """Create a new journey - DEBUG VERSION"""
    profile = get_user_profile(request.user)
    
    print("=" * 50)
    print("CREATE JOURNEY VIEW CALLED")
    print(f"Request method: {request.method}")
    print(f"User: {request.user}")
    print(f"Profile: {profile}")
    print("=" * 50)
    
    if request.method == 'POST':
        print("POST data received:")
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                print(f"  {key}: {value[:100] if value else 'EMPTY'}")
        
        form = JourneyForm(request.POST, request.FILES)
        
        print(f"Form is valid? {form.is_valid()}")
        
        if form.is_valid():
            print("Form is VALID. Creating journey...")
            
            try:
                journey = form.save(commit=False)
                journey.creator = profile
                
                # Handle Cloudinary cover image
                cover_image_url = request.POST.get('cover_image_url')
                cover_image_public_id = request.POST.get('cover_image_public_id')
                
                print(f"Cover image URL: {cover_image_url}")
                print(f"Cover image public ID: {cover_image_public_id}")
                
                if cover_image_url and cover_image_public_id:
                    journey.cover_image_url = cover_image_url
                    journey.cover_image_public_id = cover_image_public_id
                    journey.cover_image = cover_image_public_id
                
                print(f"About to save journey with title: {journey.title}")
                journey.save()
                print(f"Journey saved! ID: {journey.id}")
                
                # Save tags
                tags_input = form.cleaned_data.get('tags_input', '')
                if tags_input:
                    tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                    for tag_name in tag_names[:10]:
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        journey.tags.add(tag)
                    print(f"Added {len(tag_names)} tags")
                
                # Save milestones
                milestones_input = request.POST.get('milestones_input', '')
                if milestones_input:
                    try:
                        import json
                        milestones_list = json.loads(milestones_input)
                        if milestones_list:
                            journey.milestones = milestones_list
                            journey.save(update_fields=['milestones'])
                            print(f"Added {len(milestones_list)} milestones")
                    except json.JSONDecodeError:
                        print(f"Milestones not JSON: {milestones_input[:100]}")
                
                messages.success(request, f'Journey "{journey.title}" created successfully!')
                print(f"SUCCESS! Redirecting to journey_content with slug: {journey.slug}")
                return redirect('journey_content', slug=journey.slug)
                
            except Exception as e:
                print(f"EXCEPTION: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error creating journey: {str(e)}')
        else:
            print("Form INVALID. Errors:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"  {field}: {error}")
                    messages.error(request, f'{field}: {error}')
    
    else:
        print("GET request - showing empty form")
        form = JourneyForm()
    
    context = {
        'form': form,
        'is_editing': False,
        'CLOUDINARY_CLOUD_NAME': settings.CLOUDINARY_CLOUD_NAME,
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
            
            # Handle Cloudinary cover image
            cover_image_url = request.POST.get('cover_image_url')
            cover_image_public_id = request.POST.get('cover_image_public_id')
            
            if cover_image_url and cover_image_public_id:
                journey.cover_image_url = cover_image_url
                journey.cover_image_public_id = cover_image_public_id
                journey.cover_image = cover_image_public_id  # ← QUICK FIX
            
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
    }
    
    return render(request, 'dashboard/journey_form.html', context)


@login_required
def journey_settings_view(request, slug):
    """Quick settings for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        # Update settings directly from POST data
        journey.is_public = request.POST.get('is_public') == 'on'
        journey.allow_comments = request.POST.get('allow_comments') == 'on'
        journey.auto_import_enabled = request.POST.get('auto_import_enabled') == 'on'
        journey.import_hashtag = request.POST.get('import_hashtag', '')
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
    
    context = {
        'journey': journey,
        'activities': activities,
        'current_day': current_day,
        'day_range': range(1, journey.duration + 1),
    }
    
    return render(request, 'dashboard/content_manager.html', context)

@login_required
def post_activity_view(request, slug, day_number=None):
    journey = get_object_or_404(Journey, slug=slug, creator__user=request.user)
    
    if day_number is None:
        day_number = journey.get_current_day()
    
    existing_activity = journey.get_activity_for_day(day_number)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        file_url = request.POST.get('file_url')
        is_video = request.POST.get('is_video') == 'true'
        actual_date = request.POST.get('actual_date')
        day = request.POST.get('day_number_field') or day_number
        clear_existing = request.POST.get('clear_existing') == 'true'
        
        if content and file_url:
            # Use update_or_create to avoid duplicate key errors
            activity, created = Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day or day_number,
                defaults={
                    'content': content,
                    'file': file_url,
                    'is_video': is_video,
                    'actual_date': actual_date if actual_date else None,
                }
            )
            
            if created:
                messages.success(request, 'Activity posted!')
            else:
                messages.success(request, 'Activity updated!')
            
            return redirect('journey_content', slug=slug)
        else:
            messages.error(request, 'Please provide content and media.')
    
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
def quick_import_view(request):
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
            
            if not caption:
                caption = f"Imported from {platform.title() if platform else 'Social Media'}"
            
            activity, created = Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day_number,
                defaults={
                    'content': caption,
                    'source_url': url,
                    'source_platform': platform or '',
                    'embed_html': embed_html,
                    'is_video': False,
                }
            )
            
            if created:
                messages.success(request, f'✅ Content imported to Day {day_number}!')
            else:
                messages.success(request, f'✅ Day {day_number} updated!')
            
            return redirect('journey_detail', slug=journey.slug)
    else:
        form = QuickImportForm(user=request.user)
    
    return render(request, 'dashboard/quick_import.html', {'form': form})

def generate_embed_html(url, platform):
    """Generate embed HTML when oEmbed fails"""
    if platform == 'youtube':
        video_id = extract_youtube_id(url)
        if video_id:
            return f'<iframe width="100%" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
    
    elif platform == 'tiktok':
        return f'<blockquote class="tiktok-embed" cite="{url}"><section></section></blockquote><script async src="https://www.tiktok.com/embed.js"></script>'
    
    elif platform == 'instagram':
        return f'<blockquote class="instagram-media" data-instgrm-permalink="{url}"></blockquote><script async src="//www.instagram.com/embed.js"></script>'
    
    elif platform == 'facebook':
        return f'<iframe src="https://www.facebook.com/plugins/post.php?href={requests.utils.quote(url)}&width=350" width="100%" height="400" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowfullscreen="true"></iframe>'
    
    return ''


def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
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

def get_embed_html_from_url(url, platform):
    """Generate embed HTML for platforms"""
    if platform == 'tiktok':
        return f'<blockquote class="tiktok-embed" cite="{url}"><section></section></blockquote><script async src="https://www.tiktok.com/embed.js"></script>'
    
    elif platform == 'instagram':
        return f'<blockquote class="instagram-media" data-instgrm-permalink="{url}"></blockquote><script async src="//www.instagram.com/embed.js"></script>'
    
    elif platform == 'youtube':
        video_id = extract_youtube_video_id(url)
        if video_id:
            return f'<iframe width="100%" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
    
    elif platform == 'facebook':
        return f'<iframe src="https://www.facebook.com/plugins/post.php?href={requests.utils.quote(url)}&width=350" width="100%" height="400" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowfullscreen="true"></iframe>'
    
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
def fetch_oembed_data(url, platform):
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
    
    # Convert x.com to twitter.com for oEmbed compatibility
    request_url = url
    if platform == 'twitter':
        request_url = url.replace('x.com', 'twitter.com')
    
    try:
        params = {'url': request_url, 'omit_script': '1'}
        
        # Twitter needs these params for richer data
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


@login_required
def api_preview_url(request):
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'success': False, 'error': 'No URL provided'})
    
    platform = detect_platform_from_url(url)
    if not platform:
        return JsonResponse({'success': False, 'error': 'Unsupported platform'})
    
    # Try oEmbed first
    oembed_data = fetch_oembed_data(url, platform)
    
    if oembed_data and (oembed_data.get('thumbnail_url') or oembed_data.get('html')):
        return JsonResponse({
            'success': True,
            'platform': platform,
            'title': oembed_data.get('title', ''),
            'thumbnail_url': oembed_data.get('thumbnail_url', ''),
            'author_name': oembed_data.get('author_name', ''),
            'html': oembed_data.get('html', ''),
        })
    
    # Fallback: generate embed HTML for known platforms
    embed_html = generate_embed_html(url, platform)
    
    # For Twitter/X, try to extract a meaningful preview
    if platform == 'twitter':
        parts = url.rstrip('/').split('/')
        username = parts[3] if len(parts) > 3 else ''
        tweet_id = parts[5] if len(parts) > 5 else ''
        
        # Twitter doesn't provide thumbnails via oEmbed without auth
        # Use a placeholder card that shows the tweet context
        return JsonResponse({
            'success': True,
            'platform': platform,
            'title': f'Tweet by @{username}',
            'thumbnail_url': '',
            'author_name': f'@{username}',
            'html': embed_html if embed_html else '',
            'embed_available': bool(embed_html),
        })
    
    # For other platforms, return what we have
    return JsonResponse({
        'success': True,
        'platform': platform,
        'title': f'{platform.title()} Post',
        'thumbnail_url': '',
        'author_name': '',
        'html': embed_html if embed_html else '',
        'embed_available': bool(embed_html),
    })




@login_required
def import_queue_view(request):
    """View and manage imported content queue"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile)
    
    # Include both connected and manual imports
    imports = ImportedContent.objects.filter(
        Q(social_connection__user=request.user) | Q(social_connection__isnull=True),
        status='pending'
    ).select_related('social_connection').order_by('-posted_at')
    
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

def preview_journey_view(request, slug):
    """Public preview page - no login required"""
    journey = get_object_or_404(
        Journey.objects.select_related('creator__user').prefetch_related('activities'),
        slug=slug,
        is_active=True
    )
    
    # Only show public journeys in preview, or allow superuser
    if not journey.is_public:
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404("Journey not found")
    
    # Check if journey is already claimed by a real user
    is_claimed = not journey.creator.user.username.startswith('rallynex')
    
    # Get activities organized by day
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
    
    # Check if already claimed
    if not journey.creator.user.username.startswith('rallynex'):
        messages.warning(request, 'This journey has already been claimed.')
        return redirect('journey_detail', slug=slug)
    
    # Transfer ownership to the logged-in user
    profile = get_user_profile(request.user)
    journey.creator = profile
    journey.is_public = True  # Make it public when claimed
    journey.save()
    
    messages.success(request, f'🎉 You now own "{journey.title}"! Start adding more content.')
    return redirect('journey_detail', slug=slug)



def template_store_view(request):
    """Template marketplace — browse and purchase"""
    templates = JourneyTemplate.objects.filter(is_active=True)
    
    categories = {}
    for cat_key, cat_name in Journey.CATEGORY_CHOICES:
        cat_templates = templates.filter(category=cat_key)
        if cat_templates.exists():
            categories[cat_name] = {
                'key': cat_key,
                'templates': cat_templates,
            }
    
    user_journeys = []
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        user_journeys = Journey.objects.filter(creator=profile, is_active=True)
    
    context = {
        'categories': categories,
        'user_journeys': user_journeys,
    }
    
    return render(request, 'templates/store.html', context)


@login_required
def purchase_template_view(request, template_id):
    """Buy a template — apply to new or existing journey"""
    template = get_object_or_404(JourneyTemplate, id=template_id, is_active=True)
    profile = get_user_profile(request.user)
    user_journeys = Journey.objects.filter(creator=profile, is_active=True)
    
    context = {
        'template': template,
        'user_journeys': user_journeys,
        'paypal_client_id': getattr(settings, 'PAYPAL_CLIENT_ID', ''),
    }
    
    return render(request, 'templates/purchase.html', context)


@login_required
@require_POST
def apply_template_to_journey(request, template_id):
    """Apply purchased template style to an existing journey"""
    template = get_object_or_404(JourneyTemplate, id=template_id, is_active=True)
    journey_id = request.POST.get('journey_id')
    
    journey = get_object_or_404(Journey, id=journey_id, creator__user=request.user)
    
    # Update journey with template style
    journey.template_style = template.template_style
    journey.save(update_fields=['template_style', 'updated_at'])
    
    template.usage_count += 1
    template.save(update_fields=['usage_count'])
    
    messages.success(request, f'"{template.title}" style applied to "{journey.title}"!')
    return redirect('journey_detail', slug=journey.slug)

@login_required
@require_POST
def complete_template_purchase_view(request, template_id):
    """Complete purchase — create new journey with ALL activities pre-filled"""
    template = get_object_or_404(JourneyTemplate, id=template_id, is_active=True)
    profile = get_user_profile(request.user)
    
    paypal_order_id = request.POST.get('paypal_order_id')
    current_day = request.POST.get('current_day', '1').strip()
    
    if not paypal_order_id and not template.is_free:
        messages.error(request, 'Payment verification failed.')
        return redirect('purchase_template', template_id=template.id)
    
    try:
        day_override = int(current_day)
        day_override = max(1, min(day_override, template.duration))
    except (ValueError, TypeError):
        day_override = 1
    
    adjusted_start = timezone.now() - datetime.timedelta(days=day_override - 1)
    
    journey = Journey.objects.create(
        creator=profile,
        title=template.title,
        description=template.description,
        category=template.category,
        journey_type=template.journey_type,
        duration=template.duration,
        milestones=template.milestones,
        template_style=template.template_style,
        cover_image=template.cover_image if template.cover_image else None,
        current_day_override=day_override,
        start_date=adjusted_start,
        is_public=True,
        is_active=True,
        published_at=timezone.now(),
    )
    
    activities_created = 0
    if template.milestones:
        for milestone in template.milestones:
            day_num = milestone.get('day', 1)
            title_text = milestone.get('title', f'Day {day_num}')
            description = milestone.get('description', '')
            content = f"{title_text}\n\n{description}" if description else title_text
            
            activity, created = Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day_num,
                defaults={
                    'content': content,
                    'published_at': timezone.now(),
                }
            )
            if created:
                activities_created += 1
    
    template.usage_count += 1
    template.save(update_fields=['usage_count'])
    
    if activities_created > 0:
        messages.success(request, f'Journey "{journey.title}" created with all {activities_created} days pre-filled! You are on Day {day_override}.')
    else:
        messages.success(request, f'Journey "{journey.title}" created! You are on Day {day_override}.')
    
    return redirect('journey_detail', slug=journey.slug)
@login_required
@require_POST
def admin_create_journey_from_template(request, template_id):
    """Admin-only: create a journey from template without payment"""
    if not request.user.is_superuser:
        messages.error(request, 'Unauthorized.')
        return redirect('template_store')
    
    template = get_object_or_404(JourneyTemplate, id=template_id, is_active=True)
    profile = get_user_profile(request.user)
    
    custom_title = request.POST.get('title', '').strip()
    current_day = request.POST.get('current_day', '1').strip()
    
    journey_title = custom_title if custom_title else template.title
    
    try:
        day_override = int(current_day)
        day_override = max(1, min(day_override, template.duration))
    except (ValueError, TypeError):
        day_override = 1
    
    from datetime import timedelta
    adjusted_start = timezone.now() - timedelta(days=day_override - 1)
    
    journey = Journey.objects.create(
        creator=profile,
        title=journey_title,
        description=template.description,
        category=template.category,
        journey_type=template.journey_type,
        duration=template.duration,
        milestones=template.milestones,
        template_style=template.template_style,
        cover_image=template.cover_image if template.cover_image else None,
        current_day_override=day_override,
        start_date=adjusted_start,
        is_public=False,
        is_active=True,
        published_at=timezone.now(),
    )
    
    if template.milestones:
        for milestone in template.milestones:
            day_num = milestone.get('day', 1)
            title_text = milestone.get('title', f'Day {day_num}')
            description = milestone.get('description', '')
            content = f"{title_text}\n\n{description}" if description else title_text
            
            Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day_num,
                defaults={
                    'content': content,
                    'published_at': timezone.now(),
                }
            )
    
    template.usage_count += 1
    template.save(update_fields=['usage_count'])
    
    messages.success(request, f'Journey "{journey.title}" created! You are on Day {day_override}.')
    return redirect('journey_detail', slug=journey.slug)

@login_required
@require_POST
def complete_template_purchase_view(request, template_id):
    """Complete purchase — create new journey with ALL activities pre-filled"""
    template = get_object_or_404(JourneyTemplate, id=template_id, is_active=True)
    profile = get_user_profile(request.user)
    
    paypal_order_id = request.POST.get('paypal_order_id')
    custom_title = request.POST.get('custom_title', '').strip()
    current_day = request.POST.get('current_day', '1').strip()
    
    journey_title = custom_title if custom_title else template.title
    
    if not paypal_order_id and not template.is_free:
        messages.error(request, 'Payment verification failed.')
        return redirect('purchase_template', template_id=template.id)
    
    try:
        day_override = int(current_day)
        day_override = max(1, min(day_override, template.duration))
    except (ValueError, TypeError):
        day_override = 1
    
    from datetime import timedelta
    adjusted_start = timezone.now() - timedelta(days=day_override - 1)
    
    journey = Journey.objects.create(
        creator=profile,
        title=journey_title,
        description=template.description,
        category=template.category,
        journey_type=template.journey_type,
        duration=template.duration,
        milestones=template.milestones,
        template_style=template.template_style,
        cover_image=template.cover_image if template.cover_image else None,
        current_day_override=day_override,
        start_date=adjusted_start,
        is_public=True,
        is_active=True,
        published_at=timezone.now(),
    )
    
    activities_created = 0
    if template.milestones:
        for milestone in template.milestones:
            day_num = milestone.get('day', 1)
            title_text = milestone.get('title', f'Day {day_num}')
            description = milestone.get('description', '')
            content = f"{title_text}\n\n{description}" if description else title_text
            
            activity, created = Activity.objects.update_or_create(
                journey=journey,
                day_number_field=day_num,
                defaults={
                    'content': content,
                    'published_at': timezone.now(),
                }
            )
            if created:
                activities_created += 1
    
    template.usage_count += 1
    template.save(update_fields=['usage_count'])
    
    if activities_created > 0:
        messages.success(request, f'Journey "{journey.title}" created with all {activities_created} days pre-filled! You are on Day {day_override}.')
    else:
        messages.success(request, f'Journey "{journey.title}" created! You are on Day {day_override}.')
    
    return redirect('journey_detail', slug=journey.slug)


@login_required
@require_POST
def apply_template_to_journey(request, template_id):
    """Apply purchased template style to an existing journey"""
    template = get_object_or_404(JourneyTemplate, id=template_id, is_active=True)
    journey_id = request.POST.get('journey_id')
    current_day = request.POST.get('current_day', '1').strip()
    
    journey = get_object_or_404(Journey, id=journey_id, creator__user=request.user)
    
    # Update journey with template style
    journey.template_style = template.template_style
    
    # Update current day if provided
    try:
        day_override = int(current_day)
        day_override = max(1, min(day_override, journey.duration))
        journey.current_day_override = day_override
    except (ValueError, TypeError):
        pass
    
    journey.save(update_fields=['template_style', 'current_day_override', 'updated_at'])
    
    template.usage_count += 1
    template.save(update_fields=['usage_count'])
    
    messages.success(request, f'"{template.title}" style applied to "{journey.title}"!')
    return redirect('journey_detail', slug=journey.slug)


from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.models import User

class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth/password_reset.html'
    email_template_name = 'auth/password_reset_email.html'
    subject_template_name = 'auth/password_reset_subject.txt'
    success_url = '/password-reset/done/'
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"/password-reset/{uid}/{token}/"
            self.request.session['reset_link'] = reset_link
            self.request.session['reset_email'] = email
        except User.DoesNotExist:
            self.request.session['reset_link'] = None
            self.request.session['reset_email'] = email
        
        return super().form_valid(form)

from django.contrib.auth.views import PasswordResetDoneView

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'auth/password_reset_done.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reset_link'] = self.request.session.get('reset_link', None)
        context['reset_email'] = self.request.session.get('reset_email', None)
        return context