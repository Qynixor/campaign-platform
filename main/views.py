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
import re
from datetime import timedelta, datetime
from django.contrib.auth import get_user_model

from .models import (
    Profile, Journey, Activity, JournalEntry,
    Comment, JourneyFollow, JourneySave, Tag,
    Notification, Export, ContactMessage, Subscriber
)
from .forms import (
    SignUpForm, LoginForm, ProfileForm,
    JourneyForm, JourneySettingsForm, ActivityForm, JournalEntryForm,
    CommentForm, JourneySearchForm, ExportForm, FollowForm,
    ContactForm, NewsletterSignupForm
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
    """Landing page — documentation first"""
    featured_journeys = Journey.objects.filter(
        privacy_status='public',
        is_active=True,
        is_featured=True
    ).select_related('creator__user').prefetch_related('activities')[:6]
    
    recent_journeys = Journey.objects.filter(
        privacy_status='public',
        is_active=True
    ).order_by('-created_at')[:6]
    
    context = {
        'featured_journeys': featured_journeys,
        'recent_journeys': recent_journeys,
    }
    
    # Add user-specific data if logged in
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
    form = JourneySearchForm(request.GET)
    journeys = Journey.objects.filter(privacy_status='public', is_active=True)
    
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
        allowed_sorts = ['-created_at', 'created_at', 'title', '-title']
        if sort and sort in allowed_sorts:
            journeys = journeys.order_by(sort)
        else:
            journeys = journeys.order_by('-created_at')
    else:
        journeys = journeys.order_by('-created_at')
    
    total_count = journeys.count()
    paginator = Paginator(journeys, 12)
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
    """View a single journey with all its entries"""
    journey_qs = Journey.objects.select_related('creator__user').prefetch_related(
        'activities', 
        'followers',
        'comments'
    ).filter(slug=slug, is_active=True)
    
    journey = get_object_or_404(journey_qs)
    
    # Check privacy
    if journey.privacy_status != 'public':
        if not request.user.is_authenticated or (request.user != journey.creator.user and not request.user.is_superuser):
            raise Http404("Journey not found")
    
    track_journey_view(request, journey)
    activities_by_day = journey.get_all_activities_by_day()
    current_day = journey.get_current_day()
    current_activity = activities_by_day.get(current_day)
    
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
    }
    
    return render(request, 'creator/profile.html', context)


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================
# main/views.py - dashboard_view

@login_required
def dashboard_view(request):
    profile = get_user_profile(request.user)
    journeys = Journey.objects.filter(creator=profile).order_by('-created_at')
    
    total_journeys = journeys.count()
    active_journeys = journeys.filter(is_active=True).count()
    total_entries = Activity.objects.filter(journey__creator=profile).count()
    
    try:
        total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    except:
        total_views = 0
    
    # Comment out journal_entries for now
    # journal_entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')[:5]
    journal_entries = []
    
    context = {
        'profile': profile,
        'journeys': journeys[:5],
        'total_journeys': total_journeys,
        'active_journeys': active_journeys,
        'total_entries': total_entries,
        'total_views': total_views,
        'recent_activities': Activity.objects.filter(journey__creator=profile).order_by('-created_at')[:10],
        'recent_comments': Comment.objects.filter(journey__creator=profile).order_by('-created_at')[:5],
        'journal_entries': journal_entries,  # Empty list
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
    """Create a new journey"""
    profile = get_user_profile(request.user)
    
    if request.method == 'POST':
        form = JourneyForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                journey = form.save(commit=False)
                journey.creator = profile
                journey.save()
                form.save()  # Save many-to-many (tags)
                
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
            messages.success(request, 'Settings updated!')
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
    
    if request.method == 'POST':
        form = ActivityForm(
            request.POST, 
            request.FILES, 
            journey=journey, 
            day_number=day_number,
            instance=existing_activity
        )
        
        if form.is_valid():
            activity = form.save(commit=False)
            activity.journey = journey
            if not activity.day_number_field:
                activity.day_number_field = day_number
            activity.save()
            
            messages.success(request, f'✅ Entry saved for Day {day_number}!')
            return redirect('journey_content', slug=slug)
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
    }
    
    return render(request, 'dashboard/activity_form.html', context)


@login_required
def edit_activity_view(request, slug, day_number):
    """Edit an existing activity"""
    profile = get_user_profile(request.user)
    journey = get_object_or_404(Journey, slug=slug, creator=profile)
    activity = get_object_or_404(Activity, journey=journey, day_number_field=day_number)
    
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
# JOURNAL ENTRY VIEWS (Free-Form Documentation)
# ============================================================================

@login_required
def journal_view(request):
    """View all journal entries"""
    entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(entries, 20)
    page = request.GET.get('page')
    
    try:
        entries_page = paginator.page(page)
    except PageNotAnInteger:
        entries_page = paginator.page(1)
    except EmptyPage:
        entries_page = paginator.page(paginator.num_pages)
    
    context = {
        'entries': entries_page,
        'total_entries': entries.count(),
    }
    
    return render(request, 'dashboard/journal.html', context)


@login_required
def journal_create_view(request):
    """Create a new journal entry"""
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, user=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, 'Journal entry saved!')
            return redirect('journal_view')
    else:
        form = JournalEntryForm(user=request.user)
    
    context = {
        'form': form,
        'is_editing': False,
    }
    
    return render(request, 'dashboard/journal_form.html', context)


@login_required
def journal_edit_view(request, pk):
    """Edit a journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, user=request.user, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Journal entry updated!')
            return redirect('journal_view')
    else:
        form = JournalEntryForm(user=request.user, instance=entry)
    
    context = {
        'form': form,
        'is_editing': True,
        'entry': entry,
    }
    
    return render(request, 'dashboard/journal_form.html', context)


@login_required
def journal_delete_view(request, pk):
    """Delete a journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Journal entry deleted.')
        return redirect('journal_view')
    
    context = {
        'entry': entry,
    }
    
    return render(request, 'dashboard/journal_confirm_delete.html', context)


@login_required
def journal_detail_view(request, pk):
    """View a single journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    
    context = {
        'entry': entry,
    }
    
    return render(request, 'dashboard/journal_detail.html', context)


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
            
            messages.success(request, f'Export started! Your {export.get_format_display()} file will be ready soon.')
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
            
            messages.success(request, 'Comment added!')
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
            
            messages.success(request, 'Comment added!')
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
            messages.success(request, 'Profile updated successfully!')
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

# main/views.py

from .services.faq_service import get_ai_response

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
        
        # Generate AI response from FAQ
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
                email=email,
                # REMOVE THIS LINE: defaults={'ip_address': get_client_ip(request)}
            )
            if created:
                messages.success(request, 'You\'re subscribed!')
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


def blog_view(request):
    """Blog index"""
    return render(request, 'blog/index.html')


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


# main/views.py

@login_required
def toolbox_view(request):
    """Creator Toolbox - Central hub for all tools"""
    profile = get_user_profile(request.user)
    
    journeys = Journey.objects.filter(creator=profile)
    total_journeys = journeys.count()
    total_entries = Activity.objects.filter(journey__creator=profile).count()
    total_views = journeys.aggregate(total=Sum('view_count'))['total'] or 0
    total_followers = JourneyFollow.objects.filter(journey__creator=profile).count()
    
    context = {
        'profile': profile,
        'total_journeys': total_journeys,
        'total_entries': total_entries,
        'total_views': total_views,
        'total_followers': total_followers,
        'recent_activities': Activity.objects.filter(journey__creator=profile).order_by('-created_at')[:5],
    }
    
    return render(request, 'toolbox/index.html', context)



# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    return render(request, 'errors/403.html', status=403)