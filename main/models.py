import datetime
import uuid
import requests
from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from PIL import Image, ExifTags
from io import BytesIO
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from tinymce.models import HTMLField
from django.db.models.signals import m2m_changed
from django.urls import reverse

from django.core.cache import cache

# Add these imports at the top
from django.db import transaction
from django.db.models import Q

User = get_user_model()

import datetime
import uuid
import requests
from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from PIL import Image, ExifTags
from io import BytesIO
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from tinymce.models import HTMLField
from django.db.models.signals import m2m_changed
from django.urls import reverse

User = get_user_model()

class Profile(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    EDUCATION_CHOICES = (
        ('None', 'None'),
        ('Some High School', 'Some High School'),
        ('High School Graduate', 'High School Graduate'),
        ('Some College', 'Some College'),
        ("Associate's Degree", "Associate's Degree"),
        ("Bachelor's Degree", "Bachelor's Degree"),
        ("Master's Degree", "Master's Degree"),
        ('PhD', 'PhD'),
        ('Other', 'Other'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = CloudinaryField(
        'image',
        folder='profile_pics',
        default='v1763637368/pp_vvzbcj'
    )
    
    bio = models.TextField(default='No bio available')
    contact = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=100, blank=True)
    highest_level_of_education = models.CharField(max_length=100, choices=EDUCATION_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    campaigns = models.ManyToManyField('Campaign', related_name='user_profiles', blank=True)
    following = models.ManyToManyField(User, related_name='following_profiles', blank=True)
    followers = models.ManyToManyField(User, related_name='follower_profiles', blank=True)
    last_campaign_check = models.DateTimeField(default=timezone.now)
    last_chat_check = models.DateTimeField(default=timezone.now)
    profile_verified = models.BooleanField(default=False)

    # ✅ Payment-related field for PayPal
    paypal_email = models.EmailField(max_length=255, blank=True, null=True)
    last_activity = models.DateTimeField(default=timezone.now)
    
    def update_last_activity(self):
        """Update user's last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])   
    
    def has_paypal(self):
        """Check if PayPal details are set"""
        return bool(self.paypal_email)

    def update_verification_status(self):
        """Update verification status."""
        self.profile_verified = True
        self.save(update_fields=['profile_verified'])

    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return (
                today.year - self.date_of_birth.year -
                ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        return None

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def total_loves(self):
        from .models import Love
        # ✅ FIXED: Use self (Profile), not self.user (User)
        return Love.objects.filter(campaign__user=self).count()

    def is_changemaker(self):
        from .models import Activity, ActivityLove
        # ✅ FIXED: Use self (Profile), not self.user (User)
        activity_count = Activity.objects.filter(campaign__user=self).count()
        activity_love_count = ActivityLove.objects.filter(activity__campaign__user=self).count()
        return activity_count >= 1 and activity_love_count >= 1



@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

# FIX: Use DIFFERENT related_name for DirectMessage
class Conversation(models.Model):
    """
    Represents a conversation thread between two users
    """
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_user2')
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track if either user has blocked the conversation
    blocked_by_user1 = models.BooleanField(default=False)
    blocked_by_user2 = models.BooleanField(default=False)
    
    # Muting preferences
    muted_by_user1 = models.BooleanField(default=False)
    muted_by_user2 = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user1', 'user2']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"
    
    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get or create a conversation between two users"""
        users = sorted([user1, user2], key=lambda u: u.id)
        
        conversation, created = cls.objects.get_or_create(
            user1=users[0],
            user2=users[1],
            defaults={'updated_at': timezone.now()}
        )
        return conversation, created
    
    def get_other_user(self, current_user):
        """Get the other user in the conversation"""
        if current_user == self.user1:
            return self.user2
        return self.user1
    
    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        if user == self.user1 or user == self.user2:
            return self.messages.filter(
                recipient=user,
                read=False,
                deleted_by_recipient=False
            ).count()
        return 0
    
    def is_blocked_for_user(self, user):
        """Check if conversation is blocked for a user"""
        if user == self.user1:
            return self.blocked_by_user2
        elif user == self.user2:
            return self.blocked_by_user1
        return False
    
    def is_muted_for_user(self, user):
        """Check if conversation is muted for a user"""
        if user == self.user1:
            return self.muted_by_user1
        elif user == self.user2:
            return self.muted_by_user2
        return False
    
    @property
    def last_message(self):
        """Get the last message in the conversation"""
        
        return self.direct_messages.order_by('-timestamp').first()

# FIX: Use UNIQUE related_name for DirectMessage
class DirectMessage(models.Model):
    """
    One-on-one private messages between users
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='direct_messages')  # Changed from 'messages'
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')  # CHANGED: 'sent_direct_messages'
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_direct_messages')  # CHANGED: 'received_direct_messages'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For multimedia messages - using your existing Cloudinary setup
    file = CloudinaryField(
        'file',
        folder='direct_messages_files',
        null=True,
        blank=True,
        resource_type='auto'
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    
    # Message status
    deleted_by_sender = models.BooleanField(default=False)
    deleted_by_recipient = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'recipient', 'timestamp']),
            models.Index(fields=['recipient', 'read']),
            models.Index(fields=['conversation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"DM from {self.sender.username} to {self.recipient.username}"
    
    def is_active_for_user(self, user):
        """Check if message is visible to a specific user"""
        if user == self.sender:
            return not self.deleted_by_sender
        elif user == self.recipient:
            return not self.deleted_by_recipient
        return False
    
    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save(update_fields=['read', 'read_at'])
    
    def get_file_category(self):
        if not self.file_type:
            return ''
        if self.file_type.startswith('image'):
            return 'image'
        elif self.file_type.startswith('video'):
            return 'video'
        elif self.file_type.startswith('audio'):
            return 'audio'
        else:
            return 'document'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Create notification for recipient
            Notification.objects.create(
                user=self.recipient,
                message=f"You have a new message from {self.sender.username}",
                redirect_link=reverse('dm_page', kwargs={'dm_id': self.conversation.id})
            )


class UserVerification(models.Model):
    VERIFICATION_STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    document_type = models.CharField(max_length=100, choices=(
        ('National ID', 'National ID'),
        ('Business Certificate', 'Business Certificate'),
    ))
    document = models.FileField(upload_to='verification_docs/')
    submission_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=VERIFICATION_STATUS_CHOICES, default='Pending')
    rejection_reason = models.TextField(blank=True, null=True)
    verified_on = models.DateTimeField(blank=True, null=True)

    def approve(self):
        """Approve the verification and set the verified date."""
        self.status = 'Approved'
        self.verified_on = timezone.now()
        self.save()
        # Create a notification for the user
        Notification.objects.create(user=self.user, message=f"Your verification for {self.document_type} has been approved.")

    def reject(self, reason):
        """Reject the verification and set the rejection reason."""
        self.status = 'Rejected'
        self.rejection_reason = reason
        self.save()
        self.notify_user()  # Notify the user upon rejection

    def notify_user(self):
        """Notify the user about the rejection."""
        message = f"Your verification for {self.document_type} has been rejected. Reason: {self.rejection_reason}."
        Notification.objects.create(user=self.user, message=message)

    def __str__(self):
        return f"Verification of {self.user.username} - {self.document_type}"

    class Meta:
        verbose_name = 'User Verification'
        verbose_name_plural = 'User Verifications'
        ordering = ['-submission_date']


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Profile)
def update_user_verification_status(sender, instance, created, **kwargs):
    if instance.profile_verified:  # Use the new field name
        verification = UserVerification.objects.filter(user=instance.user).first()
        if verification and verification.status != 'Approved':
            verification.approve()
            verification.verified_on = timezone.now()
            verification.save()







class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    followed = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.follower} follows {self.followed}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # No need to call update_verification_status() anymore
            # Notify the followed user
            follower_username = self.follower.username
            followed_username = self.followed.username
            message = f"{follower_username} started following you. <a href='{reverse('profile_view', kwargs={'username': follower_username})}'>View Profile</a>"
            Notification.objects.create(user=self.followed, message=message)





def default_content():
    return 'Default content'

         

# models.py
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    
    # PayPal fields
    paypal_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_payer_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_email = models.EmailField(blank=True, null=True)
    
    # Payment provider tracking
    payment_provider = models.CharField(
        max_length=20, 
        choices=[
            ('paypal', 'PayPal'),
            ('none', 'None')
        ],
        default='none'
    )
    
    status = models.CharField(max_length=50, default='inactive')
    campaign_limit = models.PositiveIntegerField(default=2)
    
    def has_active_subscription(self):
        return self.status == 'active'
    
    def get_campaign_count(self):
        from main.models import Campaign
        try:
            return Campaign.objects.filter(user=self.user.profile).count()
        except AttributeError:
            # Fallback in case profile doesn't exist
            return Campaign.objects.filter(user__user=self.user).count()
    
    def can_create_campaign(self):
        # ACTIVE subscribers can create unlimited campaigns
        if self.has_active_subscription():
            return True
        
        # INACTIVE users are limited to campaign_limit
        return self.get_campaign_count() < self.campaign_limit
    
    @classmethod
    def get_for_user(cls, user):
        subscription, created = cls.objects.get_or_create(
            user=user,
            defaults={'status': 'inactive', 'campaign_limit': 2}
        )
        return subscription
    
    @classmethod
    def handle_paypal_subscription(cls, payer_email, subscr_id, custom_data=None):
        """
        Update or create UserSubscription when PayPal subscription is created.
        Uses custom field (user ID) to find the user.
        """
        user = None
        
        # METHOD 1: Try to get user from custom field (user ID) - PRIMARY METHOD
        if custom_data:
            try:
                user_id = int(custom_data)
                user = User.objects.get(id=user_id)
                print(f"✅ Found user by ID {user_id}: {user.username}")
            except (ValueError, User.DoesNotExist) as e:
                print(f"❌ User not found for ID {custom_data}: {e}")
        
        # METHOD 2: Fallback to email lookup (for backward compatibility)
        if not user and payer_email:
            print(f"📧 PayPal - Looking for user with email: {payer_email}")
            try:
                user = User.objects.get(email=payer_email)
                print(f"✅ Found user by email: {user.username}")
            except User.DoesNotExist:
                # Try to find by username if email contains username
                try:
                    username = payer_email.split('@')[0]
                    user = User.objects.get(username=username)
                    print(f"✅ Found user by username: {username}")
                except (User.DoesNotExist, IndexError):
                    print(f"❌ User not found for email: {payer_email}")
                    return None
        
        if not user:
            print(f"❌ Could not find user with any method")
            return None
        
        # Create or update subscription
        subscription, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'status': 'active',
                'paypal_subscription_id': subscr_id,
                'paypal_email': payer_email,
                'payment_provider': 'paypal',
                'campaign_limit': 9999
            }
        )
        
        # Update existing subscription
        subscription.paypal_subscription_id = subscr_id
        subscription.paypal_email = payer_email
        subscription.payment_provider = 'paypal'
        subscription.status = 'active'
        subscription.campaign_limit = 9999
        subscription.save()
        
        print(f"🎉 PayPal subscription activated for {user.username}")
        return subscription
    
    def __str__(self):
        return f"{self.user.username} - {self.status} ({self.payment_provider})"

@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    if created:
        UserSubscription.objects.get_or_create(
            user=instance,
            defaults={'status': 'inactive', 'campaign_limit': 2}
        )






class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import requests
from django.core.files.base import ContentFile
import cloudinary
import cloudinary.uploader

class Campaign(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_campaigns')
    title = models.CharField(max_length=300)
    timestamp = models.DateTimeField(auto_now_add=True)
    # NEW FIELD: When the actual journey/content started
    journey_start_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    content = models.TextField()
    poster = CloudinaryField('image', folder='campaign_files', null=True, blank=True)
    # Add this new field for multiple images
    additional_images = models.JSONField(default=list, blank=True, 
                                       help_text="List of additional image URLs for slideshow")
    # FIXED: Add resource_type='video' for audio files
    audio = CloudinaryField(
        'audio', 
        folder='campaign_audio', 
        resource_type='video',  # This tells Cloudinary it's not an image
        null=True, 
        blank=True
    )
    
    is_active = models.BooleanField(default=True)  # Stops donations when target is met
   
    CATEGORY_CHOICES = (
    ('Personal Empowerment', 'Personal Empowerment'),
    ('Health & Wellbeing Causes', 'Health & Wellbeing Causes'),
    ('Economic Support & Financial Causes', 'Economic Support & Financial Causes'),
    ('Creative & Cultural Causes', 'Creative & Cultural Causes'),
    ('Mental Health & Emotional Support', 'Mental Health & Emotional Support'),
    ('Career, Work & Opportunity', 'Career, Work & Opportunity'),
    ('Housing, Living & Stability', 'Housing, Living & Stability'),
    ('Community & Social Impact', 'Community & Social Impact'),
    ('Education & Skill Building', 'Education & Skill Building'),
    ('Exploration, Sports & Challenges', 'Exploration, Sports & Challenges'),
    ('Other Causes', 'Other Causes'),
    )

    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='Personal Empowerment')
    DEFAULT_CATEGORY_AUDIO = {
    'Personal Empowerment': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201319/peace_lgzimr.mp3',
    'Health & Wellbeing Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201314/health_ni0stj.mp3',
    'Economic Support & Financial Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201320/economic_jx8yp7.mp3',
    'Creative & Cultural Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201312/art_kit66w.mp3',
    'Mental Health & Emotional Support': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201320/environment_hhemfx.mp3',
    'Career, Work & Opportunity': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201324/digital_goeor8.mp3',
    'Housing, Living & Stability': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201321/community_p574mv.mp3',
    'Community & Social Impact': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3',
    'Education & Skill Building': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201304/education_wi2ywe.mp3',
    'Exploration, Sports & Challenges': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201367/Sustainable_llqh66.mp3',
    'Other Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3',
}

    def get_default_audio(self):
        return self.DEFAULT_CATEGORY_AUDIO.get(
            self.category,
            'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3'
    )

    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
    )
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    visible_to_followers = models.ManyToManyField(Profile, blank=True, related_name='visible_campaigns')

    DURATION_UNITS = (
        ('minutes', 'Minutes'),
        ('days', 'Days'),
    )

    # Original duration fields
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Enter duration.")
    duration_unit = models.CharField(
        max_length=10, 
        choices=DURATION_UNITS, 
        null=True,  # Allow NULL in database
        blank=True,  # Allow blank in forms
        default='days'  # Keep default but allow null
    )
    
    # NEW FIELDS FOR REAL-TIME DURATION TRACKING
    end_date = models.DateTimeField(null=True, blank=True, help_text="Calculated end date based on duration")
    duration_last_updated = models.DateTimeField(null=True, blank=True, help_text="When the duration was last changed")
    original_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Original duration when campaign started")
    original_duration_unit = models.CharField(max_length=10, null=True, blank=True, help_text="Original duration unit when campaign started")
    
    funding_goal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,  # Allow NULL in database
        blank=True,  # Allow blank in forms
        default=0.00
    )
    
    tags = models.ManyToManyField(Tag, through='CampaignTag', related_name='campaigns', blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['end_date']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['journey_start_date']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return self.title

    # ==================== SOUND TRIBE METHODS ====================
    def get_sound_tribe_members_count(self):
        """Get the number of members in the sound tribe for this campaign"""
        return SoundTribe.objects.filter(campaign=self).count()
    
    def has_user_joined_tribe(self, user_profile):
        """Check if a specific user has joined the sound tribe"""
        if not user_profile:
            return False
        return SoundTribe.objects.filter(
            user=user_profile,
            campaign=self
        ).exists()
    
    def get_recent_tribe_members(self, limit=6):
        """Get recent tribe members with profile data"""
        recent_members = SoundTribe.objects.filter(
            campaign=self
        ).select_related('user__user', 'user').order_by('-timestamp')[:limit]
        
        return [
            {
                'username': member.user.user.username,
                'profile_pic': member.user.image.url if member.user.image else '',
                'profile_url': reverse('profile_view', kwargs={'username': member.user.user.username}),
                'timestamp': member.timestamp
            }
            for member in recent_members
        ]

    # ==================== FUNDING PROPERTIES ====================
    @property
    def total_pledges(self):
        return self.pledge_set.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def total_donations(self):
        """Calculate total donations for this campaign."""
        return self.donations.filter(fulfilled=True).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
    
    @property
    def donation_percentage(self):
        if self.funding_goal == 0:
            return 0
        return round((self.total_donations / self.funding_goal) * 100, 2)

    @property
    def donation_remaining(self):
        return max(self.funding_goal - self.total_donations, 0)

    @property
    def love_count(self):
        return self.loves.count()
    
    @property
    def is_changemaker(self):
        """Check if the user qualifies as a changemaker."""
        activity_count = self.activity_set.count()
        activity_love_count = ActivityLove.objects.filter(activity__campaign=self).count()
        return activity_count >= 1 and activity_love_count >= 1

    # ==================== TIME/DURATION PROPERTIES ====================
    @property
    def is_outdated(self):
        """Check if the campaign is outdated based on end_date."""
        if self.end_date is None:
            return False  # Ongoing campaigns never expire
        return timezone.now() > self.end_date
    
    @property
    def days_left(self):
        """Calculate days/minutes left based on end_date (real-time)."""
        if self.end_date is None:
            return None
        
        remaining = self.end_date - timezone.now()
        
        if remaining.total_seconds() <= 0:
            return 0
            
        if self.duration_unit == 'minutes':
            return max(int(remaining.total_seconds() // 60), 0)
        else:
            return max(remaining.days, 0)

    @property
    def elapsed_time(self):
        """Calculate how much time has elapsed since journey start"""
        start_date = self.journey_start_date or self.timestamp
        elapsed = timezone.now() - start_date
        return elapsed
    
    @property
    def remaining_percentage(self):
        """Calculate percentage of time remaining"""
        if not self.duration or not self.duration_unit or not self.end_date:
            return 100
        
        total_duration = None
        if self.duration_unit == 'minutes':
            total_duration = timedelta(minutes=self.duration)
        else:
            total_duration = timedelta(days=self.duration)
        
        start_date = self.journey_start_date or self.timestamp
        elapsed = timezone.now() - start_date
        remaining = max(total_duration - elapsed, timedelta(0))
        
        if total_duration.total_seconds() == 0:
            return 0
        
        percentage = (remaining.total_seconds() / total_duration.total_seconds()) * 100
        return max(0, min(100, percentage))

    # ==================== FIXED DAY TRACKING METHODS ====================
    def get_current_day(self):
        """
        Calculate which day of the journey the user is on RIGHT NOW.
        
        CORRECT BEHAVIOR:
        - Started Feb 15 at 10:00 AM
        - Feb 15 10:00 AM - Feb 16 9:59 AM = Day 1
        - Feb 16 10:00 AM - Feb 17 9:59 AM = Day 2
        - Feb 17 10:00 AM - Feb 18 9:59 AM = Day 3
        """
        start_date = self.journey_start_date or self.timestamp
        
        if not start_date:
            return 1
        
        # If campaign has ended, return the final day
        if self.is_outdated and self.duration:
            return self.duration
        
        # Calculate time since start
        now = timezone.now()
        time_since_start = now - start_date
        
        if self.duration_unit == 'minutes':
            # Minutes since start (floor division)
            minutes_since = int(time_since_start.total_seconds() / 60)
            # Current day = minutes_since + 1
            # Example: minute 0-59 = Day 1, minute 60-119 = Day 2
            current_day = minutes_since + 1
        else:
            # Days since start (floor division)
            days_since = time_since_start.days
            # Current day = days_since + 1
            # Example: day 0 = Day 1, day 1 = Day 2
            current_day = days_since + 1
        
        # Cap at total duration
        if self.duration and current_day > self.duration:
            return self.duration
        
        return current_day

    def is_day_locked(self, day_number):
        """
        Check if a specific day number is still locked.
        
        EXAMPLE: Started Feb 15, today is Feb 15
        - Day 1: is_day_locked(1) → False (available)
        - Day 2: is_day_locked(2) → True (locked until tomorrow)
        - Day 3: is_day_locked(3) → True (locked)
        """
        current_day = self.get_current_day()
        return day_number > current_day

    def get_day_unlock_date(self, day_number):
        """
        Calculate exactly when a specific day becomes available.
        
        EXAMPLE: Started Feb 15 at 3:30 PM
        - Day 1 unlocks: Feb 15 at 3:30 PM (immediately)
        - Day 2 unlocks: Feb 16 at 3:30 PM
        - Day 3 unlocks: Feb 17 at 3:30 PM
        """
        start_date = self.journey_start_date or self.timestamp
        
        if day_number <= 1:
            return start_date
        
        # Day N unlocks at start_date + (N-1) days/minutes
        if self.duration_unit == 'minutes':
            # For minute-based campaigns
            unlock_time = start_date + timedelta(minutes=day_number - 1)
        else:
            # For day-based campaigns
            unlock_time = start_date + timedelta(days=day_number - 1)
        
        return unlock_time

    def get_day_status(self, day_number):
        """
        Get detailed status for a specific day.
        Returns a dictionary with all the information needed for templates.
        """
        now = timezone.now()
        current_day = self.get_current_day()
        
        # Case 1: Day is in the past or present (available)
        if day_number < current_day:
            # Past day - completed
            return {
                'status': 'completed',
                'can_upload': False,  # Can't upload to past days
                'message': f'Day {day_number} completed',
                'unlock_date': None,
                'unlock_date_formatted': None,
                'hours_remaining': 0,
                'days_remaining': 0,
            }
        
        elif day_number == current_day:
            # Current day - available now
            return {
                'status': 'available',
                'can_upload': True,
                'message': f'Day {day_number} is available now',
                'unlock_date': None,
                'unlock_date_formatted': None,
                'hours_remaining': 0,
                'days_remaining': 0,
            }
        
        else:
            # Future day - locked
            unlock_date = self.get_day_unlock_date(day_number)
            time_until_unlock = unlock_date - now
            
            # Calculate time remaining
            days_remaining = time_until_unlock.days
            hours_remaining = int(time_until_unlock.total_seconds() / 3600)
            minutes_remaining = int(time_until_unlock.total_seconds() / 60)
            
            # Create user-friendly message
            if days_remaining > 0:
                message = f'Day {day_number} unlocks in {days_remaining} day{"s" if days_remaining != 1 else ""}'
            elif hours_remaining > 0:
                message = f'Day {day_number} unlocks in {hours_remaining} hour{"s" if hours_remaining != 1 else ""}'
            else:
                message = f'Day {day_number} unlocks in {minutes_remaining} minute{"s" if minutes_remaining != 1 else ""}'
            
            return {
                'status': 'locked',
                'can_upload': False,
                'message': message,
                'unlock_date': unlock_date,
                'unlock_date_formatted': unlock_date.strftime('%b %d, %Y at %I:%M %p'),
                'days_remaining': days_remaining,
                'hours_remaining': hours_remaining,
                'minutes_remaining': minutes_remaining,
            }

    def get_day_range(self, max_days=None):
        """
        Get list of day numbers to display in templates.
        """
        if max_days:
            return range(1, max_days + 1)
        elif self.duration:
            return range(1, self.duration + 1)
        else:
            # If no duration, show first 7 days by default
            return range(1, 8)

    def get_completed_days_count(self):
        """
        Get the number of days that have been completed (have updates).
        """
        return self.activity_set.count()

    def get_remaining_days_count(self):
        """
        Get the number of days remaining in the journey.
        """
        if not self.duration:
            return 0
        completed = self.get_completed_days_count()
        return max(0, self.duration - completed)

    # ==================== SAVE METHOD & HELPERS ====================
    def has_duration_changed(self):
        """Check if duration fields have changed"""
        if not self.pk:
            return True
        try:
            old = Campaign.objects.get(pk=self.pk)
            return (old.duration != self.duration or 
                    old.duration_unit != self.duration_unit)
        except Campaign.DoesNotExist:
            return True

    def calculate_end_date(self):
        """Calculate end date based on duration and start date"""
        if not self.duration or not self.duration_unit:
            return None
        
        # Use journey_start_date as base for end date calculation
        base_time = self.journey_start_date or self.timestamp
        
        if self.duration_unit == 'minutes':
            return base_time + timedelta(minutes=self.duration)
        else:
            return base_time + timedelta(days=self.duration)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Set journey_start_date if this is a new campaign
        if is_new and not self.journey_start_date:
            self.journey_start_date = timezone.now()
        
        # Handle existing campaign
        if is_new:
            # Set original duration values for new campaign
            self.original_duration = self.duration
            self.original_duration_unit = self.duration_unit
            self.duration_last_updated = self.journey_start_date or self.timestamp
            
            # Calculate end date for new campaign
            if self.duration and self.duration_unit:
                self.end_date = self.calculate_end_date()
            
            visibility_changed = False
        else:
            # Existing campaign - check if duration changed
            old_instance = Campaign.objects.get(pk=self.pk)
            visibility_changed = old_instance.visibility != self.visibility
            
            if self.has_duration_changed():
                # Store original duration if not already set
                if not self.original_duration:
                    self.original_duration = old_instance.original_duration or old_instance.duration
                if not self.original_duration_unit:
                    self.original_duration_unit = old_instance.original_duration_unit or old_instance.duration_unit
                
                # Update the last updated time to NOW
                self.duration_last_updated = timezone.now()
                
                # Calculate new end date based on current time + new duration
                self.end_date = self.calculate_end_date()
        
        # Save the campaign
        super().save(*args, **kwargs)

        # Handle visibility notifications for existing campaigns
        if not is_new and visibility_changed and self.visibility == 'private':
            self.notify_visible_to_followers()

    def notify_visible_to_followers(self):
        for profile in self.visible_to_followers.all():
            user = profile.user
            message = (
                f'You have been granted access to a private cause: {self.title}. '
                f'<a href="{reverse("view_campaign", kwargs={"campaign_id": self.pk})}">View Cause</a>'
            )
            Notification.objects.create(
                user=user,
                message=message,
                timestamp=timezone.now(),
                campaign_notification=True,
                campaign=self,
                redirect_link=f'/campaigns/{self.pk}/'
            )

    def award_changemaker_status(self):
        """Award changemaker status and assign the correct award type."""
        # Check if the user already has an award for this campaign
        if not ChangemakerAward.objects.filter(user=self.user, campaign=self).exists():
            # Determine the number of campaigns with changemaker status
            changemaker_campaigns = Campaign.objects.filter(user=self.user, activity__isnull=False).distinct()

            # Assign the award based on the number of changemaker campaigns
            campaign_count = changemaker_campaigns.count()
            if campaign_count >= 3:
                award_type = 'Gold'
            elif campaign_count >= 2:
                award_type = 'Silver'
            else:
                award_type = 'Bronze'

            # Create the award entry
            ChangemakerAward.objects.create(
                user=self.user,
                campaign=self,
                award=award_type,
                timestamp=timezone.now()
            )




        def get_goals_and_activities(self):
            goals_activities = {
        'Personal Empowerment': {
            'Goals': [
                'Empower an individual or group to overcome limitations and unlock potential.',
                'Support personal transformation that leads to long-term independence.'
            ],
            'Activities': [
                'Share weekly updates documenting growth, challenges, and breakthroughs.',
                'Run a skills-building challenge with community accountability.',
                'Host live or recorded talks sharing lessons learned.',
                'Provide tools, resources, or mentorship tied to the cause.',
                'Document impact stories from supporters or beneficiaries.'
            ]
        },

        'Health & Wellbeing Causes': {
            'Goals': [
                'Improve physical health outcomes for yourself or others.',
                'Raise awareness and support for health-related challenges.'
            ],
            'Activities': [
                'Post recovery, training, or treatment updates with proof and milestones.',
                'Share educational content about the health condition or goal.',
                'Organize a fitness or wellness challenge supporters can join.',
                'Document the use of funds for medical or wellness needs.',
                'Highlight supporter stories and encouragement.'
            ]
        },

        'Economic Support & Financial Causes': {
            'Goals': [
                'Provide financial relief, stability, or opportunity.',
                'Mobilize support to overcome economic barriers.'
            ],
            'Activities': [
                'Share transparent breakdowns of financial needs and progress.',
                'Post updates showing how funds are being used.',
                'Offer products or services that directly support the cause.',
                'Highlight milestones such as debts cleared or resources secured.',
                'Educate supporters on the broader financial issue being addressed.'
            ]
        },

        'Creative & Cultural Causes': {
            'Goals': [
                'Preserve, promote, or fund creative and cultural expression.',
                'Turn creativity into a sustainable source of impact.'
            ],
            'Activities': [
                'Share behind-the-scenes creation updates.',
                'Release exclusive content to supporters.',
                'Sell creative works or merchandise tied to the cause.',
                'Document cultural impact or community engagement.',
                'Collaborate with other creators or communities.'
            ]
        },

        'Mental Health & Emotional Support': {
            'Goals': [
                'Support emotional wellbeing and mental health awareness.',
                'Create safe spaces for healing and shared experiences.'
            ],
            'Activities': [
                'Post honest updates about mental health journeys or programs.',
                'Share educational resources and coping strategies.',
                'Host guided sessions, talks, or reflections.',
                'Highlight stories of hope, progress, and recovery.',
                'Use funds to access therapy, support groups, or outreach.'
            ]
        },

        'Career, Work & Opportunity': {
            'Goals': [
                'Create access to jobs, skills, or professional growth.',
                'Support career transitions or workforce development.'
            ],
            'Activities': [
                'Share progress toward certifications, training, or job placement.',
                'Offer mentorship or workshops to supporters.',
                'Document outcomes such as employment or business launches.',
                'Sell services or products that fund the cause.',
                'Highlight community success stories.'
            ]
        },

        'Housing, Living & Stability': {
            'Goals': [
                'Secure safe, stable, and dignified living conditions.',
                'Improve quality of life through better housing or resources.'
            ],
            'Activities': [
                'Share updates on housing progress or improvements.',
                'Post photos/videos showing before-and-after impact.',
                'Break down costs and needs transparently.',
                'Document how support improves daily living.',
                'Engage supporters in long-term stability planning.'
            ]
        },

        'Community & Social Impact': {
            'Goals': [
                'Strengthen communities and address social challenges.',
                'Mobilize people around a shared cause or mission.'
            ],
            'Activities': [
                'Post updates from community actions or events.',
                'Share stories from people impacted by the cause.',
                'Organize campaigns, drives, or collective actions.',
                'Highlight supporter contributions and involvement.',
                'Track measurable community impact over time.'
            ]
        },

        'Education & Skill Building': {
            'Goals': [
                'Expand access to education and practical skills.',
                'Empower learners through knowledge and opportunity.'
            ],
            'Activities': [
                'Share learning progress and teaching outcomes.',
                'Post educational content or mini-lessons.',
                'Fundraise for courses, materials, or training.',
                'Showcase student or participant success stories.',
                'Offer paid or free educational resources.'
            ]
        },

        'Exploration, Sports & Challenges': {
            'Goals': [
                'Use challenges and exploration to inspire or fund impact.',
                'Turn personal feats into collective motivation.'
            ],
            'Activities': [
                'Document challenge progress with photos, videos, or audio.',
                'Tie milestones to donation or pledge triggers.',
                'Engage supporters with live updates or check-ins.',
                'Share lessons learned and motivation.',
                'Celebrate achievements with the community.'
            ]
        },

        'Other Causes': {
            'Goals': [
                'Support a unique or emerging cause.',
                'Experiment with new forms of impact and storytelling.'
            ],
            'Activities': [
                'Define custom updates that fit the cause.',
                'Combine storytelling, funding, and community building.',
                'Test new engagement or support models.',
                'Document learnings and outcomes openly.',
                'Let supporters help shape the direction of the cause.'
            ]
        },
    }

        return goals_activities.get(self.category, {})


class CampaignView(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)  # Allow null values for the user field
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    time_spent = models.DurationField(default=timezone.timedelta(minutes=0))

    class Meta:
        unique_together = ('user', 'campaign')






class SoundTribe(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'campaign')
    
    def __str__(self):
        username = self.user.user.username if self.user else "Unknown"
        return f"{username} - {self.campaign.title}"
    
    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new tribe join
            # Create the notification message
            message = f"{self.user.user.username} joined your Soundmark Tribe. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
            # Create the notification
            Notification.objects.create(user=self.campaign.user.user, message=message)
        super().save(*args, **kwargs)









class CampaignTag(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('campaign', 'tag')
    
    def __str__(self):
        return f"{self.campaign.title} - {self.tag.name}"





class Report(models.Model):
    REASON_CHOICES = (
        ('Spam', 'Spam'),
        ('Inappropriate Content', 'Inappropriate Content'),
        ('Copyright Violation', 'Copyright Violation'),
        ('Fraud', 'Fraud'),
        ('Other', 'Other'),
    )
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reports_made')
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Report by {self.reported_by} on {self.campaign}'




class NotInterested(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='not_interested_campaigns')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='not_interested_by')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.user.username} not interested in {self.campaign.title}'




class SupportCampaign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE)
    
    CATEGORY_CHOICES = (
        ('donation', 'Monetary Donation'),
        ('pledge','Pledge'),
        ('campaign_product','Campaign Product'),
    )
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='donation')
    
    # Visibility flags for template toggles
    donate_monetary_visible = models.BooleanField(default=False)
    pledge_visible = models.BooleanField(default=False)
    campaign_product_visible = models.BooleanField(default=False)

    def total_donations(self):
        return self.campaign.donations.aggregate(total=models.Sum('amount'))['total'] or 0

    def total_pledges(self):
        return self.campaign.pledges.aggregate(total=models.Sum('amount'))['total'] or 0

    def donation_percentage(self):
        if self.campaign.funding_goal == 0:
            return 0
        return round((self.total_donations() / self.campaign.funding_goal) * 100, 2)

    def donation_remaining(self):
        return max(self.campaign.funding_goal - self.total_donations(), 0)

    def __str__(self):
        return f"{self.user.username} supports {self.campaign.title}"




from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Donation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    fulfilled = models.BooleanField(default=False)
    paypal_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)  # Changed from tx_ref
    paypal_payout_id = models.CharField(max_length=100, blank=True, null=True)  # For tracking payout to campaign owner

    def __str__(self):
        return f"{self.user.username} donated ${self.amount} to {self.campaign.title}"

# Your other models (Campaign, Profile, etc.) remain the same


from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# models.py - Update your Pledge model
class Pledge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='pledges')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    contact = models.EmailField(blank=True, null=True)
    is_fulfilled = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    anonymous_name = models.CharField(max_length=100, blank=True, null=True)

    # ✅ PayPal payment tracking fields
    paypal_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    paypal_payout_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='pending', choices=(
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ))
    
    # Session key for anonymous users
    session_key = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        if self.user:
            return f"{self.user.username} pledged ${self.amount} to {self.campaign.title}"
        else:
            name = self.anonymous_name or "Anonymous"
            return f"{name} pledged ${self.amount} to {self.campaign.title}"

    def toggle_fulfilled(self):
        self.is_fulfilled = not self.is_fulfilled
        self.save()
        return self.is_fulfilled






# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class CampaignProduct(models.Model):
    STOCK_STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('preorder', 'Preorder'),
        ('discontinued', 'Discontinued'),
    ]

    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # ✅ Cloudinary like poster (no default placeholder)
    image = CloudinaryField(
        'image',
        folder='campaign_product_files',
        null=True,
        blank=True
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    stock_status = models.CharField(
        max_length=20,
        choices=STOCK_STATUS_CHOICES,
        default='in_stock'
    )

    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


    def get_stock_display(self):
        """Helper: decide stock display based on manual status"""
        if self.stock_status == 'out_of_stock':
            return "Out of Stock"
        elif self.stock_status == 'low_stock':
            return f"Only {self.stock_quantity} left"
        elif self.stock_status == 'preorder':
            return "Available for Preorder"
        elif self.stock_status == 'discontinued':
            return "Discontinued"
        else:  # in_stock
            return f"{self.stock_quantity} in stock"

    def can_be_purchased(self):
        return (self.is_active and 
                self.stock_status != 'out_of_stock' and 
                self.stock_status != 'discontinued' and
                self.stock_quantity > 0)


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    product = models.ForeignKey(CampaignProduct, on_delete=models.CASCADE, related_name='transactions')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    tx_ref = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # PayPal tracking fields
    paypal_order_id = models.CharField(max_length=255, null=True, blank=True)
    paypal_capture_id = models.CharField(max_length=255, null=True, blank=True)
    payout_status = models.CharField(max_length=50, choices=PAYOUT_STATUS_CHOICES, default="pending")
    payout_reference = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - ${self.amount} ({self.status})"

    def mark_as_successful(self, paypal_capture_id=None):
        self.status = 'successful'
        if paypal_capture_id:
            self.paypal_capture_id = paypal_capture_id
        self.save()
        
        # Update stock
        if self.product.stock_quantity >= self.quantity:
            self.product.stock_quantity -= self.quantity
            self.product.save()









from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart ({self.user.username})"
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(CampaignProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def total_price(self):
        return self.product.price * self.quantity














class Love(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='loves')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new love
            # Create the notification message
            campaign_title = self.campaign.title
            message = f"{self.user.username} loved your cause '{campaign_title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
            # Create the notification
            Notification.objects.create(user=self.campaign.user.user, message=message)
        super().save(*args, **kwargs)




# models.py
from django.db import models
from django.contrib.auth.models import User

class Comment(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="comments")
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    timestamp = models.DateTimeField(auto_now_add=True)
    text = models.TextField(default='say something..')
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Comment by {self.user.user.username} on {self.campaign.title}"
    
    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new comment
            # Create notification only for top-level comments
            if not self.parent_comment:
                commenter_username = self.user.user.username
                message = f"{commenter_username} commented on your cause '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
                Notification.objects.create(user=self.campaign.user.user, message=message)
        super().save(*args, **kwargs)
    
  
    

    

    def user_like_status(self, user):
        try:
            profile = user.profile
            like = self.likes.get(user=profile)
            return 'liked' if like.is_like else 'disliked'
        except CommentLike.DoesNotExist:
            return None

class CommentLike(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    is_like = models.BooleanField()  # True for like, False for dislike
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'comment')  # A user can only like/dislike a comment once
    
    def __str__(self):
        return f"{'Like' if self.is_like else 'Dislike'} by {self.user.user.username} on comment {self.comment.id}"




class Activity(models.Model):
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE)
    content = models.TextField(default='content')
    timestamp = models.DateTimeField(auto_now_add=True)

    # ✅ Cloudinary version of file upload - Configured for both images and videos
    file = CloudinaryField(
        'file',
        folder='activity_files',
        null=True,
        blank=True,
        resource_type='auto'  # This allows both images and videos
    )

    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new activity
            # Create the notification message for the campaign owner
            message_owner = f"An activity was added to your cause '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
            # Create the notification for the campaign owner
            Notification.objects.create(user=self.campaign.user.user, message=message_owner)
            followers = self.campaign.user.followers.all()
            for follower in followers:
                message_follower = f"An activity was added to a cause you're following: '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
                Notification.objects.create(user=follower, message=message_follower)

        super().save(*args, **kwargs)
    
    @property
    def day_number(self):
        """
        Calculate which day of the campaign this activity belongs to
        based on when it was posted relative to the campaign start.
        """
        if not self.campaign or not self.campaign.timestamp:
            return 1
            
        # Calculate days difference between campaign start and activity post
        delta = self.timestamp.date() - self.campaign.timestamp.date()
        day_num = delta.days + 1  # +1 because day 1 is the first day
        
        # Ensure we don't go below 1
        return max(1, day_num)


class ActivityLove(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='loves')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new love
            # Create the notification message
            message = f"{self.user.username} loved an activity in your cause '{self.activity.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.activity.campaign.pk})}'>View Cause</a>"
            # Create the notification
            Notification.objects.create(user=self.activity.campaign.user.user, message=message)
        super().save(*args, **kwargs)




class ActivityComment(models.Model):
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def reply_count(self):
        return self.replies.count()
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.activity}"

class ActivityCommentLike(models.Model):
    comment = models.ForeignKey(ActivityComment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('comment', 'user')
    
    def __str__(self):
        return f"{self.user.username} likes {self.comment}"






class Chat(models.Model):
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_chats', default=None)
    participants = models.ManyToManyField(User, related_name='chats')
    title = models.CharField(max_length=100, default='')  
    created_at = models.DateTimeField(auto_now_add=True)

    def has_unread_messages(self, last_chat_check):
        return self.messages.filter(timestamp__gt=last_chat_check).exists()

    def __str__(self):
        return f"{self.title} (ID: {self.id})"

@receiver(m2m_changed, sender=Chat.participants.through)
def notify_user_added(sender, instance, action, model, pk_set, **kwargs):
    if action == 'post_add':
        for user_id in pk_set:
            user = User.objects.get(pk=user_id)
            message = f"You have been added to the chat '{instance.title}'. <a href='{reverse('chat_detail', kwargs={'chat_id': instance.pk})}'>View Chat</a>"
            Notification.objects.create(user=user, message=message)



import re
from django.utils.html import escape
# models.py
class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField(default='say something..')
    timestamp = models.DateTimeField(auto_now_add=True)

    # ✅ Cloudinary file field (replaces FileField)
    file = CloudinaryField(
        'file',
        folder='chat_files',
        null=True,
        blank=True
    )

    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)  # image, document, etc.

    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new message
            # Create the notification message
            if self.file:
                message = f"{self.sender.username} shared a file in the chat '{self.chat.title}'. <a href='{reverse('chat_detail', kwargs={'chat_id': self.chat.pk})}'>View Chat</a>"
            else:
                message = f"You have a new message from {self.sender.username} in the chat '{self.chat.title}'. <a href='{reverse('chat_detail', kwargs={'chat_id': self.chat.pk})}'>View Chat</a>"
            
            # Notify all participants except the sender
            for participant in self.chat.participants.exclude(id=self.sender.id):
                Notification.objects.create(user=participant, message=message)

        super().save(*args, **kwargs)

    @property
    def file_category(self):
        if not self.file_type:
            return ''
            if self.file_type.startswith('image'):
                return 'image'
            elif self.file_type.startswith('video'):
                return 'video'
            else:
                return 'document'




class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    viewed = models.BooleanField(default=False)
    campaign_notification = models.BooleanField(default=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True)
    redirect_link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  # Add this field for soft deletion

    def __str__(self):
        return self.message




class ChangemakerAward(models.Model):
    BRONZE = 'bronze'
    SILVER = 'silver'
    GOLD = 'gold'

    AWARD_CHOICES = (
        (BRONZE, 'Bronze'),
        (SILVER, 'Silver'),
        (GOLD, 'Gold'),
    )

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='changemaker_awards')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='related_awards')
    award = models.CharField(max_length=6, choices=AWARD_CHOICES, default=BRONZE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.award}'

    @staticmethod
    def assign_award(user):
        """
        Assigns the appropriate award based on the number of campaigns the user has completed.
        """
        campaign_count = Campaign.objects.filter(user=user).count()
        
        if campaign_count >= 3:
            award = ChangemakerAward.GOLD
        elif campaign_count == 2:
            award = ChangemakerAward.SILVER
        else:
            award = ChangemakerAward.BRONZE

        # Get the most recent campaign for this user
        latest_campaign = Campaign.objects.filter(user=user).latest('timestamp')

        # Check if this user already has an award for this campaign
        if not ChangemakerAward.objects.filter(user=user, campaign=latest_campaign).exists():
            ChangemakerAward.objects.create(user=user, campaign=latest_campaign, award=award)

    @staticmethod
    def get_awards(user):
        """
        Returns the list of awards earned by the user.
        """
        return ChangemakerAward.objects.filter(user=user)


# marketing 
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User

from django.db import models
from django.utils.text import slugify





# models.py
from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField
from django.urls import reverse
import re

class Blog(models.Model):
    CATEGORY_CHOICES = [
        ('RallyNex-Led', 'RallyNex-Led'),
        ('Tips', 'Tips'),
        ('Spotlight', 'Spotlight'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Core fields
    title = models.CharField(max_length=255, help_text="Blog post title (max 255 characters)")
    slug = models.SlugField(unique=True, max_length=255, blank=True, 
                           help_text="URL-friendly version of the title")
    excerpt = models.TextField(max_length=500, blank=True, 
                              help_text="Short summary (shown in listings)")
    content = HTMLField(help_text="Full blog content")
    
    # Author & timestamps
    author = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, 
                              related_name='blog_posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, 
                                       help_text="Leave empty for immediate publication")
    
    # SEO fields
    meta_title = models.CharField(max_length=60, blank=True, 
                                 help_text="SEO title tag (50-60 characters optimal)")
    meta_description = models.TextField(max_length=160, blank=True, 
                                       help_text="SEO description (150-160 characters optimal)")
    focus_keyword = models.CharField(max_length=50, blank=True, 
                                    help_text="Primary keyword for SEO")
    canonical_url = models.URLField(max_length=500, blank=True, 
                                   help_text="Canonical URL if republished from elsewhere")
    
    # Images
    featured_image = CloudinaryField(
        'image',
        folder='blog/featured',
        transformation=[
            {'width': 1200, 'height': 630, 'crop': 'fill'},
            {'quality': 'auto:best'},
        ],
        format='webp',
        null=True,
        blank=True,
        help_text="Featured image (1200x630 recommended)"
    )
    
    og_image = CloudinaryField(
        'image',
        folder='blog/og',
        transformation=[
            {'width': 1200, 'height': 630, 'crop': 'fill'},
            {'quality': 'auto:best'},
        ],
        format='webp',
        null=True,
        blank=True,
        help_text="Social sharing image (1200x630)"
    )
    
    # Status & organization
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    tags = models.CharField(max_length=255, blank=True, 
                           help_text="Comma-separated tags")
    
    # Reading & engagement
    estimated_reading_time = models.PositiveIntegerField(default=5, 
                                                        help_text="Minutes to read")
    view_count = models.PositiveIntegerField(default=0, editable=False)
    like_count = models.PositiveIntegerField(default=0, editable=False)
    share_count = models.PositiveIntegerField(default=0, editable=False)
    
    # SEO performance
    seo_score = models.PositiveIntegerField(default=0, editable=False, 
                                           help_text="Auto-calculated SEO score")
    
    # Internal linking
    related_posts = models.ManyToManyField('self', blank=True, symmetrical=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
        indexes = [
            models.Index(fields=['slug', 'status']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['category', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if empty
        if not self.slug:
            base_slug = slugify(self.title)[:250]
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Auto-generate meta title if empty
        if not self.meta_title:
            self.meta_title = self.title[:60]
        
        # Auto-generate meta description if empty
        if not self.meta_description:
            # Strip HTML tags and get first 160 characters
            clean_text = re.sub('<[^<]+?>', '', self.content)
            self.meta_description = clean_text[:160]
        
        # Auto-generate excerpt if empty
        if not self.excerpt:
            clean_text = re.sub('<[^<]+?>', '', self.content)
            self.excerpt = clean_text[:500]
        
        # Set published_at if publishing for first time
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        # Calculate SEO score
        self.calculate_seo_score()
        
        super().save(*args, **kwargs)
    
    def calculate_seo_score(self):
        """Calculate an SEO score based on content quality"""
        score = 0
        
        # Title length (optimal: 50-60 chars)
        title_len = len(self.meta_title or self.title)
        if 50 <= title_len <= 60:
            score += 20
        elif 40 <= title_len <= 70:
            score += 10
        
        # Meta description length (optimal: 150-160 chars)
        desc_len = len(self.meta_description or '')
        if 150 <= desc_len <= 160:
            score += 20
        elif 130 <= desc_len <= 170:
            score += 10
        
        # Content length (good: 1000+ words)
        word_count = len(self.content.split())
        if word_count >= 2000:
            score += 30
        elif word_count >= 1000:
            score += 20
        elif word_count >= 500:
            score += 10
        
        # Featured image
        if self.featured_image:
            score += 10
        
        # Focus keyword
        if self.focus_keyword:
            score += 10
        
        # Excerpt
        if self.excerpt and len(self.excerpt) >= 100:
            score += 10
        
        self.seo_score = min(score, 100)
    
    def get_absolute_url(self):
        return reverse('blog_detail', args=[self.slug])
    
    def get_admin_url(self):
        return reverse('admin:main_blog_change', args=[self.id])
    
    def __str__(self):
        return self.title
    
    @property
    def is_published(self):
        return self.status == 'published'
    
    @property
    def word_count(self):
        return len(self.content.split())
    
    @property
    def read_time_minutes(self):
        # Assuming 200 words per minute reading speed
        words_per_minute = 200
        return max(1, round(len(self.content.split()) / words_per_minute))





from cloudinary.models import CloudinaryField
from django.utils.text import slugify

class CampaignStory(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)  # For friendly URLs
    content = models.TextField()

    # ✅ Cloudinary image field
    image = CloudinaryField(
        'image',
        folder='story_images',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)  # Automatically create a URL-friendly slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title



class FAQ(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General Information'),
        ('campaigns', 'Creating & Managing Campaigns'),
        ('funding', 'Funding & Payments'),
        ('security', 'Security & Policies'),
        ('backers', 'For Backers & Donors'),
    ]
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return self.question







class AffiliateLink(models.Model):
    title = models.CharField(max_length=200)
    link = models.URLField()
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='affiliate_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set when an instance is created

    def __str__(self):
        return self.title




class PlatformFund(models.Model):
    donation_link = models.URLField(max_length=200)

    def __str__(self):
        return self.donation_link


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email



class AffiliateLibrary(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField()
    affiliate_link = models.URLField()
    description = models.TextField(blank=True)
    # Add more fields as needed, such as commission rate, affiliate program details, etc.

class AffiliateNewsSource(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField()
    affiliate_link = models.URLField()
    description = models.TextField(blank=True)
    # Add more fields as needed, such as commission rate, affiliate program details, etc


class NativeAd(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()

    # ✅ Cloudinary image upload
    image = CloudinaryField(
        'image',
        folder='native_ad_images',
        null=True,
        blank=True
    )

    link = models.URLField()
    sponsored_by = models.CharField(max_length=100)

    def __str__(self):
        return self.title





class Surah(models.Model):
    name = models.CharField(max_length=255)
    surah_number = models.IntegerField(unique=True)
    chapter = models.IntegerField(default=1)
    english_name = models.CharField(max_length=255, default='unknown')
    place_of_revelation = models.CharField(max_length=255, default='unknown')

    def __str__(self):
        return self.name

class QuranVerse(models.Model):
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE)
    verse_number = models.IntegerField()
    verse_text = models.TextField()
    translation = models.TextField()
    description = models.TextField(blank=True, null=True)  # New description field

    class Meta:
        unique_together = ('surah', 'verse_number')

    def __str__(self):
        return f"{self.surah.name} {self.verse_number}"


class Adhkar(models.Model):
    TYPE_CHOICES = [
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('night', 'Night'),
        ('after_prayer', 'After Prayer'),
        ('anywhere', 'Anywhere'),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    text = models.TextField()
    translation = models.TextField()
    reference = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.get_type_display()} Adhkar"


class Hadith(models.Model):
    narrator = models.CharField(max_length=255)
    text = models.TextField()
    reference = models.CharField(max_length=255)
    authenticity = models.CharField(max_length=100)

    def __str__(self):
        return f"Hadith {self.id}: {self.reference}"

