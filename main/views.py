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
from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import json
import re
import uuid
from datetime import timedelta, datetime
from django.contrib.auth import get_user_model

from .models import (
    Profile, Journey, Activity, Reflection,
    Comment, JourneyFollow, JourneySave, Tag,
    Notification, Export, ContactMessage, Subscriber,
    # Monetization Models
    SubscriptionPlan, UserSubscription, OneTimeProduct, 
    UserPurchase, PaidJourneyExport, PaidCustomTheme, 
    PaidExtraStorage, PaidAIProgressReport, PaymentTransaction,
)
from .forms import (
    SignUpForm, LoginForm, ProfileForm,
    JourneyForm, JourneySettingsForm, ActivityForm, ReflectionForm,
    CommentForm, JourneySearchForm, ExportForm, ContactForm,
    NewsletterSignupForm,
    # Monetization Forms
    SubscribeForm, PurchaseProductForm, ExportRequestForm,
    ThemeCustomizationForm, AICustomizationForm,
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
    
    journey.view_count += 1
    journey.save(update_fields=['view_count'])
    
    cache_key = f'journey_view_{journey.id}_{session_key}'
    if not cache.get(cache_key):
        journey.unique_viewers += 1
        journey.save(update_fields=['unique_viewers'])
        cache.set(cache_key, True, 3600)


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
            messages.success(request, f'Welcome to Rallynex, {user.username}! 🚀')
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
            messages.success(request, f'Welcome back, {user.username}! 👋')
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
# PUBLIC VIEWS - BUILD IN PUBLIC FOCUS
# ============================================================================

def landing_view(request):
    """Landing page — Build in Public focus"""
    featured_journeys = Journey.objects.filter(
        privacy_status='public',
        is_active=True,
        is_featured=True
    ).select_related('creator__user').prefetch_related('activities')[:6]
    
    recent_journeys = Journey.objects.filter(
        privacy_status='public',
        is_active=True
    ).order_by('-created_at')[:6]
    
    public_journeys = Journey.objects.filter(privacy_status='public', is_active=True)
    
    context = {
        'featured_journeys': featured_journeys,
        'recent_journeys': recent_journeys,
        'total_public_journeys': public_journeys.count(),
        'total_activities': Activity.objects.filter(journey__privacy_status='public').count(),
        'total_builders': User.objects.filter(profile__journeys__isnull=False).distinct().count(),
        'total_followers': JourneyFollow.objects.count(),
    }
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            user_journeys = Journey.objects.filter(creator=profile, is_active=True)
            context.update({
                'user_journeys': user_journeys[:3],
                'user_journey_count': user_journeys.count(),
                'user_following': JourneyFollow.objects.filter(user=request.user).count(),
                'user_notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
            })
        except Profile.DoesNotExist:
            pass
    
    return render(request, 'landing.html', context)


def discover_view(request):
    """Browse and discover public journeys"""
    # Get parameters
    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '')
    selected_journey_type = request.GET.get('journey_type', '')
    selected_sort = request.GET.get('sort', '-created_at')
    
    # Base queryset
    journeys = Journey.objects.filter(
        privacy_status='public', 
        is_active=True
    ).select_related('creator__user').prefetch_related('activities')
    
    # Apply search
    if search_query:
        journeys = journeys.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(creator__user__username__icontains=search_query)
        )
    
    # Apply category
    if selected_category:
        journeys = journeys.filter(category=selected_category)
    
    # Apply journey type
    if selected_journey_type:
        journeys = journeys.filter(journey_type=selected_journey_type)
    
    # ✅ THIS IS WHERE THE SORT HAPPENS
    sort_mapping = {
        '-created_at': '-created_at',
        'created_at': 'created_at',
        '-view_count': '-view_count',
        'view_count': 'view_count',
        '-follower_count': '-follower_count',
        'follower_count': 'follower_count',
        'title': 'title',
        '-title': '-title',
    }
    
    if selected_sort in sort_mapping:
        journeys = journeys.order_by(sort_mapping[selected_sort])
    else:
        journeys = journeys.order_by('-created_at')
    
    # Log the sort for debugging
    print(f"📊 Sorting by: {selected_sort}")
    print(f"📊 Total journeys: {journeys.count()}")
    
    # Pagination
    paginator = Paginator(journeys, 12)
    page = request.GET.get('page', 1)
    
    try:
        journeys_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        journeys_page = paginator.page(1)
    
    context = {
        'journeys': journeys_page,
        'total_count': journeys.count(),
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_journey_type': selected_journey_type,
        'selected_sort': selected_sort,  # ← THIS MUST BE HERE
        'categories': Journey.CATEGORY_CHOICES,
        'journey_types': Journey.JOURNEY_TYPES,
    }
    
    return render(request, 'discover.html', context)



def journey_detail_view(request, slug):
    """View a single journey with all its entries"""
    journey_qs = Journey.objects.select_related('creator__user').prefetch_related(
        'activities', 
        'followers',
        'comments',
        'reflections'
    ).filter(slug=slug, is_active=True)
    
    journey = get_object_or_404(journey_qs)
    
    if journey.privacy_status != 'public':
        if not request.user.is_authenticated or (request.user != journey.creator.user and not request.user.is_superuser):
            raise Http404("Journey not found")
    
    track_journey_view(request, journey)
    activities_by_day = journey.get_all_activities_by_day()
    current_day = journey.get_current_day()
    current_activity = activities_by_day.get(current_day)
    
    if request.user.is_authenticated and request.user == journey.creator.user:
        reflections = Reflection.objects.filter(
            related_journey=journey
        ).order_by('-created_at')[:10]
    else:
        reflections = Reflection.objects.filter(
            related_journey=journey,
            is_private=False
        ).order_by('-created_at')[:10]
    
    is_following = False
    is_saved = False
    if request.user.is_authenticated:
        is_following = JourneyFollow.objects.filter(user=request.user, journey=journey).exists()
        is_saved = JourneySave.objects.filter(user=request.user, journey=journey).exists()
    
    recent_comments = Comment.objects.filter(
        journey=journey
    ).select_related('user').order_by('-created_at')[:10]
    
    related_journeys = Journey.objects.filter(
        category=journey.category,
        privacy_status='public',
        is_active=True
    ).exclude(id=journey.id).order_by('-view_count')[:4]
    
    has_subscription = False
    has_export_purchase = False
    has_theme_purchase = False
    has_ai_report_purchase = False
    existing_export = None
    
    if request.user.is_authenticated:
        has_subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            end_date__gt=timezone.now()
        ).exists()
        
        has_export_purchase = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='export',
            status='completed'
        ).exists()
        
        has_theme_purchase = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='theme',
            status='completed'
        ).exists()
        
        has_ai_report_purchase = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='ai_report',
            status='completed'
        ).exists()
        
        existing_export = PaidJourneyExport.objects.filter(
            user=request.user,
            journey=journey
        ).first()
    
    # Apply theme
    theme_css = ""
    if hasattr(journey, 'theme_settings') and journey.theme_settings:
        try:
            from .services.customization_service import CustomizationService
            theme_css = CustomizationService.generate_css(journey)
        except:
            pass
    
    context = {
        'theme_css': theme_css,
        'journey': journey,
        'activities_by_day': activities_by_day,
        'current_day': current_day,
        'current_activity': current_activity,
        'reflections': reflections,
        'is_following': is_following,
        'is_saved': is_saved,
        'recent_comments': recent_comments,
        'related_journeys': related_journeys,
        'total_days_range': range(1, journey.duration + 1),
        'has_subscription': has_subscription,
        'has_export_purchase': has_export_purchase,
        'has_theme_purchase': has_theme_purchase,
        'has_ai_report_purchase': has_ai_report_purchase,
        'existing_export': existing_export,
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
        privacy_status='public',
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
        'total_journeys': journeys.count(),
        'total_followers': JourneyFollow.objects.filter(journey__creator=profile).count(),
        'total_activities': Activity.objects.filter(journey__creator=profile).count(),
    }
    
    return render(request, 'creator/profile.html', context)


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def dashboard_view(request):
    """User dashboard with monetization info"""
    profile = get_user_profile(request.user)
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    subscription_features = {}
    if has_subscription:
        subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            end_date__gt=timezone.now()
        ).first()
        subscription_features = subscription.get_features() if subscription else {}
    
    has_export = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='export',
        status='completed'
    ).exists()
    has_theme = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='theme',
        status='completed'
    ).exists()
    has_ai_report = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='ai_report',
        status='completed'
    ).exists()
    has_storage = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='storage',
        status='completed'
    ).exists()
    
    total_journeys = journeys.count()
    active_journeys = journeys.filter(is_active=True).count()
    total_entries = Activity.objects.filter(journey__creator=profile).count()
    total_reflections = Reflection.objects.filter(user=request.user).count()
    
    try:
        total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    except:
        total_views = 0
    
    recent_reflections = Reflection.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    recent_activities = Activity.objects.filter(
        journey__creator=profile
    ).order_by('-created_at')[:10]
    
    recent_comments = Comment.objects.filter(
        journey__creator=profile
    ).order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'journeys': journeys[:5],
        'total_journeys': total_journeys,
        'active_journeys': active_journeys,
        'total_entries': total_entries,
        'total_reflections': total_reflections,
        'total_views': total_views,
        'recent_activities': recent_activities,
        'recent_comments': recent_comments,
        'recent_reflections': recent_reflections,
        'has_subscription': has_subscription,
        'subscription_features': subscription_features,
        'has_export': has_export,
        'has_theme': has_theme,
        'has_ai_report': has_ai_report,
        'has_storage': has_storage,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def my_journeys_view(request):
    """List all user's journeys"""
    profile = get_user_profile(request.user)
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    active_count = journeys.filter(is_active=True).count()
    total_entries = Activity.objects.filter(journey__creator=profile).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    for journey in journeys:
        journey.activity_count = journey.activities.count()
        journey.follower_count = journey.followers.count()
        journey.reflection_count = journey.reflections.count()
    
    context = {
        'journeys': journeys,
        'active_count': active_count,
        'total_entries': total_entries,
        'total_views': total_views,
        'total_followers': total_followers,
    }
    
    return render(request, 'dashboard/journeys.html', context)


# ============================================================================
# JOURNEY CRUD VIEWS
# ============================================================================

@login_required
def create_journey_view(request):
    """Create a new build in public journey"""
    profile = get_user_profile(request.user)
    
    if request.method == 'POST':
        form = JourneyForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                journey = form.save(commit=False)
                journey.creator = profile
                journey.save()
                form.save()
                
                messages.success(request, f'🚀 Journey "{journey.title}" created successfully!')
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
            messages.success(request, f'📝 Journey "{journey.title}" updated!')
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
        form = JourneySettingsForm(request.POST, instance=journey)
        if form.is_valid():
            form.save()
            messages.success(request, '⚙️ Settings updated!')
            return redirect('my_journeys')
    else:
        form = JourneySettingsForm(instance=journey)
    
    context = {
        'journey': journey,
        'form': form,
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
# ACTIVITY / ENTRY VIEWS
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
        'total_entries': journey.activities.count(),
    }
    
    return render(request, 'dashboard/content_manager.html', context)
@login_required
def create_activity_view(request, slug, day_number=None):
    """Create or edit an activity for a specific day"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if day_number is None:
        day_number = journey.get_current_day()
    
    existing_activity = journey.get_activity_for_day(day_number)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()  # ✅ timezone is already imported at the top
    ).exists()
    
    if request.method == 'POST':
        form = ActivityForm(
            request.POST, 
            request.FILES, 
            journey=journey, 
            day_number=day_number,
            instance=existing_activity
        )
        
        if form.is_valid():
            try:
                activity = form.save(commit=False)
                activity.journey = journey
                if not activity.day_number_field:
                    activity.day_number_field = day_number
                
                # ✅ Set default values for all required fields
                # Source URL
                if not getattr(activity, 'source_url', None):
                    activity.source_url = ''
                
                # View count
                if not getattr(activity, 'view_count', None):
                    activity.view_count = 0
                
                # Unique viewers (if exists)
                if hasattr(activity, 'unique_viewers') and activity.unique_viewers is None:
                    activity.unique_viewers = 0
                
                # Published at (if exists)
                if hasattr(activity, 'published_at') and activity.published_at is None:
                    activity.published_at = timezone.now()  # ✅ Use timezone directly
                
                activity.save()
                
                messages.success(request, f'✅ Entry saved for Day {day_number}!')
                return redirect('journey_content', slug=slug)
            except Exception as e:
                messages.error(request, f'Error saving entry: {str(e)}')
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Activity save error: {e}", exc_info=True)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ActivityForm(
            journey=journey,
            day_number=day_number,
            instance=existing_activity
        )
    
    context = {
        'journey': journey,
        'day_number': day_number,
        'existing_activity': existing_activity,
        'form': form,
        'CLOUDINARY_CLOUD_NAME': settings.CLOUDINARY_CLOUD_NAME,
        'is_editing': existing_activity is not None,
        'has_subscription': has_subscription,
    }
    
    return render(request, 'dashboard/activity_form.html', context)
@login_required
def edit_activity_view(request, slug, day_number):
    """Edit an existing activity"""
    return create_activity_view(request, slug, day_number)


@login_required
def delete_activity_view(request, slug, day_number):
    """Delete an activity"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    activity = get_object_or_404(Activity, journey=journey, day_number_field=day_number)
    
    if request.method == 'POST':
        activity.delete()
        messages.success(request, f'Day {day_number} content deleted.')
        return redirect('journey_content', slug=slug)
    
    context = {
        'journey': journey,
        'activity': activity,
        'day_number': day_number,
    }
    
    return render(request, 'dashboard/activity_confirm_delete.html', context)


# ============================================================================
# REFLECTION VIEWS
# ============================================================================

@login_required
def reflection_view(request):
    """View all reflections"""
    reflections = Reflection.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    paginator = Paginator(reflections, 20)
    page = request.GET.get('page')
    
    try:
        reflections_page = paginator.page(page)
    except PageNotAnInteger:
        reflections_page = paginator.page(1)
    except EmptyPage:
        reflections_page = paginator.page(paginator.num_pages)
    
    context = {
        'reflections': reflections_page,
        'total_reflections': reflections.count(),
    }
    
    return render(request, 'dashboard/reflections.html', context)


@login_required
def create_reflection_view(request):
    """Create a new reflection"""
    if request.method == 'POST':
        form = ReflectionForm(request.POST, user=request.user)
        if form.is_valid():
            reflection = form.save(commit=False)
            reflection.user = request.user
            reflection.save()
            messages.success(request, '💭 Reflection saved!')
            return redirect('reflection_view')
    else:
        form = ReflectionForm(user=request.user)
    
    context = {
        'form': form,
        'is_editing': False,
    }
    
    return render(request, 'dashboard/reflection_form.html', context)


@login_required
def edit_reflection_view(request, pk):
    """Edit a reflection"""
    reflection = get_object_or_404(Reflection, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ReflectionForm(request.POST, user=request.user, instance=reflection)
        if form.is_valid():
            form.save()
            messages.success(request, '💭 Reflection updated!')
            return redirect('reflection_view')
    else:
        form = ReflectionForm(user=request.user, instance=reflection)
    
    context = {
        'form': form,
        'is_editing': True,
        'reflection': reflection,
    }
    
    return render(request, 'dashboard/reflection_form.html', context)


@login_required
def delete_reflection_view(request, pk):
    """Delete a reflection"""
    reflection = get_object_or_404(Reflection, pk=pk, user=request.user)
    
    if request.method == 'POST':
        reflection.delete()
        messages.success(request, 'Reflection deleted.')
        return redirect('reflection_view')
    
    context = {
        'reflection': reflection,
    }
    
    return render(request, 'dashboard/reflection_confirm_delete.html', context)


def reflection_detail_view(request, pk):
    """View a single reflection"""
    reflection = get_object_or_404(Reflection, pk=pk)
    
    if reflection.is_private:
        if not request.user.is_authenticated or request.user != reflection.user:
            raise Http404("This reflection is private.")
    
    context = {
        'reflection': reflection,
    }
    
    return render(request, 'dashboard/reflection_detail.html', context)


# ============================================================================
# EXPORT VIEWS
# ============================================================================

@login_required
def export_journey_view(request, slug):
    """Export a journey as PDF, Markdown, etc."""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            export = form.save(commit=False)
            export.user = request.user
            export.journey = journey
            export.status = 'pending'
            export.save()
            
            messages.success(request, f'📄 Export started! Your {export.get_format_display()} file will be ready soon.')
            return redirect('my_journeys')
    else:
        form = ExportForm()
    
    context = {
        'journey': journey,
        'form': form,
        'existing_exports': Export.objects.filter(journey=journey, user=request.user).order_by('-requested_at'),
    }
    
    return render(request, 'dashboard/export_journey.html', context)


@login_required
def download_export_view(request, export_id):
    """Download an exported file"""
    export = get_object_or_404(Export, id=export_id, user=request.user)
    
    if export.status != 'completed' or not export.file_url:
        messages.error(request, 'Export not ready yet.')
        return redirect('my_journeys')
    
    return redirect(export.file_url)


# ============================================================================
# FOLLOW & SAVE VIEWS
# ============================================================================

@login_required
def follow_journey_view(request, slug):
    """Follow/unfollow a journey"""
    journey = get_object_or_404(Journey, slug=slug)
    
    if request.method == 'POST':
        form = FollowForm(request.POST)
        if form.is_valid():
            follow, created = JourneyFollow.objects.get_or_create(
                user=request.user,
                journey=journey
            )
            
            if not created:
                follow.delete()
                following = False
            else:
                follow.notify_on_new_entry = form.cleaned_data.get('notify_on_new_entry', True)
                follow.notify_on_completion = form.cleaned_data.get('notify_on_completion', True)
                follow.save()
                following = True
            
            return JsonResponse({
                'following': following,
                'follower_count': journey.followers.count(),
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def save_journey_view(request, slug):
    """Save/unsave a journey"""
    journey = get_object_or_404(Journey, slug=slug)
    
    saved, created = JourneySave.objects.get_or_create(user=request.user, journey=journey)
    
    if not created:
        saved.delete()
        is_saved = False
    else:
        is_saved = True
    
    return JsonResponse({
        'saved': is_saved,
        'save_count': journey.saves.count(),
    })


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
# COMMENT VIEWS
# ============================================================================

@login_required
def comment_journey_view(request, slug):
    """Add a comment to a journey"""
    journey = get_object_or_404(Journey, slug=slug)
    
    if not journey.allow_comments:
        messages.error(request, 'Comments are not allowed on this journey.')
        return redirect('journey_detail', slug=slug)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.journey = journey
            comment.save()
            
            messages.success(request, '💬 Comment added!')
        else:
            messages.error(request, 'Please enter a valid comment.')
    
    return redirect('journey_detail', slug=slug)


@login_required
def comment_activity_view(request, slug, day_number):
    """Add a comment to an activity"""
    journey = get_object_or_404(Journey, slug=slug)
    activity = get_object_or_404(Activity, journey=journey, day_number_field=day_number)
    
    if not journey.allow_comments:
        messages.error(request, 'Comments are not allowed on this journey.')
        return redirect('journey_detail', slug=slug)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.activity = activity
            comment.save()
            
            messages.success(request, '💬 Comment added!')
        else:
            messages.error(request, 'Please enter a valid comment.')
    
    return redirect('journey_detail', slug=slug)


@login_required
def delete_comment_view(request, comment_id):
    """Delete a comment"""
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    
    journey_slug = comment.journey.slug if comment.journey else None
    
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted.')
    
    if journey_slug:
        return redirect('journey_detail', slug=journey_slug)
    
    return redirect('dashboard')


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
            messages.success(request, '👤 Profile updated successfully!')
            return redirect('profile_settings')
    else:
        form = ProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
        'CLOUDINARY_CLOUD_NAME': settings.CLOUDINARY_CLOUD_NAME,
    }
    
    return render(request, 'dashboard/profile_settings.html', context)


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
        'unread_count': notifications.filter(is_read=False).count(),
    }
    
    return render(request, 'dashboard/notifications.html', context)


@login_required
def mark_notification_read_view(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@login_required
def mark_all_notifications_read_view(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
def unread_notification_count(request):
    """API endpoint for unread notification count"""
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0})
    
    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'unread_count': unread_count})
    except Exception:
        return JsonResponse({'unread_count': 0})


# ============================================================================
# CONTACT VIEWS
# ============================================================================

def contact_view(request):
    """Contact form with AI response"""
    try:
        from .services.faq_service import get_ai_response
    except:
        def get_ai_response(msg, name):
            return f"Thank you for your message, {name}! We'll get back to you soon."

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
        
        ai_response = get_ai_response(message, name)
        
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


def newsletter_signup_view(request):
    """Newsletter signup"""
    if request.method == 'POST':
        form = NewsletterSignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            subscriber, created = Subscriber.objects.get_or_create(
                email=email
            )
            if created:
                messages.success(request, '📬 You\'re subscribed!')
            else:
                messages.info(request, 'You\'re already subscribed.')
            return redirect('landing')
    else:
        form = NewsletterSignupForm()
    
    return render(request, 'newsletter_signup.html', {'form': form})


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
# THEME TOGGLE
# ============================================================================

@require_POST
def toggle_theme(request):
    """Toggle dark/light theme"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        response = JsonResponse({'success': True, 'theme': theme})
        response.set_cookie('theme', theme, max_age=365*24*60*60, httponly=True, samesite='Lax')
        return response
    except:
        return JsonResponse({'success': False}, status=400)


@login_required
def toolbox_view(request):
    """Creator Toolbox - Central hub for all tools"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile)
    total_journeys = journeys.count()
    total_entries = Activity.objects.filter(journey__creator=profile).count()
    total_reflections = Reflection.objects.filter(user=request.user).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    context = {
        'profile': profile,
        'total_journeys': total_journeys,
        'total_entries': total_entries,
        'total_reflections': total_reflections,
        'total_views': total_views,
        'total_followers': total_followers,
        'recent_activities': Activity.objects.filter(journey__creator=profile).order_by('-created_at')[:5],
        'recent_reflections': Reflection.objects.filter(user=request.user).order_by('-created_at')[:5],
    }
    
    return render(request, 'toolbox/index.html', context)


# ============================================================================
# MONETIZATION VIEWS - SUBSCRIPTION
# ============================================================================

@login_required
def subscription_plans(request):
    """View all subscription plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    current_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).first()
    
    context = {
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'main/subscription_plans.html', context)


@login_required
def subscribe(request, plan_id):
    """Subscribe to a plan"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    existing = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).first()
    
    if existing:
        messages.warning(request, 'You already have an active subscription.')
        return redirect('subscription_plans')
    
    if request.method == 'POST':
        with transaction.atomic():
            subscription = UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                status='pending',
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=30 if plan.plan_type == 'monthly' else 365),
            )
            
            PaymentTransaction.objects.create(
                user=request.user,
                subscription=subscription,
                paypal_transaction_id=f'PAYPAL_{uuid.uuid4().hex[:10]}',
                amount=plan.price,
                transaction_type='subscription',
                description=f'Subscription to {plan.name}',
                is_successful=True,
            )
            
            messages.success(request, f'You have subscribed to {plan.name}!')
            return redirect('subscription_success')
    
    context = {
        'plan': plan,
    }
    return render(request, 'main/subscribe.html', context)


@login_required
def subscription_success(request):
    """Subscription success page"""
    return render(request, 'main/subscription_success.html')


@login_required
def cancel_subscription(request, subscription_id):
    """Cancel a subscription"""
    subscription = get_object_or_404(
        UserSubscription,
        id=subscription_id,
        user=request.user,
        status='active'
    )
    
    if request.method == 'POST':
        subscription.status = 'canceled'
        subscription.cancel_date = timezone.now()
        subscription.save()
        
        messages.success(request, 'Your subscription has been canceled.')
        return redirect('subscription_plans')
    
    return render(request, 'main/cancel_subscription.html', {'subscription': subscription})


# ============================================================================
# MONETIZATION VIEWS - ONE-TIME PURCHASES
# ============================================================================

@login_required
def product_list(request):
    """View all one-time products"""
    products = OneTimeProduct.objects.filter(is_active=True)
    user_purchases = UserPurchase.objects.filter(
        user=request.user,
        status='completed'
    ).values_list('product_id', flat=True)
    
    context = {
        'products': products,
        'user_purchases': user_purchases,
    }
    return render(request, 'main/product_list.html', context)


@login_required
def purchase_product(request, product_id):
    """Purchase a one-time product"""
    product = get_object_or_404(OneTimeProduct, id=product_id, is_active=True)
    
    existing = UserPurchase.objects.filter(
        user=request.user,
        product=product,
        status='completed'
    ).first()
    
    if existing and product.payment_type != 'monthly':
        messages.warning(request, 'You already purchased this product.')
        return redirect('product_list')
    
    if request.method == 'POST':
        form = PurchaseProductForm(request.user, request.POST)
        if form.is_valid():
            with transaction.atomic():
                purchase = UserPurchase.objects.create(
                    user=request.user,
                    product=product,
                    amount_paid=product.price_min,
                    status='pending',
                )
                
                journey_id = form.cleaned_data.get('journey_id')
                if journey_id and product.product_type == 'export':
                    journey = get_object_or_404(Journey, id=journey_id, creator=request.user.profile)
                    PaidJourneyExport.objects.create(
                        user=request.user,
                        journey=journey,
                        purchase=purchase,
                        format='pdf',
                    )
                    
                elif journey_id and product.product_type == 'ai_report':
                    journey = get_object_or_404(Journey, id=journey_id, creator=request.user.profile)
                    PaidAIProgressReport.objects.create(
                        user=request.user,
                        journey=journey,
                        purchase=purchase,
                        report_title=f"Progress Report - {journey.title}",
                        report_content="Report generation pending...",
                        status='pending'
                    )
                
                PaymentTransaction.objects.create(
                    user=request.user,
                    purchase=purchase,
                    paypal_transaction_id=f'PAYPAL_{uuid.uuid4().hex[:10]}',
                    amount=product.price_min,
                    transaction_type='purchase',
                    description=f'Purchase of {product.name}',
                    is_successful=True,
                )
                
                messages.success(request, f'You purchased {product.name}!')
                return redirect('purchase_success', purchase_id=purchase.id)
    else:
        form = PurchaseProductForm(request.user)
    
    context = {
        'product': product,
        'form': form,
    }
    return render(request, 'main/purchase_product.html', context)


@login_required
def purchase_success(request, purchase_id):
    """Purchase success page"""
    purchase = get_object_or_404(UserPurchase, id=purchase_id, user=request.user)
    return render(request, 'main/purchase_success.html', {'purchase': purchase})


# ============================================================================
# MONETIZATION VIEWS - EXPORT
# ============================================================================

@login_required
def request_export(request, journey_id):
    """Request a journey export"""
    journey = get_object_or_404(Journey, id=journey_id, creator=request.user.profile)
    
    has_purchase = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='export',
        status='completed'
    ).exists()
    
    if not has_purchase:
        messages.warning(request, 'You need to purchase export feature first.')
        return redirect('product_list')
    
    existing = PaidJourneyExport.objects.filter(
        user=request.user,
        journey=journey
    ).first()
    
    if request.method == 'POST':
        form = ExportRequestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                if existing:
                    existing.format = form.cleaned_data['format']
                    existing.include_media = form.cleaned_data['include_media']
                    existing.include_reflections = form.cleaned_data['include_reflections']
                    existing.include_comments = form.cleaned_data['include_comments']
                    existing.expires_at = timezone.now() + timezone.timedelta(days=7)
                    existing.save()
                else:
                    existing = PaidJourneyExport.objects.create(
                        user=request.user,
                        journey=journey,
                        purchase=UserPurchase.objects.filter(
                            user=request.user,
                            product__product_type='export',
                            status='completed'
                        ).first(),
                        format=form.cleaned_data['format'],
                        include_media=form.cleaned_data['include_media'],
                        include_reflections=form.cleaned_data['include_reflections'],
                        include_comments=form.cleaned_data['include_comments'],
                        expires_at=timezone.now() + timezone.timedelta(days=7),
                    )
                
                messages.success(request, 'Export request submitted!')
                return redirect('export_download', export_id=existing.id)
    else:
        form = ExportRequestForm(instance=existing)
    
    context = {
        'journey': journey,
        'form': form,
        'export': existing,
    }
    return render(request, 'main/request_export.html', context)


@login_required
def export_download(request, export_id):
    """Download a journey export"""
    export = get_object_or_404(PaidJourneyExport, id=export_id, user=request.user)
    
    if not export.is_valid():
        messages.error(request, 'Export has expired or is not available.')
        return redirect('request_export', journey_id=export.journey.id)
    
    export.is_downloaded = True
    export.download_count += 1
    export.downloaded_at = timezone.now()
    export.save()
    
    messages.success(request, 'Your export is being generated.')
    return render(request, 'main/export_download.html', {'export': export})


# ============================================================================
# MONETIZATION VIEWS - THEME
# ============================================================================

@login_required
def theme_customization(request, journey_id):
    """Customize a journey theme"""
    journey = get_object_or_404(Journey, id=journey_id, creator=request.user.profile)
    
    has_purchase = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='theme',
        status='completed'
    ).exists()
    
    if not has_purchase:
        messages.warning(request, 'You need to purchase theme customization first.')
        return redirect('product_list')
    
    theme, created = PaidCustomTheme.objects.get_or_create(
        user=request.user,
        defaults={
            'name': f'{journey.title} Theme',
            'theme_type': 'custom',
            'purchase': UserPurchase.objects.filter(
                user=request.user,
                product__product_type='theme',
                status='completed'
            ).first()
        }
    )
    
    if request.method == 'POST':
        form = ThemeCustomizationForm(request.POST, instance=theme)
        if form.is_valid():
            theme = form.save(commit=False)
            theme.user = request.user
            theme.save()
            messages.success(request, 'Theme updated successfully!')
            return redirect('journey_detail', slug=journey.slug)
    else:
        form = ThemeCustomizationForm(instance=theme)
    
    context = {
        'journey': journey,
        'form': form,
        'theme': theme,
    }
    return render(request, 'main/theme_customization.html', context)


@login_required
def apply_theme(request, theme_id):
    """Apply a theme to all user's journeys"""
    theme = get_object_or_404(PaidCustomTheme, id=theme_id, user=request.user)
    
    PaidCustomTheme.objects.filter(user=request.user, is_default=True).update(is_default=False)
    theme.is_default = True
    theme.save()
    
    messages.success(request, 'Theme applied successfully!')
    return redirect('dashboard')


# ============================================================================
# MONETIZATION VIEWS - AI REPORT
# ============================================================================

@login_required
def generate_ai_report(request, journey_id):
    """Generate an AI progress report"""
    journey = get_object_or_404(Journey, id=journey_id, creator=request.user.profile)
    
    has_purchase = UserPurchase.objects.filter(
        user=request.user,
        product__product_type='ai_report',
        status='completed'
    ).exists()
    
    if not has_purchase:
        messages.warning(request, 'You need to purchase AI Report feature first.')
        return redirect('product_list')
    
    existing = PaidAIProgressReport.objects.filter(
        user=request.user,
        journey=journey,
        status='completed'
    ).order_by('-created_at').first()
    
    if existing and existing.is_valid():
        messages.info(request, 'You already have a valid report for this journey.')
        return redirect('view_ai_report', report_id=existing.id)
    
    if request.method == 'POST':
        form = AICustomizationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                report = PaidAIProgressReport.objects.create(
                    user=request.user,
                    journey=journey,
                    purchase=UserPurchase.objects.filter(
                        user=request.user,
                        product__product_type='ai_report',
                        status='completed'
                    ).first(),
                    report_title=form.cleaned_data['report_title'],
                    report_content="Generating report...",
                    status='generating',
                )
                
                messages.success(request, 'Your AI report is being generated. You will be notified when ready.')
                return redirect('view_ai_report', report_id=report.id)
    else:
        form = AICustomizationForm()
    
    context = {
        'journey': journey,
        'form': form,
        'existing_report': existing,
    }
    return render(request, 'main/generate_ai_report.html', context)


@login_required
def view_ai_report(request, report_id):
    """View an AI progress report"""
    report = get_object_or_404(PaidAIProgressReport, id=report_id, user=request.user)
    
    if report.status == 'generating':
        messages.info(request, 'Your report is still being generated. Please refresh in a few moments.')
    elif report.status == 'failed':
        messages.error(request, f"Report generation failed: {report.error_message}")
    
    context = {
        'report': report,
    }
    return render(request, 'main/view_ai_report.html', context)


# ============================================================================
# MONETIZATION VIEWS - STORAGE
# ============================================================================

@login_required
def storage_dashboard(request):
    """View storage usage and management"""
    user = request.user
    
    total_storage = 50  # Default free storage
    used_storage = 0
    
    subscription = UserSubscription.objects.filter(
        user=user,
        status='active',
        end_date__gt=timezone.now()
    ).first()
    
    if subscription:
        total_storage += subscription.plan.storage_limit_mb
    
    extra_storage = PaidExtraStorage.objects.filter(
        user=user,
        is_active=True
    )
    
    for storage in extra_storage:
        if storage.is_valid():
            total_storage += storage.total_mb
            used_storage += storage.used_mb
    
    storage_purchases = UserPurchase.objects.filter(
        user=user,
        product__product_type='storage',
        status='completed'
    )
    
    context = {
        'total_storage': total_storage,
        'used_storage': used_storage,
        'available_storage': total_storage - used_storage,
        'percentage_used': (used_storage / total_storage * 100) if total_storage > 0 else 0,
        'subscription': subscription,
        'storage_purchases': storage_purchases,
        'extra_storage': extra_storage,
    }
    return render(request, 'main/storage_dashboard.html', context)


# ============================================================================
# MONETIZATION VIEWS - DASHBOARD
# ============================================================================

@login_required
def subscription_dashboard(request):
    """User subscription and purchase dashboard"""
    user = request.user
    
    subscription = UserSubscription.objects.filter(
        user=user,
        status='active',
        end_date__gt=timezone.now()
    ).first()
    
    recent_purchases = UserPurchase.objects.filter(
        user=user,
        status='completed'
    ).order_by('-purchased_at')[:10]
    
    recent_exports = PaidJourneyExport.objects.filter(
        user=user
    ).order_by('-created_at')[:10]
    
    ai_reports = PaidAIProgressReport.objects.filter(
        user=user
    ).order_by('-created_at')[:10]
    
    storage_info = {
        'total': 50,
        'used': 0,
    }
    
    if subscription:
        storage_info['total'] += subscription.plan.storage_limit_mb
    
    context = {
        'subscription': subscription,
        'recent_purchases': recent_purchases,
        'recent_exports': recent_exports,
        'ai_reports': ai_reports,
        'storage_info': storage_info,
        'has_subscription': bool(subscription),
    }
    return render(request, 'main/subscription_dashboard.html', context)


# ============================================================================
# PAYPAL WEBHOOK
# ============================================================================

@csrf_exempt
def paypal_webhook(request):
    """Handle PayPal webhook notifications"""
    try:
        data = json.loads(request.body)
        event_type = data.get('event_type')
        
        if event_type == 'PAYMENT.SALE.COMPLETED':
            transaction_id = data.get('resource', {}).get('id')
            pass
        
        elif event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
            subscription_id = data.get('resource', {}).get('id')
            pass
        
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            subscription_id = data.get('resource', {}).get('id')
            pass
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ============================================================================
# TEMPLATE CONTEXT PROCESSOR
# ============================================================================

def monetization_context(request):
    """Add monetization info to all templates"""
    context = {}
    
    if request.user.is_authenticated:
        has_subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            end_date__gt=timezone.now()
        ).exists()
        
        context['has_subscription'] = has_subscription
        
        context['has_export'] = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='export',
            status='completed'
        ).exists()
        context['has_theme'] = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='theme',
            status='completed'
        ).exists()
        context['has_ai_report'] = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='ai_report',
            status='completed'
        ).exists()
        context['has_storage'] = UserPurchase.objects.filter(
            user=request.user,
            product__product_type='storage',
            status='completed'
        ).exists()
    
    return context


# ============================================================================
# ANALYTICS VIEWS
# ============================================================================

@login_required
def journey_analytics(request, slug):
    """View advanced analytics for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    if not has_subscription:
        messages.warning(request, '📊 Upgrade to Premium to access advanced analytics.')
        return redirect('subscription_plans')
    
    analytics = {
        'total_views': journey.view_count,
        'unique_viewers': journey.unique_viewers,
        'follower_count': journey.follower_count,
        'total_entries': journey.activities.count(),
        'progress_percentage': journey.get_progress_percentage(),
        'current_day': journey.get_current_day(),
    }
    
    context = {
        'journey': journey,
        'analytics': analytics,
        'has_subscription': has_subscription,
    }
    
    return render(request, 'journey/analytics.html', context)


@login_required
def journey_metrics(request, slug):
    """View custom metrics for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    if not has_subscription:
        messages.warning(request, '📊 Upgrade to Premium to use custom metrics.')
        return redirect('subscription_plans')
    
    metrics_data = {}
    for activity in journey.activities.all():
        if activity.custom_metrics:
            for key, value in activity.custom_metrics.items():
                if key not in metrics_data:
                    metrics_data[key] = []
                metrics_data[key].append({
                    'day': activity.day_number_field,
                    'value': value
                })
    
    available_metrics = list(metrics_data.keys())
    selected_metric = request.GET.get('metric')
    
    chart_data = None
    stats = None
    if selected_metric and selected_metric in available_metrics:
        values = [item['value'] for item in metrics_data[selected_metric]]
        chart_data = {
            'labels': [item['day'] for item in metrics_data[selected_metric]],
            'values': values,
        }
        stats = {
            'count': len(values),
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'avg': sum(values) / len(values) if values else None,
            'latest': values[-1] if values else None,
        }
    
    context = {
        'journey': journey,
        'metrics_data': metrics_data,
        'available_metrics': available_metrics,
        'selected_metric': selected_metric,
        'chart_data': json.dumps(chart_data) if chart_data else None,
        'stats': stats,
        'has_subscription': has_subscription,
    }
    
    return render(request, 'journey/metrics.html', context)


@login_required
def add_metric_entry(request, slug, day_number):
    """Add or update custom metrics for a specific day"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    activity = get_object_or_404(Activity, journey=journey, day_number_field=day_number)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    if not has_subscription:
        return JsonResponse({'error': 'Premium feature'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            metric_key = data.get('metric')
            metric_value = data.get('value')
            
            if not metric_key or metric_value is None:
                return JsonResponse({'error': 'Invalid data'}, status=400)
            
            if not activity.custom_metrics:
                activity.custom_metrics = {}
            
            activity.custom_metrics[metric_key] = metric_value
            activity.save()
            
            return JsonResponse({
                'success': True,
                'message': f'{metric_key} updated to {metric_value}'
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)


# ============================================================================
# GOALS & MILESTONES VIEWS
# ============================================================================

@login_required
def journey_goals(request, slug):
    """View and manage goals for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    if not has_subscription:
        messages.warning(request, '🎯 Upgrade to Premium to use Goals & Milestones.')
        return redirect('subscription_plans')
    
    goals = []
    milestones = []
    
    for activity in journey.activities.all():
        if activity.activity_type == 'milestone':
            milestones.append({
                'day': activity.day_number_field,
                'title': activity.title or 'Milestone',
                'content': activity.content[:100],
            })
        
        if activity.custom_metrics and 'goal' in activity.custom_metrics:
            goals.append({
                'day': activity.day_number_field,
                'metric': activity.custom_metrics.get('goal_metric', ''),
                'target': activity.custom_metrics.get('goal_target', 0),
                'current': activity.custom_metrics.get('goal_current', 0),
            })
    
    context = {
        'journey': journey,
        'goals': goals,
        'milestones': milestones,
        'has_subscription': has_subscription,
    }
    
    return render(request, 'journey/goals.html', context)


@login_required
def create_goal(request, slug):
    """Create a new goal"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    if request.method == 'POST':
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        target = request.POST.get('target', '')
        
        if not title or not target:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('journey_goals', slug=slug)
        
        messages.success(request, f'🎯 Goal "{title}" created successfully!')
        return redirect('journey_goals', slug=slug)
    
    return redirect('journey_goals', slug=slug)


@login_required
def update_goal_progress(request, slug, goal_id):
    """Update goal progress"""
    return redirect('journey_goals', slug=slug)


@login_required
def delete_goal(request, slug, goal_id):
    """Delete a goal"""
    if request.method == 'POST':
        messages.success(request, 'Goal deleted.')
    return redirect('journey_goals', slug=slug)


# ============================================================================
# JOURNEY DASHBOARD
# ============================================================================

@login_required
def journey_dashboard(request, slug):
    """Complete dashboard for a journey"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    if not has_subscription:
        messages.warning(request, '📊 Upgrade to Premium to access the Journey Dashboard.')
        return redirect('subscription_plans')
    
    analytics = {
        'total_views': journey.view_count,
        'unique_viewers': journey.unique_viewers,
        'follower_count': journey.follower_count,
        'total_entries': journey.activities.count(),
        'progress_percentage': journey.get_progress_percentage(),
        'current_day': journey.get_current_day(),
    }
    
    metrics_data = {}
    for activity in journey.activities.all():
        if activity.custom_metrics:
            for key, value in activity.custom_metrics.items():
                if key not in metrics_data:
                    metrics_data[key] = []
                metrics_data[key].append({
                    'day': activity.day_number_field,
                    'value': value
                })
    
    context = {
        'journey': journey,
        'has_subscription': has_subscription,
        'analytics': analytics,
        'metrics_data': metrics_data,
        'available_metrics': list(metrics_data.keys()),
    }
    
    return render(request, 'journey/dashboard.html', context)


# ============================================================================
# JOURNEY CUSTOMIZATION
# ============================================================================

@login_required
def journey_customize(request, slug):
    """Customize journey appearance"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    
    has_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gt=timezone.now()
    ).exists()
    
    if not has_subscription:
        messages.warning(request, '🎨 Upgrade to Premium to customize your journey.')
        return redirect('subscription_plans')
    
    current_theme = getattr(journey, 'theme_settings', None)
    
    if not current_theme or not isinstance(current_theme, dict):
        current_theme = {
            'primary_color': '#3B82F6',
            'secondary_color': '#6366F1',
            'background_color': '#FFFFFF',
            'text_color': '#1F2937',
            'accent_color': '#3B82F6',
            'font_family': 'Inter',
            'layout_style': 'modern',
            'theme_name': 'Default'
        }
    
    if request.method == 'POST':
        theme_data = {
            'primary_color': request.POST.get('primary_color', '#3B82F6'),
            'secondary_color': request.POST.get('secondary_color', '#6366F1'),
            'background_color': request.POST.get('background_color', '#FFFFFF'),
            'text_color': request.POST.get('text_color', '#1F2937'),
            'accent_color': request.POST.get('accent_color', '#3B82F6'),
            'font_family': request.POST.get('font_family', 'Inter'),
            'layout_style': request.POST.get('layout_style', 'modern'),
            'theme_name': request.POST.get('theme_name', 'Custom Theme'),
        }
        
        journey.theme_settings = theme_data
        journey.save()
        
        messages.success(request, '🎨 Theme updated successfully!')
        return redirect('journey_customize', slug=slug)
    
    context = {
        'journey': journey,
        'current_theme': current_theme,
        'has_subscription': has_subscription,
        'fonts': ['Inter', 'Roboto', 'Open Sans', 'Lato', 'Montserrat'],
        'layouts': ['modern', 'classic', 'minimal', 'bold'],
    }
    
    return render(request, 'journey/customize.html', context)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    return render(request, 'errors/403.html', status=403)