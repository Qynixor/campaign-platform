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
    """User profile for Rallynex — Product Builders & Creators"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = CloudinaryField(
        'image',
        folder='profile_pics',
        default='v1763637368/pp_vvzbcj'
    )
    
    bio = models.TextField(default='', max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # Social links for builders
    website = models.URLField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    linkedin = models.CharField(max_length=50, blank=True)
    github = models.CharField(max_length=50, blank=True)
    
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
    
    def get_follower_count(self):
        return JourneyFollow.objects.filter(journey__creator=self).count()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# ============================================================================
# JOURNEY MODEL — Build in Public Focused
# ============================================================================
class Journey(models.Model):
    """
    A journey is a container for documenting product building progress.
    Daily logs tracking wins, failures, learnings, and milestones.
    """
    
    # ===== JOURNEY TYPES =====
    JOURNEY_TYPES = [
        ('build_in_public', 'Build in Public'),
        ('product', 'Product Journey'),
        ('startup', 'Startup Journey'),
        ('side_project', 'Side Project'),
    ]
    
    # ===== CATEGORIES — PRODUCT BUILDING =====
    CATEGORY_CHOICES = [
        ('product', 'Product'),
        ('marketing', 'Marketing'),
        ('fundraising', 'Fundraising'),
        ('hiring', 'Hiring & Team'),
        ('development', 'Development'),
        ('design', 'Design'),
        ('sales', 'Sales'),
        ('learning', 'Learning & Skills'),
        ('personal', 'Personal Growth'),
        ('other', 'Other'),
    ]
    
    PRIVACY_CHOICES = [
        ('private', 'Private — Only Me'),
        ('unlisted', 'Unlisted — Anyone with Link'),
        ('public', 'Public — Everyone'),
    ]
    
    # ===== TEMPLATE STYLES =====
    TEMPLATE_STYLE_CHOICES = [
        ('build_in_public', 'Build in Public'),
        ('minimal', 'Minimal'),
        ('product', 'Product Journey'),
        ('startup', 'Startup Journey'),
    ]
    
    # ==================== BASIC INFO ====================
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='journeys')
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(max_length=500, blank=True)
    
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='product'
    )
    
    journey_type = models.CharField(
        max_length=20, 
        choices=JOURNEY_TYPES, 
        default='build_in_public'
    )
    
    # ===== BUILD IN PUBLIC METRICS =====
    product_stage = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., Idea, MVP, Beta, Launch, Growth, Scale"
    )
    
    product_url = models.URLField(blank=True, help_text="Link to your product")
    github_url = models.URLField(blank=True, help_text="Link to your GitHub repo")
    
    # ===== VISUALS ====================
    cover_image = CloudinaryField('image', folder='journey_covers', null=True, blank=True)
    
    template_style = models.CharField(
        max_length=20,
        choices=TEMPLATE_STYLE_CHOICES,
        default='build_in_public',
        help_text="Display style for your journey"
    )
    
    # ==================== STRUCTURE ====================
    duration = models.PositiveIntegerField(
        default=30, 
        help_text="Number of days for this journey"
    )
    
    current_day_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Manually set current day. Overrides calendar calculation."
    )
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # ==================== COMMUNITY ====================
    allow_comments = models.BooleanField(
        default=True, 
        help_text="Allow public comments"
    )
    
    allow_followers = models.BooleanField(
        default=True,
        help_text="Allow others to follow your journey"
    )
    
    # ==================== ANALYTICS ====================
    view_count = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    follower_count = models.PositiveIntegerField(default=0)
    
    # ==================== PRIVACY ====================
    privacy_status = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='private'
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
        
        if self.duration and self.journey_type in ['build_in_public', 'product', 'startup', 'side_project']:
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
        return f"Follow {self.creator.get_display_name()}'s build in public journey: {self.title} on Rallynex"
    
    def get_meta_image(self):
        if self.cover_image:
            return self.cover_image.url
        return None
    
    # ===== HELPER METHODS =====
    def get_total_entries(self):
        """Count total activity entries"""
        return self.activities.count()
    
    def get_total_reflections(self):
        """Count total reflections"""
        return self.reflections.count()
    
    def get_log_count(self):
        """Get total number of logs"""
        return self.activities.count()
    
    def get_building_days(self):
        """Get number of days since start"""
        if not self.start_date:
            return 0
        return (timezone.now() - self.start_date).days
    
    def update_follower_count(self):
        """Update follower count"""
        self.follower_count = self.followers.count()
        self.save(update_fields=['follower_count'])


# ============================================================================
# ACTIVITY MODEL — Daily Build in Public Entries
# ============================================================================

class Activity(models.Model):
    """
    Individual daily entry within a build in public journey.
    This is where users document their daily product progress.
    """
    
    # ===== ACTIVITY TYPES =====
    ACTIVITY_TYPES = [
        ('ship', '🚀 Ship / Launch'),
        ('milestone', '🏆 Milestone'),
        ('learning', '📚 Learning'),
        ('failure', '💥 Failure / Setback'),
        ('win', '🎉 Win'),
        ('progress', '📈 Progress'),
        ('reflection', '💭 Reflection'),
        ('experiment', '🧪 Experiment'),
        ('feedback', '💬 Feedback'),
    ]
    
    # ===== PRODUCT AREAS =====
    PRODUCT_AREAS = [
        ('frontend', 'Frontend'),
        ('backend', 'Backend'),
        ('design', 'Design'),
        ('marketing', 'Marketing'),
        ('sales', 'Sales'),
        ('fundraising', 'Fundraising'),
        ('hiring', 'Hiring'),
        ('community', 'Community'),
        ('product', 'Product'),
        ('other', 'Other'),
    ]
    
    # ==================== RELATIONSHIPS ====================
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='activities')
    
    # ==================== CONTENT ====================
    title = models.CharField(max_length=200, blank=True, help_text="Optional title for this entry")
    content = models.TextField(max_length=500, help_text="What did you build, learn, or ship today?")
    summary = models.TextField(blank=True, help_text="Short summary")
    
    # ==================== ACTIVITY METADATA ====================
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
        default='progress',
        help_text="What type of activity is this?"
    )
    
    product_area = models.CharField(
        max_length=20,
        choices=PRODUCT_AREAS,
        blank=True,
        null=True,
        help_text="Which area of your product does this relate to?"
    )
    
    # ==================== BUILD METRICS ====================
    hours_spent = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True,
        help_text="Hours spent working on this"
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
    
    # ==================== METRICS ====================
    custom_metrics = models.JSONField(default=dict, blank=True, help_text="Custom metrics like users, revenue, followers, etc.")
    
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
            models.Index(fields=['product_area']),
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
    
    def get_icon_for_type(self):
        """Get emoji icon for activity type"""
        icons = {
            'ship': '🚀',
            'milestone': '🏆',
            'learning': '📚',
            'failure': '💥',
            'win': '🎉',
            'progress': '📈',
            'reflection': '💭',
            'experiment': '🧪',
            'feedback': '💬',
        }
        return icons.get(self.activity_type, '📝')

# ============================================================================
# REFLECTION MODEL — Personal Reflections (replaces JournalEntry)
# ============================================================================

class Reflection(models.Model):
    """
    Personal reflections for product building journey.
    NOT a blog post — this is for personal reflection, lessons learned, and mindset.
    """
    
    # ===== REFLECTION TYPES =====
    REFLECTION_TYPES = [
        ('learning', 'Key Learning'),
        ('challenge', 'Challenge Overcome'),
        ('milestone', 'Milestone Celebration'),
        ('mistake', 'Mistake/Lesson'),
        ('gratitude', 'Gratitude'),
        ('future', 'Future Vision'),
        ('general', 'General Reflection'),
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
        default='general'
    )
    
    summary = models.CharField(
        max_length=100, 
        help_text="What was this reflection about?"
    )
    
    reflection = models.TextField(
        max_length=500, 
        help_text="What did you learn? How did you feel?"
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
        ('linkedin', 'LinkedIn'),
        ('github', 'GitHub'),
        ('devto', 'Dev.to'),
        ('hashnode', 'Hashnode'),
        ('medium', 'Medium'),
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
        ('like', 'Like on Your Post'),
        ('share', 'Someone Shared Your Journey'),
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
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    
    content = models.TextField(max_length=500)
    is_liked = models.BooleanField(default=False)
    
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
        ('csv', 'CSV'),
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
    include_comments = models.BooleanField(default=True)
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
        ('build_in_public', 'Build in Public Help'),
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
    has_social_sharing = models.BooleanField(default=True)
    has_export_features = models.BooleanField(default=True)
    
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
            'social_sharing': self.plan.has_social_sharing,
            'export_features': self.plan.has_export_features,
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
        ('social_pack', 'Social Media Pack'),
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
        ('csv', 'CSV'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_journey_exports')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='paid_export_orders')
    purchase = models.ForeignKey(UserPurchase, on_delete=models.PROTECT, related_name='paid_export_purchases')
    
    format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    file_url = models.URLField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    
    include_media = models.BooleanField(default=True)
    include_reflections = models.BooleanField(default=True)
    include_comments = models.BooleanField(default=True)
    include_metrics = models.BooleanField(default=True)
    
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
        # Update follower count
        instance.journey.update_follower_count()


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