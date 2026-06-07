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
    """User profile for Rallynex"""
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = CloudinaryField(
        'image',
        folder='profile_pics',
        default='v1763637368/pp_vvzbcj'
    )
    
    bio = models.TextField(default='No bio available', max_length=200)
    location = models.CharField(max_length=100, blank=True)
    
    # Social connections (usernames for display)
    tiktok_username = models.CharField(max_length=50, blank=True)
    instagram_username = models.CharField(max_length=50, blank=True)
    youtube_channel = models.CharField(max_length=100, blank=True)
    
    # Verification
    profile_verified = models.BooleanField(default=False)
    
    # Payments
    paypal_email = models.EmailField(max_length=254, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now)
    
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
    
    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# ============================================================================
# SOCIAL CONNECTION MODELS (THE BRIDGE)
# ============================================================================

class SocialConnection(models.Model):
    """OAuth connections to social platforms"""
    
    PLATFORMS = [
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_connections')
    platform = models.CharField(max_length=20, choices=PLATFORMS)
    platform_user_id = models.CharField(max_length=100)
    platform_username = models.CharField(max_length=100)
    
    # OAuth tokens
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expires = models.DateTimeField(null=True)
    
    # Auto-import settings
    auto_import = models.BooleanField(default=True)
    import_hashtag = models.CharField(max_length=50, blank=True)
    
    # Metadata
    connected_at = models.DateTimeField(auto_now_add=True)
    last_sync = models.DateTimeField(null=True)
    
    class Meta:
        unique_together = ('user', 'platform')
        indexes = [
            models.Index(fields=['user', 'platform']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.platform}"
    
    def is_token_expired(self):
        if not self.token_expires:
            return False
        return timezone.now() > self.token_expires


class ImportedContent(models.Model):
    """Content imported from social platforms - the bridge between socials and activities"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('assigned', 'Assigned to Day'),
        ('ignored', 'Ignored'),
    ]
    
    # Source info
    social_connection = models.ForeignKey(SocialConnection, on_delete=models.CASCADE, related_name='imported_content', null=True, blank=True)
    platform = models.CharField(max_length=20)
    platform_post_id = models.CharField(max_length=100)
    platform_url = models.URLField(max_length=500)
    
    # Content
    caption = models.TextField()
    media_url = models.URLField(max_length=500)
    media_type = models.CharField(max_length=20)  # video, image
    thumbnail_url = models.URLField(max_length=500, blank=True)
    
    # Metadata from platform
    posted_at = models.DateTimeField()
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    
    # Assignment
    detected_day = models.PositiveIntegerField(null=True, blank=True)
    assigned_journey = models.ForeignKey('Journey', on_delete=models.SET_NULL, null=True, related_name='imported_content')
    assigned_day = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Resulting activity (once processed)
    created_activity = models.OneToOneField('Activity', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    imported_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('platform', 'platform_post_id')
        ordering = ['-posted_at']
        indexes = [
            models.Index(fields=['social_connection', 'status']),
            models.Index(fields=['assigned_journey', 'assigned_day']),
        ]
        verbose_name_plural = 'Imported Content'
    
    def __str__(self):
        return f"{self.platform} post: {self.caption[:50]}"
    
    def approve_and_assign(self, journey, day):
        """Approve content and assign to a journey day"""
        self.status = 'assigned'
        self.assigned_journey = journey
        self.assigned_day = day
        self.processed_at = timezone.now()
        self.save()


# ============================================================================
# JOURNEY MODEL
# ============================================================================
class Journey(models.Model):
    """
    Main Journey model - a structured series of content
    """
    
    JOURNEY_TYPES = [
        ('daily', 'Daily Challenge'),
        ('milestone', 'Milestone Journey'),
    ]
    
    CATEGORY_CHOICES = [
        ('fitness', 'Fitness & Wellness'),
        ('learning', 'Learning & Skills'),
        ('creative', 'Creative Projects'),
        ('business', 'Business & Startups'),
        ('personal', 'Personal Growth'),
        ('cause', 'Social Cause'),
        ('other', 'Other'),
    ]
    
    # ==================== BASIC INFO ====================
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='journeys')
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(max_length=500)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='personal')
    journey_type = models.CharField(max_length=20, choices=JOURNEY_TYPES, default='daily')
    
    # ==================== VISUALS ====================
    cover_image = CloudinaryField('image', folder='journey_covers', null=True, blank=True)
    cover_video = CloudinaryField('video', folder='journey_covers', resource_type='video', null=True, blank=True)
    
    # ==================== STRUCTURE ====================
    duration = models.PositiveIntegerField(default=30, help_text="Number of days or milestones")
    duration_unit = models.CharField(max_length=10, default='days')
    
    # Allow creators already mid-journey to jump to their current day
    current_day_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Manually set current day for creators already in progress. Overrides calendar calculation."
    )
    
    milestones = models.JSONField(default=list, blank=True, help_text="List of milestone descriptions")
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # ==================== SETTINGS ====================
    is_public = models.BooleanField(default=True)
    allow_comments = models.BooleanField(default=True)
    auto_import_enabled = models.BooleanField(default=False)
    import_hashtag = models.CharField(max_length=50, blank=True)
    
    # ==================== FUNDING (OPTIONAL) ====================
    funding_enabled = models.BooleanField(default=False)
    funding_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    funding_description = models.TextField(blank=True)
    
    # ==================== RELATIONSHIPS ====================
    followers = models.ManyToManyField(User, through='JourneyFollow', related_name='followed_journeys', blank=True)
    tags = models.ManyToManyField('Tag', through='JourneyTag', related_name='journeys', blank=True)
    
    # ==================== ANALYTICS ====================
    view_count = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    total_watch_time = models.PositiveIntegerField(default=0)
    
    # ==================== STATUS ====================
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # ==================== TIMESTAMPS ====================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Template tracking
    template_style = models.CharField(max_length=20, default='default')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['category', 'is_public']),
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
        
        # Guard against None start_date
        if not self.start_date:
            self.start_date = timezone.now()
        
        if self.duration and self.journey_type == 'daily':
            self.end_date = self.start_date + datetime.timedelta(days=self.duration)
        
        super().save(*args, **kwargs)
    
    # ==================== DAY/MILESTONE METHODS ====================
    
    def get_current_day(self):
        """
        Calculate current day based on journey type:
        - Daily: Based on calendar days elapsed OR manual override
        - Milestone: Based on number of completed milestones
        """
        if self.current_day_override:
            return min(self.current_day_override, self.duration)
        
        if self.journey_type == 'milestone':
            return self.activities.count()
        
        now = timezone.now()
        if now < self.start_date:
            return 0
        
        days_passed = (now - self.start_date).days
        return min(days_passed + 1, self.duration)
    
    def get_progress_percentage(self):
        """Get completion percentage"""
        if self.duration == 0:
            return 0
        
        if self.journey_type == 'milestone':
            completed = self.activities.count()
            return min(round((completed / self.duration) * 100), 100)
        
        current = self.get_current_day()
        return min(round((current / self.duration) * 100), 100)
    
    def is_day_locked(self, day_number):
        """
        Check if a day/milestone is locked.
        - Daily: Locked if day > current calendar day (respects override)
        - Milestone: NEVER locked
        """
        if self.journey_type == 'daily':
            current = self.get_current_day()
            return day_number > current
        elif self.journey_type == 'milestone':
            return False
        return False
    
    def get_day_status(self, day_number):
        """Get status of a specific day/milestone."""
        has_content = self.activities.filter(day_number_field=day_number).exists()
        
        if self.journey_type == 'daily':
            current = self.get_current_day()
            
            if day_number > current:
                return 'locked'
            elif day_number == current:
                return 'current'
            else:
                return 'completed' if has_content else 'available'
        
        elif self.journey_type == 'milestone':
            if has_content:
                return 'completed'
            else:
                return 'available'
        
        return 'available'
    
    # ==================== CONTENT METHODS ====================
    
    def get_activity_for_day(self, day_number):
        return self.activities.filter(day_number_field=day_number).first()
    
    def get_all_activities_by_day(self):
        activities = {}
        for activity in self.activities.all():
            activities[activity.day_number_field] = activity
        return activities
    
    # ==================== STATS METHODS ====================
    
    def get_follower_count(self):
        return self.followers.count()
    
    def get_love_count(self):
        return ActivityLove.objects.filter(activity__journey=self).count()
    
    def get_comment_count(self):
        return ActivityComment.objects.filter(activity__journey=self).count()
    
    def get_share_count(self):
        return self.shares.count()
    
    def get_save_count(self):
        return self.saves.count()
    
    def get_total_donations(self):
        if not self.funding_enabled:
            return 0
        return self.donations.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    
    def get_donation_percentage(self):
        if not self.funding_enabled or self.funding_goal == 0:
            return 0
        return min(round((self.get_total_donations() / float(self.funding_goal)) * 100), 100)
    
    # ==================== URL METHODS ====================
    
    def get_absolute_url(self):
        return reverse('journey_detail', kwargs={'slug': self.slug})
    
    def get_share_url(self):
        return f"https://rallynex.com/j/{self.slug}"
    
    # ==================== META METHODS ====================
    
    def get_meta_title(self):
        return f"{self.title} | Rallynex"
    
    def get_meta_description(self):
        if self.description:
            return self.description[:160]
        return f"Follow {self.creator.get_display_name()}'s journey: {self.title} on Rallynex"
    
    def get_meta_image(self):
        if self.cover_image:
            return self.cover_image.url
        return self.creator.image.url


# ============================================================================
# ACTIVITY MODEL (DAY CONTENT)
# ============================================================================
class Activity(models.Model):
    """Individual day/milestone content within a journey"""
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='activities')
    content = models.TextField(max_length=500, help_text="Caption/description for this day")
    
    # Media
    file = CloudinaryField('file', folder='activity_files', null=True, blank=True, resource_type='auto')
    is_video = models.BooleanField(default=False)
    thumbnail = CloudinaryField('image', folder='activity_thumbnails', null=True, blank=True)
    
    # Day tracking
    day_number_field = models.PositiveIntegerField(default=1, db_index=True)
    
    # NEW: Actual date when this milestone happened (for portfolio/trust building)
    actual_date = models.DateField(
        null=True, 
        blank=True,
        help_text="When this milestone actually happened (e.g., project completion date)"
    )
    
    # Source tracking (if imported)
    imported_from = models.ForeignKey(ImportedContent, on_delete=models.SET_NULL, null=True, blank=True)
    source_url = models.URLField(blank=True, help_text="Original social media URL")
    
    # Stats
    view_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    source_url = models.URLField(blank=True, help_text="Original social media URL")
    source_platform = models.CharField(max_length=20, blank=True, help_text="tiktok, youtube, instagram, facebook")
    # Embed
    embed_html = models.TextField(blank=True, help_text="Embed HTML for social media content")
    
    class Meta:
        ordering = ['day_number_field']
        unique_together = ['journey', 'day_number_field']
        indexes = [
            models.Index(fields=['journey', 'day_number_field']),
            models.Index(fields=['journey', 'created_at']),
        ]
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        if self.journey.journey_type == 'milestone':
            return f"Milestone {self.day_number_field} - {self.journey.title}"
        return f"Day {self.day_number_field} - {self.journey.title}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Detect if file is video
        if self.file and hasattr(self.file, 'resource_type'):
            self.is_video = self.file.resource_type == 'video'
        
        super().save(*args, **kwargs)
        
        if is_new and not self.published_at:
            self.published_at = timezone.now()
            self.save(update_fields=['published_at'])
            self._notify_followers()
    
    def _notify_followers(self):
        """Notify journey followers of new activity"""
        # Customize message based on journey type
        if self.journey.journey_type == 'milestone':
            message = f"Milestone {self.day_number_field} of '{self.journey.title}' is complete!"
        else:
            message = f"Day {self.day_number_field} of '{self.journey.title}' is now available!"
        
        for follow in self.journey.journeyfollow_set.filter(notify_on_activity=True):
            Notification.objects.create(
                user=follow.user,
                message=message,
                redirect_link=self.journey.get_absolute_url(),
                journey=self.journey
            )
    
    def get_absolute_url(self):
        return f"{self.journey.get_absolute_url()}?day={self.day_number_field}"
    
    def is_locked(self):
        return self.journey.is_day_locked(self.day_number_field)
    
    def get_love_count(self):
        return self.loves.count()
    
    def get_comment_count(self):
        return self.comments.count()
    
    def get_display_date(self):
        """Return the actual date if set, otherwise the published date"""
        if self.actual_date:
            return self.actual_date
        return self.published_at.date() if self.published_at else None
    
    def get_date_display(self):
        """Return formatted date for display"""
        date = self.get_display_date()
        if date:
            return date.strftime("%b %d, %Y")
        return None

# ============================================================================
# RELATIONSHIP MODELS
# ============================================================================

class JourneyFollow(models.Model):
    """Users following a journey"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE)
    followed_at = models.DateTimeField(auto_now_add=True)
    notify_on_activity = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'journey')
        indexes = [
            models.Index(fields=['user', '-followed_at']),
            models.Index(fields=['journey', '-followed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} follows {self.journey.title}"


class Tag(models.Model):
    """Tags for journeys"""
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
# ENGAGEMENT MODELS
# ============================================================================

class ActivityLove(models.Model):
    """Likes on activities"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='loves')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('activity', 'user')
        indexes = [
            models.Index(fields=['activity', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} loved Activity {self.activity.id}"


class ActivityComment(models.Model):
    """Comments on activities"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} on Activity {self.activity.id}"


class JourneySave(models.Model):
    """Users saving/bookmarking journeys"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'journey')
        indexes = [
            models.Index(fields=['journey', '-saved_at']),
        ]


class Share(models.Model):
    """Track shares of journeys"""
    
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('whatsapp', 'WhatsApp'),
        ('linkedin', 'LinkedIn'),
        ('copy', 'Copy Link'),
        ('other', 'Other'),
    ]
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['journey', '-created_at']),
        ]
        verbose_name = 'Share'
        verbose_name_plural = 'Shares'
    
    def __str__(self):
        return f"Share of {self.journey.title} on {self.platform}"


# ============================================================================
# DONATION MODEL
# ============================================================================

class Donation(models.Model):
    """Simple donations for journeys with funding enabled"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='donations')
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    donor_name = models.CharField(max_length=100, blank=True)
    donor_email = models.EmailField(blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(max_length=500, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paypal_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journey', 'status']),
            models.Index(fields=['donor', '-created_at']),
        ]
    
    def __str__(self):
        donor_display = self.donor.username if self.donor else (self.donor_name or 'Anonymous')
        return f"${self.amount} from {donor_display} to {self.journey.title}"


# ============================================================================
# NOTIFICATION MODEL
# ============================================================================

class Notification(models.Model):
    """User notifications"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    redirect_link = models.URLField(blank=True)
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, null=True, blank=True)
    
    viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'viewed']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"


# ============================================================================
# POST-JOURNEY PRODUCT (OPTIONAL MONETIZATION)
# ============================================================================

class PostJourneyProduct(models.Model):
    """Products creators can sell after journey completes"""
    
    PRODUCT_TYPES = [
        ('blueprint', 'Blueprint PDF'),
        ('behind_scenes', 'Behind the Scenes Video'),
        ('coaching', 'One-on-One Coaching'),
        ('bundle', 'Complete Bundle'),
    ]
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='post_journey_products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    
    # Files
    pdf_file = CloudinaryField('pdf', folder='post_journey_pdfs', null=True, blank=True, resource_type='raw')
    video_file = CloudinaryField('video', folder='post_journey_videos', null=True, blank=True, resource_type='video')
    
    # Coaching specific
    coaching_calendar_link = models.URLField(blank=True)
    coaching_duration = models.IntegerField(default=60, help_text="Minutes per session")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.journey.title} - {self.get_product_type_display()}"


# ============================================================================
# MODERATION MODELS
# ============================================================================

class Report(models.Model):
    """User reports for inappropriate content"""
    
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Violation'),
        ('harassment', 'Harassment'),
        ('other', 'Other'),
    ]
    
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='reports', null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='reports', null=True, blank=True)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report by {self.reported_by.username}"


# ============================================================================
# BLOG / MARKETING MODELS
# ============================================================================

class Blog(models.Model):
    """Blog posts for marketing/SEO"""
    
    CATEGORY_CHOICES = [
        ('updates', 'Product Updates'),
        ('tips', 'Creator Tips'),
        ('spotlight', 'Journey Spotlight'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    excerpt = models.TextField(max_length=500, blank=True)
    content = models.TextField()
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    featured_image = CloudinaryField('image', folder='blog', null=True, blank=True)
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    view_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Add these new fields
    category = models.CharField(max_length=50, choices=[
        ('social-problems', 'Social Media Problems'),
        ('creator-monetization', 'Creator Monetization'),
        ('challenge-design', 'Challenge Design'),
        ('creator-growth', 'Creator Growth'),
        ('rallynex-specific', 'Rallynex Specific'),
        ('high-intent', 'High-Intent Keywords'),
    ], default='social-problems')
    
    read_time = models.PositiveIntegerField(default=5, help_text="Minutes to read")
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    canonical_url = models.URLField(blank=True)
    
    # For internal linking
    related_posts = models.ManyToManyField('self', blank=True, symmetrical=False)
    
    # Content upgrade (lead magnet)
    content_upgrade_title = models.CharField(max_length=100, blank=True)
    content_upgrade_url = models.URLField(blank=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'status']),
            models.Index(fields=['status', '-published_at']),
        ]
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog_detail', args=[self.slug])


class FAQ(models.Model):
    """Frequently Asked Questions"""
    
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('creators', 'For Creators'),
        ('supporters', 'For Supporters'),
        ('payments', 'Payments'),
    ]
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['category', 'order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question


# ============================================================================
# SIGNALS
# ============================================================================

@receiver(post_save, sender=JourneyFollow)
def create_follow_notification(sender, instance, created, **kwargs):
    """Notify creator when someone follows their journey"""
    if created:
        Notification.objects.create(
            user=instance.journey.creator.user,
            message=f"{instance.user.username} started following your journey '{instance.journey.title}'!",
            redirect_link=instance.journey.get_absolute_url(),
            journey=instance.journey
        )


@receiver(post_save, sender=Donation)
def create_donation_notification(sender, instance, created, **kwargs):
    """Notify creator when they receive a donation"""
    if created:
        donor_display = instance.donor.username if instance.donor else (instance.donor_name or 'Someone')
        Notification.objects.create(
            user=instance.journey.creator.user,
            message=f"{donor_display} donated ${instance.amount} to '{instance.journey.title}'!",
            redirect_link=instance.journey.get_absolute_url(),
            journey=instance.journey
        )


@receiver(models.signals.post_delete, sender=Journey)
def delete_journey_files(sender, instance, **kwargs):
    """Clean up Cloudinary files when journey is deleted"""
    if instance.cover_image:
        from cloudinary.uploader import destroy
        destroy(instance.cover_image.public_id)
    if instance.cover_video:
        from cloudinary.uploader import destroy
        destroy(instance.cover_video.public_id, resource_type="video")


class JourneyTemplate(models.Model):
    """Pre-built journey templates creators can purchase"""
    
    CATEGORY_CHOICES = Journey.CATEGORY_CHOICES
    JOURNEY_TYPES = Journey.JOURNEY_TYPES
    
    STYLE_CHOICES = [
        ('default', 'Default'),
        ('fitness', 'Fitness'),
        ('portfolio', 'Portfolio'),
        ('startup', 'Startup'),
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    journey_type = models.CharField(max_length=20, choices=JOURNEY_TYPES, default='daily')
    duration = models.PositiveIntegerField(default=30)
    milestones = models.JSONField(default=list, blank=True)
    template_style = models.CharField(max_length=20, choices=STYLE_CHOICES, default='default')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=10.00)
    is_free = models.BooleanField(default=False)
    cover_image = CloudinaryField('image', folder='template_covers', null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', '-usage_count']
    
    def __str__(self):
        return f"{self.title} — ${self.price}"