import datetime
import uuid
from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.urls import reverse
from django.utils.text import slugify
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


# ============================================================================
# CORE USER MODELS
# ============================================================================
class Profile(models.Model):
    """User profile for Rallynex — fitness & wellness focused"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = CloudinaryField(
        'image',
        folder='profile_pics',
        default='v1763637368/pp_vvzbcj'
    )
    
    bio = models.TextField(default='', max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # Optional social links
    website = models.URLField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    instagram = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    def get_display_name(self):
        return self.user.get_full_name() or self.user.username
    
    def get_journey_count(self):
        return self.journeys.count()
    
    def get_total_entries(self):
        return Activity.objects.filter(journey__creator=self).count()
    
    def get_current_streak(self):
        """Calculate current streak across all active journeys"""
        # FUTURE: Implement streak calculation
        return 0


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# ============================================================================
# JOURNEY MODEL — Fitness & Wellness Focused
# ============================================================================
class Journey(models.Model):
    """
    A journey is a container for documenting fitness and wellness progress.
    Daily logs with structured tracking.
    """
    
    # ===== JOURNEY TYPES =====
    JOURNEY_TYPES = [
        ('daily', 'Daily Journey'),
        # FUTURE: ('milestone', 'Milestone Journey'),
        # FUTURE: ('challenge', 'Challenge'),
        # FUTURE: ('build_in_public', 'Build in Public'),
    ]
    
    # ===== CATEGORIES — FITNESS & WELLNESS ONLY =====
    CATEGORY_CHOICES = [
        ('fitness', 'Fitness'),
        ('wellness', 'Wellness'),
        # FUTURE: ('nutrition', 'Nutrition'),
        # FUTURE: ('recovery', 'Recovery'),
        # FUTURE: ('build_in_public', 'Build in Public'),
        # FUTURE: ('learning', 'Learning & Skills'),
        # FUTURE: ('creative', 'Creative Projects'),
        # FUTURE: ('business', 'Business & Startups'),
        # FUTURE: ('personal', 'Personal Growth'),
        # FUTURE: ('cause', 'Social Cause'),
        # FUTURE: ('other', 'Other'),
    ]
    
    # ===== FITNESS GOALS =====
    FITNESS_GOALS = [
        ('build_muscle', 'Build Muscle'),
        ('lose_weight', 'Lose Weight'),
        ('increase_stamina', 'Increase Stamina'),
        ('improve_flexibility', 'Improve Flexibility'),
        ('run_faster', 'Run Faster'),
        ('general_fitness', 'General Fitness'),
    ]
    
    # ===== WELLNESS FOCUS =====
    WELLNESS_FOCUS = [
        ('mental_health', 'Mental Health'),
        ('better_sleep', 'Better Sleep'),
        ('stress_reduction', 'Stress Reduction'),
        ('mindfulness', 'Mindfulness'),
        ('nutrition', 'Nutrition'),
        ('general_wellness', 'General Wellness'),
    ]
    
    PRIVACY_CHOICES = [
        ('private', 'Private — Only Me'),
        ('unlisted', 'Unlisted — Anyone with Link'),
        ('public', 'Public — Everyone'),
    ]
    
    # ===== TEMPLATE STYLES =====
    TEMPLATE_STYLE_CHOICES = [
        ('fitness', 'Fitness'),
        # FUTURE: ('wellness', 'Wellness'),
        # FUTURE: ('minimal', 'Minimal'),
        # FUTURE: ('build_in_public', 'Build in Public'),
    ]
    
    # ==================== BASIC INFO ====================
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='journeys')
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(max_length=500, blank=True)
    
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='fitness'
    )
    
    journey_type = models.CharField(
        max_length=20, 
        choices=JOURNEY_TYPES, 
        default='daily'
    )
    
    # ===== GOALS & FOCUS =====
    fitness_goal = models.CharField(
        max_length=50,
        choices=FITNESS_GOALS,
        blank=True,
        null=True,
        help_text="What's your main fitness goal?"
    )
    
    wellness_focus = models.CharField(
        max_length=50,
        choices=WELLNESS_FOCUS,
        blank=True,
        null=True,
        help_text="What's your wellness focus?"
    )
    
    custom_goal = models.CharField(
        max_length=200,
        blank=True,
        help_text="Custom goal if none of the above fit"
    )
    
    # ==================== VISUALS ====================
    cover_image = CloudinaryField('image', folder='journey_covers', null=True, blank=True)
    
    template_style = models.CharField(
        max_length=20,
        choices=TEMPLATE_STYLE_CHOICES,
        default='fitness',
        help_text="Display style for your journey"
    )
    
    # ==================== STRUCTURE ====================
    duration = models.PositiveIntegerField(
        default=30, 
        help_text="Number of days for this fitness/wellness journey"
    )
    
    current_day_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Manually set current day. Overrides calendar calculation."
    )
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # ==================== TARGETS (future expansion) ====================
    # target_weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    # target_distance = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    # target_streak = models.PositiveIntegerField(default=0)
    
    # ==================== ANALYTICS ====================
    view_count = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    
    # ==================== PRIVACY ====================
    privacy_status = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='private'
    )
    
    allow_comments = models.BooleanField(
        default=False, 
        help_text="Allow public comments"
    )
    
    # ==================== STATUS ====================
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_archived = models.BooleanField(
        default=False, 
        help_text="Journey is complete and archived"
    )
    
    # ==================== TIMESTAMPS ====================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['category', 'privacy_status']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_featured', '-created_at']),
        ]
        verbose_name_plural = 'Journeys'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Journey.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        if not self.start_date:
            self.start_date = timezone.now()
        
        if self.duration and self.journey_type == 'daily':
            self.end_date = self.start_date + datetime.timedelta(days=self.duration)
        
        super().save(*args, **kwargs)
    
    def get_current_day(self):
        """Get the current day based on start date or manual override"""
        if self.current_day_override:
            return min(self.current_day_override, self.duration)
        
        now = timezone.now()
        if now < self.start_date:
            return 0
        
        days_passed = (now - self.start_date).days
        return min(days_passed + 1, self.duration)
    
    def get_progress_percentage(self):
        """Calculate progress percentage"""
        if self.duration == 0:
            return 0
        
        current = self.get_current_day()
        return min(round((current / self.duration) * 100), 100)
    
    def is_day_locked(self, day_number):
        """Check if a day is locked (future day)"""
        current = self.get_current_day()
        return day_number > current
    
    def get_day_status(self, day_number):
        """Get status of a specific day"""
        has_content = self.activities.filter(day_number_field=day_number).exists()
        current = self.get_current_day()
        
        if day_number > current:
            return 'locked'
        elif day_number == current:
            return 'current'
        else:
            return 'completed' if has_content else 'available'
    
    def get_activity_for_day(self, day_number):
        """Get activity for a specific day"""
        return self.activities.filter(day_number_field=day_number).first()
    
    def get_all_activities_by_day(self):
        """Get all activities indexed by day number"""
        activities = {}
        for activity in self.activities.all():
            activities[activity.day_number_field] = activity
        return activities
    
    def get_absolute_url(self):
        return reverse('journey_detail', kwargs={'slug': self.slug})
    
    def get_meta_title(self):
        return f"{self.title} | Rallynex"
    
    def get_meta_description(self):
        if self.description:
            return self.description[:160]
        return f"Follow {self.creator.get_display_name()}'s fitness journey: {self.title} on Rallynex"
    
    def get_meta_image(self):
        if self.cover_image:
            return self.cover_image.url
        return None
    
    # ===== HELPER METHODS =====
    
    def get_total_workouts(self):
        """Count total workout activities"""
        return self.activities.filter(
            activity_type__in=['cardio', 'strength', 'hiit', 'yoga', 'walking', 'running']
        ).count()
    
    def get_total_reflections(self):
        """Count total reflections"""
        return self.reflections.count()
    
    def get_metrics_summary(self):
        """Get summary of progress metrics"""
        metrics = {}
        for activity in self.activities.all():
            if activity.progress_metrics:
                for key, value in activity.progress_metrics.items():
                    if key not in metrics:
                        metrics[key] = []
                    metrics[key].append(value)
        return metrics
    
    def get_streak(self):
        """Calculate current streak of consecutive days with activity"""
        # FUTURE: Implement streak calculation
        return 0


# ============================================================================
# ACTIVITY MODEL — Daily Fitness/Wellness Entries
# ============================================================================

class Activity(models.Model):
    """
    Individual daily entry within a fitness or wellness journey.
    This is where users document their daily progress.
    """
    
    # ===== MOOD TRACKING =====
    MOOD_CHOICES = [
        ('amazing', '🌟 Amazing'),
        ('great', '💪 Great'),
        ('good', '👍 Good'),
        ('okay', '😐 Okay'),
        ('tired', '😴 Tired'),
        ('challenged', '💪 Challenged'),
        ('struggling', '😞 Struggling'),
        ('proud', '🏆 Proud'),
        ('grateful', '🙏 Grateful'),
        ('neutral', '😶 Neutral'),
    ]
    
    # ===== WORKOUT TYPES =====
    WORKOUT_TYPES = [
        ('cardio', 'Cardio'),
        ('strength', 'Strength Training'),
        ('hiit', 'HIIT'),
        ('yoga', 'Yoga'),
        ('pilates', 'Pilates'),
        ('walking', 'Walking'),
        ('running', 'Running'),
        ('cycling', 'Cycling'),
        ('swimming', 'Swimming'),
        ('sports', 'Sports'),
        ('stretching', 'Stretching'),
        ('other', 'Other'),
    ]
    
    # ===== INTENSITY LEVELS =====
    INTENSITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    # ==================== RELATIONSHIPS ====================
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='activities')
    
    # ==================== CONTENT ====================
    title = models.CharField(max_length=200, blank=True, help_text="Optional title for this entry")
    content = models.TextField(max_length=500, help_text="Your entry content")
    summary = models.TextField(blank=True, help_text="Short summary")
    
    # ==================== WORKOUT DETAILS ====================
    activity_type = models.CharField(
        max_length=20,
        choices=WORKOUT_TYPES,
        blank=True,
        null=True,
        help_text="Type of activity"
    )
    
    duration_minutes = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Duration in minutes"
    )
    
    intensity = models.CharField(
        max_length=10,
        choices=INTENSITY_CHOICES,
        blank=True,
        null=True,
        help_text="Intensity level"
    )
    
    # ==================== MEDIA ====================
    media_file = CloudinaryField(
        'file', 
        folder='activity_files', 
        null=True, 
        blank=True, 
        resource_type='auto'
    )
    is_video = models.BooleanField(default=False)
    thumbnail = CloudinaryField('image', folder='activity_thumbnails', null=True, blank=True)
    media_caption = models.CharField(max_length=200, blank=True)
    
    # ==================== DAY TRACKING ====================
    day_number_field = models.PositiveIntegerField(default=1, db_index=True)
    actual_date = models.DateField(null=True, blank=True, help_text="Actual date of the entry")
    custom_metrics = models.JSONField(default=dict, blank=True, help_text="Custom metrics like weight, sleep, mood, energy, stress, etc.")   
    # ==================== MOOD & METRICS ====================
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True, null=True)
    
    # Flexible metrics (e.g., {"weight": 75, "distance": 5.2, "reps": 10, "sleep": 8})
    progress_metrics = models.JSONField(default=dict, blank=True)
    
    # ==================== LOCATION ====================
    location = models.CharField(max_length=200, blank=True)
    
    # ==================== STATUS ====================
    is_draft = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    
    # ==================== TIMESTAMPS ====================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['day_number_field']
        unique_together = ['journey', 'day_number_field']
        indexes = [
            models.Index(fields=['journey', 'day_number_field']),
            models.Index(fields=['journey', 'created_at']),
            models.Index(fields=['activity_type']),
        ]
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        if self.title:
            return f"Day {self.day_number_field} - {self.title}"
        return f"Day {self.day_number_field} - {self.journey.title}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if self.media_file and hasattr(self.media_file, 'resource_type'):
            self.is_video = self.media_file.resource_type == 'video'
        
        super().save(*args, **kwargs)
        
        if is_new and not self.published_at:
            self.published_at = timezone.now()
            self.save(update_fields=['published_at'])
    
    def get_absolute_url(self):
        return f"{self.journey.get_absolute_url()}?day={self.day_number_field}"
    
    def is_locked(self):
        return self.journey.is_day_locked(self.day_number_field)
    
    def get_display_date(self):
        if self.actual_date:
            return self.actual_date
        return self.published_at.date() if self.published_at else None
    
    def get_date_display(self):
        date = self.get_display_date()
        if date:
            return date.strftime("%b %d, %Y")
        return None
    
    def get_display_html(self):
        """Get the best available HTML for display"""
        if self.media_file:
            if self.is_video:
                return f'<video src="{self.media_file.url}" controls playsinline style="width:100%;display:block;"></video>'
            else:
                return f'<img src="{self.media_file.url}" alt="{self.title or self.content}" style="width:100%;display:block;">'
        if self.thumbnail:
            return f'<img src="{self.thumbnail.url}" alt="{self.title or self.content}" style="width:100%;display:block;">'
        return None
    
    def get_formatted_metrics(self):
        """Format progress metrics for display"""
        if not self.progress_metrics:
            return None
        return self.progress_metrics

# ============================================================================
# REFLECTION MODEL — Personal Reflections (replaces JournalEntry)
# ============================================================================

class Reflection(models.Model):
    """
    Personal reflections for fitness and wellness.
    NOT a blog post — this is for personal reflection, gratitude, and mindset.
    """
    
    # ===== REFLECTION TYPES =====
    REFLECTION_TYPES = [
        ('workout', 'Workout Reflection'),
        ('nutrition', 'Nutrition Reflection'),
        ('mental', 'Mental Wellness'),
        ('recovery', 'Recovery & Sleep'),
        ('milestone', 'Milestone Celebration'),
        ('struggle', 'Struggle / Challenge'),
        ('gratitude', 'Gratitude'),
        ('general', 'General Reflection'),
    ]
    
    # ===== MOOD CHOICES =====
    MOOD_CHOICES = [
        ('amazing', '🌟 Amazing'),
        ('good', '👍 Good'),
        ('okay', '😐 Okay'),
        ('tired', '😴 Tired'),
        ('challenged', '💪 Challenged'),
        ('struggling', '😞 Struggling'),
        ('proud', '🏆 Proud'),
        ('grateful', '🙏 Grateful'),
    ]
    
    # ==================== RELATIONSHIPS ====================
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reflections')
    
    # Optional connections
    related_journey = models.ForeignKey(
        Journey, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reflections'
    )
    related_activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reflections'
    )
    
    # ==================== CONTENT ====================
    reflection_type = models.CharField(
        max_length=20, 
        choices=REFLECTION_TYPES, 
        default='general',  # ← ADDED
        blank=True,         # ← ADDED
        null=True           # ← ADDED
    )
    
    summary = models.CharField(
        max_length=100, 
        help_text="What was this reflection about?"
    )
    
    reflection = models.TextField(
        max_length=500, 
        help_text="How did you feel? What did you learn?"
    )
    
    # ==================== MOOD & ENERGY ====================
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, null=True, blank=True)
    energy_level = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        help_text="1-10"
    )
    sleep_hours = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        null=True, 
        blank=True
    )
    
    # ==================== PRIVACY ====================
    is_private = models.BooleanField(
        default=True, 
        help_text="Private reflections stay between you and your journey"
    )
    
    # ==================== TIMESTAMPS ====================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'related_journey']),
            models.Index(fields=['reflection_type']),
        ]
        verbose_name_plural = 'Reflections'
    
    def __str__(self):
        return f"{self.user.username} - {self.summary[:50]}"
    
    def get_absolute_url(self):
        return reverse('reflection_detail', kwargs={'pk': self.pk})


# ============================================================================
# SOCIAL PUBLISHING (Optional Sharing)
# ============================================================================

class SocialPublish(models.Model):
    """
    Optional publishing — users can share their journey entries
    to social media when they're ready.
    """
    
    PLATFORM_CHOICES = [
        ('twitter', 'Twitter/X'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_publishes')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='social_publishes')
    activity = models.ForeignKey(
        Activity, 
        on_delete=models.CASCADE, 
        related_name='social_publishes',
        null=True,
        blank=True
    )
    
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    share_text = models.TextField()
    share_image = CloudinaryField('image', folder='social_shares', null=True, blank=True)
    
    publish_url = models.URLField(blank=True)
    publish_id = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['journey', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.platform} - {self.journey.title}"


# ============================================================================
# NOTIFICATION MODEL
# ============================================================================

class Notification(models.Model):
    """User notifications — minimal and clean"""
    
    NOTIFICATION_TYPES = [
        ('comment', 'New Comment'),
        ('follow', 'New Follower'),
        ('milestone', 'Milestone Reached'),
        ('export', 'Export Ready'),
        # FUTURE: ('streak', 'Streak Milestone'),
        # FUTURE: ('achievement', 'Achievement Unlocked'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES,
        default='comment'
    )
    message = models.CharField(max_length=255)
    
    related_journey = models.ForeignKey('Journey', on_delete=models.CASCADE, null=True, blank=True)
    related_activity = models.ForeignKey('Activity', on_delete=models.CASCADE, null=True, blank=True)
    
    redirect_link = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"


# ============================================================================
# COMMENT MODEL
# ============================================================================

class Comment(models.Model):
    """
    Comments on journeys and activities.
    Turned off by default for privacy.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    
    content = models.TextField(max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journey', '-created_at']),
            models.Index(fields=['activity', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} on {self.journey or self.activity}"


# ============================================================================
# JOURNEY FOLLOW
# ============================================================================

class JourneyFollow(models.Model):
    """
    Users who follow a journey to get updates.
    Following is opt-in — not the default.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='followers')
    
    notify_on_new_entry = models.BooleanField(default=True)
    notify_on_completion = models.BooleanField(default=True)
    
    followed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'journey')
        indexes = [
            models.Index(fields=['user', '-followed_at']),
            models.Index(fields=['journey', '-followed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} follows {self.journey.title}"


# ============================================================================
# JOURNEY SAVE (Bookmark)
# ============================================================================

class JourneySave(models.Model):
    """
    Users saving/bookmarking journeys to read later.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'journey')
        indexes = [
            models.Index(fields=['journey', '-saved_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} saved {self.journey.title}"


# ============================================================================
# TAG MODEL
# ============================================================================

class Tag(models.Model):
    """Tags for journeys — simple categorization"""
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"#{self.name}"


class JourneyTag(models.Model):
    """Through model for journey tags"""
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('journey', 'tag')


# ============================================================================
# EXPORT MODEL
# ============================================================================

class Export(models.Model):
    """
    Track exported journeys — users can export their documentation.
    """
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('markdown', 'Markdown'),
        ('json', 'JSON'),
        ('html', 'HTML'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exports')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='exports')
    
    format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    include_media = models.BooleanField(default=True)
    include_comments = models.BooleanField(default=False)
    include_reflections = models.BooleanField(default=True)
    
    file_url = models.URLField(blank=True)
    file_size = models.PositiveIntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['journey', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.journey.title} - {self.format}"


# ============================================================================
# CONTACT & SUBSCRIBER
# ============================================================================

class ContactMessage(models.Model):
    """Contact form messages"""
    
    SUBJECT_CHOICES = [
        ('general', 'General Question'),
        ('support', 'Technical Support'),
        ('journey', 'Journey Help'),
        ('export', 'Export Help'),
        ('feature', 'Feature Request'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField()
    ai_response = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class Subscriber(models.Model):
    """Email subscribers for updates"""
    
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return self.email


# ============================================================================
# FUTURE MODELS (Commented — Ready for Expansion)
# ============================================================================

"""
# FUTURE: Fitness Analytics
class FitnessAnalytics(models.Model):
    '''Aggregated analytics for a journey'''
    journey = models.OneToOneField(Journey, on_delete=models.CASCADE)
    total_workouts = models.PositiveIntegerField(default=0)
    total_days_active = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    weight_trend = models.JSONField(default=list)
    performance_trend = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)


# FUTURE: Challenges
class Challenge(models.Model):
    '''Group fitness challenges'''
    name = models.CharField(max_length=100)
    description = models.TextField()
    duration_days = models.PositiveIntegerField(default=30)
    participants = models.ManyToManyField(User, through='ChallengeParticipant')
    is_active = models.BooleanField(default=True)


class ChallengeParticipant(models.Model):
    '''User participation in challenges'''
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    progress = models.PositiveIntegerField(default=0)


# FUTURE: Device Integration
class Integration(models.Model):
    '''Connect to fitness devices/apps'''
    PROVIDER_CHOICES = [
        ('fitbit', 'Fitbit'),
        ('apple_health', 'Apple Health'),
        ('google_fit', 'Google Fit'),
        ('strava', 'Strava'),
        ('garmin', 'Garmin'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    access_token = models.TextField()
    refresh_token = models.TextField()
    last_sync = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


# FUTURE: Achievements
class Achievement(models.Model):
    '''Gamification achievements'''
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    points = models.PositiveIntegerField(default=0)


class UserAchievement(models.Model):
    '''User earned achievements'''
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
"""


# ============================================================================
# SIGNALS
# ============================================================================

@receiver(post_save, sender=JourneyFollow)
def create_follow_notification(sender, instance, created, **kwargs):
    """Create notification when someone follows a journey"""
    if created:
        Notification.objects.create(
            user=instance.journey.creator.user,
            notification_type='follow',
            message=f"{instance.user.username} started following your journey '{instance.journey.title}'.",
            related_journey=instance.journey,
            redirect_link=instance.journey.get_absolute_url()
        )


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    """Create notification when someone comments"""
    if created:
        target_user = None
        if instance.journey:
            target_user = instance.journey.creator.user
        elif instance.activity:
            target_user = instance.activity.journey.creator.user
        
        if target_user and target_user != instance.user:
            Notification.objects.create(
                user=target_user,
                notification_type='comment',
                message=f"{instance.user.username} commented on your journey.",
                related_journey=instance.journey,
                related_activity=instance.activity,
                redirect_link=instance.journey.get_absolute_url() if instance.journey else instance.activity.get_absolute_url()
            )


@receiver(post_save, sender=Activity)
def check_milestone_notification(sender, instance, created, **kwargs):
    """Check if journey hit a milestone (25%, 50%, 75%, 100%)"""
    if created:
        progress = instance.journey.get_progress_percentage()
        milestones = [25, 50, 75, 100]
        
        if progress in milestones:
            Notification.objects.create(
                user=instance.journey.creator.user,
                notification_type='milestone',
                message=f"🎉 Your journey '{instance.journey.title}' is {progress}% complete!",
                related_journey=instance.journey,
                related_activity=instance,
                redirect_link=instance.journey.get_absolute_url()
            )


@receiver(post_save, sender=Reflection)
def check_reflection_streak(sender, instance, created, **kwargs):
    """FUTURE: Check if user has maintained a reflection streak"""
    pass

# ============================================================================
# MONETIZATION MODELS - PayPal Integration
# ============================================================================

class SubscriptionPlan(models.Model):
    """
    Rallynex Plus subscription plans
    """
    PLAN_TYPES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    
    name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    daily_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # PayPal details
    paypal_plan_id = models.CharField(max_length=100, blank=True, help_text="PayPal Plan ID")
    
    # Features included
    has_advanced_analytics = models.BooleanField(default=True)
    has_custom_metrics = models.BooleanField(default=True)
    has_goals_milestones = models.BooleanField(default=True)
    has_progress_charts = models.BooleanField(default=True)
    has_extra_storage = models.BooleanField(default=True)
    has_customization = models.BooleanField(default=True)
    
    storage_limit_mb = models.PositiveIntegerField(default=500)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - ${self.price}"
    
    def save(self, *args, **kwargs):
        if self.plan_type == 'monthly':
            self.daily_price = round(self.price / 30, 2)
        elif self.plan_type == 'annual':
            self.daily_price = round(self.price / 365, 2)
        super().save(*args, **kwargs)


class UserSubscription(models.Model):
    """
    Active user subscriptions via PayPal
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    
    # PayPal subscription details
    paypal_subscription_id = models.CharField(max_length=100, blank=True)
    paypal_customer_id = models.CharField(max_length=100, blank=True)
    
    # Subscription dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    cancel_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    auto_renew = models.BooleanField(default=True)
    
    # Storage tracking
    storage_used_mb = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['paypal_subscription_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True
    
    def get_features(self):
        return {
            'advanced_analytics': self.plan.has_advanced_analytics,
            'custom_metrics': self.plan.has_custom_metrics,
            'goals_milestones': self.plan.has_goals_milestones,
            'progress_charts': self.plan.has_progress_charts,
            'extra_storage': self.plan.has_extra_storage,
            'customization': self.plan.has_customization,
            'storage_limit_mb': self.plan.storage_limit_mb,
            'storage_used_mb': self.storage_used_mb,
        }


class OneTimeProduct(models.Model):
    """
    One-time purchase products
    """
    PRODUCT_TYPES = [
        ('export', 'Export Complete Journey'),
        ('theme', 'Custom Journey Theme'),
        ('storage', 'Extra Storage'),
        ('ai_report', 'AI Progress Report'),
    ]
    
    PAYMENT_TYPES = [
        ('one_time', 'One-Time Payment'),
        ('monthly', 'Monthly Charge'),
        ('per_report', 'Per Report'),
    ]
    
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='one_time')
    
    price_min = models.DecimalField(max_digits=6, decimal_places=2)
    price_max = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # PayPal
    paypal_product_id = models.CharField(max_length=100, blank=True)
    paypal_plan_id = models.CharField(max_length=100, blank=True)
    
    description = models.TextField()
    features = models.JSONField(default=list, blank=True)
    storage_amount_mb = models.PositiveIntegerField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['product_type', 'price_min']
    
    def __str__(self):
        return f"{self.name} (${self.price_min}-${self.price_max})"
    
    def get_price_display(self):
        if self.price_max:
            return f"${self.price_min} - ${self.price_max}"
        return f"${self.price_min}"


class UserPurchase(models.Model):
    """
    Track user one-time purchases via PayPal
    """
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_purchases')
    product = models.ForeignKey(OneTimeProduct, on_delete=models.PROTECT)
    
    # PayPal
    paypal_transaction_id = models.CharField(max_length=100, blank=True)
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2)
    
    # For AI reports
    report_data = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    metadata = models.JSONField(default=dict, blank=True)
    
    # Storage tracking
    storage_allocated_mb = models.PositiveIntegerField(default=0)
    storage_used_mb = models.PositiveIntegerField(default=0)
    
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['product', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} (${self.amount_paid})"
    
    def is_active(self):
        if self.status != 'completed':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class PaidJourneyExport(models.Model):
    """
    Export Complete Journey purchases (paid version)
    """
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('markdown', 'Markdown'),
        ('json', 'JSON'),
        ('html', 'HTML'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_journey_exports')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='paid_export_orders')
    purchase = models.ForeignKey(UserPurchase, on_delete=models.PROTECT, related_name='paid_export_purchases')
    
    format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    file_url = models.URLField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    
    include_media = models.BooleanField(default=True)
    include_reflections = models.BooleanField(default=True)
    include_comments = models.BooleanField(default=False)
    
    is_downloaded = models.BooleanField(default=False)
    download_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'journey']),
            models.Index(fields=['purchase']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.journey.title} ({self.format})"


# main/models.py - Add this class

class CustomTheme(models.Model):
    """
    Custom themes for journeys
    """
    THEME_TYPES = [
        ('default', 'Default'),
        ('dark', 'Dark'),
        ('vibrant', 'Vibrant'),
        ('pastel', 'Pastel'),
        ('minimal', 'Minimal'),
        ('nature', 'Nature'),
        ('ocean', 'Ocean'),
        ('custom', 'Custom'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_themes')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, null=True, blank=True, related_name='custom_themes')
    
    name = models.CharField(max_length=100, default='Custom Theme')
    theme_type = models.CharField(max_length=20, choices=THEME_TYPES, default='default')
    
    # Colors
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#6366F1')
    background_color = models.CharField(max_length=7, default='#FFFFFF')
    text_color = models.CharField(max_length=7, default='#1F2937')
    accent_color = models.CharField(max_length=7, default='#3B82F6')
    
    # Font & Layout
    font_family = models.CharField(max_length=50, default='Inter')
    layout_style = models.CharField(max_length=20, default='modern')
    
    # Cover image (optional)
    cover_image = CloudinaryField('image', folder='theme_covers', null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['journey', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def apply_to_journey(self, journey):
        """Apply this theme to a journey"""
        journey.theme_settings = {
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'background_color': self.background_color,
            'text_color': self.text_color,
            'accent_color': self.accent_color,
            'font_family': self.font_family,
            'layout_style': self.layout_style,
            'theme_name': self.name,
            'cover_image': self.cover_image.url if self.cover_image else None
        }
        journey.save()
        return journey


class PaidCustomTheme(models.Model):
    """
    Custom Journey Theme purchases (paid version)
    """
    THEME_TYPES = [
        ('dark', 'Dark'),
        ('light', 'Light'),
        ('minimal', 'Minimal'),
        ('vibrant', 'Vibrant'),
        ('pastel', 'Pastel'),
        ('custom', 'Custom'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_themes')
    purchase = models.ForeignKey(UserPurchase, on_delete=models.PROTECT, related_name='paid_theme_purchases')
    
    name = models.CharField(max_length=50)
    theme_type = models.CharField(max_length=20, choices=THEME_TYPES, default='custom')
    
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#6366F1')
    background_color = models.CharField(max_length=7, default='#FFFFFF')
    text_color = models.CharField(max_length=7, default='#1F2937')
    
    cover_image = CloudinaryField('image', folder='custom_themes', null=True, blank=True)
    layout_style = models.CharField(max_length=20, default='modern')
    font_family = models.CharField(max_length=50, default='Inter')
    
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class PaidExtraStorage(models.Model):
    """
    Extra Storage purchases (paid version)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_extra_storage')
    purchase = models.ForeignKey(UserPurchase, on_delete=models.PROTECT, related_name='paid_storage_purchases')
    
    total_mb = models.PositiveIntegerField()
    used_mb = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.total_mb}MB"
    
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class PaidAIProgressReport(models.Model):
    """
    AI Progress Report purchases (paid version)
    """
    REPORT_STATUS = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_ai_reports')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='paid_ai_report_orders')
    purchase = models.ForeignKey(UserPurchase, on_delete=models.PROTECT, related_name='paid_ai_report_purchases')
    
    report_title = models.CharField(max_length=200)
    report_content = models.TextField()
    
    summary = models.TextField(blank=True)
    insights = models.JSONField(default=dict, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    progress_data = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    error_message = models.TextField(blank=True)
    
    generated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    download_count = models.PositiveIntegerField(default=0)
    is_downloaded = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'journey']),
            models.Index(fields=['purchase']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.journey.title} Report"
    
    def is_valid(self):
        if self.status != 'completed':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class PaymentTransaction(models.Model):
    """
    Log all PayPal transactions
    """
    TRANSACTION_TYPES = [
        ('subscription', 'Subscription'),
        ('purchase', 'One-Time Purchase'),
        ('refund', 'Refund'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    purchase = models.ForeignKey(UserPurchase, on_delete=models.SET_NULL, null=True, blank=True)
    
    # PayPal
    paypal_transaction_id = models.CharField(max_length=100)
    paypal_invoice_id = models.CharField(max_length=100, blank=True)
    paypal_payer_id = models.CharField(max_length=100, blank=True)
    
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    description = models.CharField(max_length=200)
    metadata = models.JSONField(default=dict, blank=True)
    
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['paypal_transaction_id']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.transaction_type})"


# main/models.py - Add these models

class Goal(models.Model):
    """User goals for their journey"""
    
    GOAL_TYPES = [
        ('streak', 'Streak Goal'),
        ('days', 'Days Goal'),
        ('weight', 'Weight Goal'),
        ('sleep', 'Sleep Goal'),
        ('workouts', 'Workouts Goal'),
        ('custom', 'Custom Goal'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='goals')
    
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    target_value = models.FloatField()
    current_value = models.FloatField(default=0)
    unit = models.CharField(max_length=20, blank=True, help_text="e.g., kg, km, days, hours")
    
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def update_progress(self, value):
        """Update goal progress"""
        self.current_value = value
        if self.current_value >= self.target_value and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            # Create milestone notification
            Notification.objects.create(
                user=self.user,
                notification_type='milestone',
                message=f"🎉 You completed your goal: {self.title}!",
                related_journey=self.journey,
                redirect_link=self.journey.get_absolute_url()
            )
        self.save()
    
    def get_progress_percentage(self):
        """Get progress percentage"""
        if self.target_value == 0:
            return 0
        return min(round((self.current_value / self.target_value) * 100), 100)
    
    def get_days_remaining(self):
        """Get days remaining until deadline"""
        if not self.deadline:
            return None
        remaining = (self.deadline - timezone.now()).days
        return max(0, remaining)


class Milestone(models.Model):
    """Milestones achieved in a journey"""
    
    MILESTONE_TYPES = [
        ('first_entry', 'First Entry'),
        ('streak_3', '3-Day Streak'),
        ('streak_7', '7-Day Streak'),
        ('streak_14', '14-Day Streak'),
        ('streak_30', '30-Day Streak'),
        ('halfway', 'Halfway Point'),
        ('complete', 'Journey Complete'),
        ('custom', 'Custom Milestone'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='milestones')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='milestones')
    
    milestone_type = models.CharField(max_length=20, choices=MILESTONE_TYPES)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='🏆')
    
    achieved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-achieved_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"