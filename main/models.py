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
from django.db import models, transaction
from django.db.models import Q, Sum, Avg, Count
from django.db.models.functions import TruncDate  # Add this line
from django.core.cache import cache

# Add these imports at the top
from django.db import transaction
from django.db.models import Q

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
    # REMOVED: following and followers fields
    last_campaign_check = models.DateTimeField(default=timezone.now)
    last_chat_check = models.DateTimeField(default=timezone.now)
    profile_verified = models.BooleanField(default=False)

    # ✅ Payment-related field for PayPal
    paypal_email = models.EmailField(max_length=254, blank=True, null=True, verbose_name="PayPal Email")
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
        return Love.objects.filter(campaign__user=self).count()

    def is_changemaker(self):
        from .models import Activity, ActivityLove
        activity_count = Activity.objects.filter(campaign__user=self).count()
        activity_love_count = ActivityLove.objects.filter(activity__campaign__user=self).count()
        return activity_count >= 1 and activity_love_count >= 1


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

@receiver(post_save, sender=Profile)
def update_user_verification_status(sender, instance, created, **kwargs):
    if instance.profile_verified:
        verification = UserVerification.objects.filter(user=instance.user).first()
        if verification and verification.status != 'Approved':
            verification.approve()
            verification.verified_on = timezone.now()
            verification.save()

from django.db import models
from django.contrib.auth.models import User
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
from cloudinary.models import CloudinaryField
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncDate
import json
import requests
from django.core.files.base import ContentFile
import cloudinary
import cloudinary.uploader
from cloudinary.models import CloudinaryField
import json
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from cloudinary.models import CloudinaryField


# ============================================================================
# CAMPAIGN MODEL
# ============================================================================

class Campaign(models.Model):
    """
    Main Campaign model for journey-based crowdfunding
    """
    # ==================== BASIC FIELDS ====================
    user = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='user_campaigns')
    title = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    journey_start_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    content = models.TextField(max_length=150)
    
    # ==================== MEDIA FIELDS ====================
    poster = CloudinaryField('image', folder='campaign_files', null=True, blank=True)
    additional_images = models.JSONField(default=list, blank=True, 
                                       help_text="List of additional image URLs for slideshow")
    audio = CloudinaryField(
        'audio', 
        folder='campaign_audio', 
        resource_type='video',
        null=True, 
        blank=True
    )
    
    # ==================== STATUS FIELDS ====================
    is_active = models.BooleanField(default=True)
    premium_activated = models.BooleanField(default=False, help_text="Whether premium stats have been activated for this campaign")   
    template = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='clones')
    
    # ==================== CATEGORY CHOICES ====================
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
        ('Religious & Spiritual Causes', 'Religious & Spiritual Causes'),
        ('Other Causes', 'Other Causes'),
    )

    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='Personal Empowerment')
    
    # ==================== DEFAULT AUDIO BY CATEGORY ====================
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
        'Religious & Spiritual Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201319/peace_lgzimr.mp3',
        'Other Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3',
    }

    # ==================== DURATION FIELDS ====================
    DURATION_UNITS = (
        ('minutes', 'Minutes'),
        ('days', 'Days'),
    )

    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Enter duration.")
    duration_unit = models.CharField(
        max_length=10, 
        choices=DURATION_UNITS, 
        null=True,
        blank=True,
        default='days'
    )
    
    end_date = models.DateTimeField(null=True, blank=True, help_text="Calculated end date based on duration")
    duration_last_updated = models.DateTimeField(null=True, blank=True, help_text="When the duration was last changed")
    original_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Original duration when campaign started")
    original_duration_unit = models.CharField(max_length=10, null=True, blank=True, help_text="Original duration unit when campaign started")
    
    # ==================== FUNDING FIELDS ====================
    funding_goal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,
        blank=True,
        default=0.00
    )
    
    # ==================== RELATIONSHIP FIELDS ====================
    tags = models.ManyToManyField('Tag', through='CampaignTag', related_name='campaigns', blank=True)
    
    # Campaign following system
    followers = models.ManyToManyField(
        User, 
        through='CampaignFollow',
        related_name='following_campaigns',
        blank=True,
        help_text="Users following this campaign"
    )


    # ==================== META CLASS ====================
    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['end_date']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['journey_start_date']),
            models.Index(fields=['is_active', '-timestamp']),
            models.Index(fields=['template']),
        ]
        ordering = ['-timestamp']

    
    # ADD THESE METHODS:
    def get_display_tags(self, limit=3):
        """Get limited number of tags for display"""
        return self.tags.all()[:limit]
    
    def has_more_tags(self):
        """Check if there are more than 3 tags"""
        return self.tags.count() > 3
    
    def get_excess_tags_count(self):
        """Get count of tags beyond the limit"""
        return max(0, self.tags.count() - 3)
    
    def get_tags_string(self, limit=None):
        """Get tags as formatted string with # symbols"""
        tags = self.tags.all()
        if limit:
            tags = tags[:limit]
        
        if tags:
            return ' '.join([f'#{tag.name}' for tag in tags])
        return ''


    # ==================== STRING REPRESENTATION ====================
    def __str__(self):
        return self.title

    # ==================== MEDIA HELPER METHODS ====================
    
    def get_default_audio(self):
        """Get default audio URL based on category"""
        return self.DEFAULT_CATEGORY_AUDIO.get(
            self.category,
            'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3'
        )

    def get_images(self):
        """Return list of all image URLs for slideshow with high quality"""
        images = []
        if self.poster:
            images.append(self._get_optimized_url(self.poster.url, 430, 860))
        
        # Add additional images if they exist
        if self.additional_images and isinstance(self.additional_images, list):
            for img in self.additional_images[:4]:
                images.append(self._get_optimized_url(img, 430, 860))
        
        # If no images, return placeholder
        if not images:
            images.append('https://res.cloudinary.com/dvlgdzood/image/upload/q_90,f_auto,c_fill,w_430,h_860/v1763637368/pp_vvzbcj.jpg')
        
        return images[:5]
    
    def _get_optimized_url(self, url, width, height):
        """Apply Cloudinary optimizations to URL"""
        if not url or 'cloudinary' not in url:
            return url
        
        try:
            if 'upload/' in url:
                parts = url.split('upload/')
                if len(parts) > 1:
                    return f"{parts[0]}upload/q_90,f_auto,c_fill,w_{width},h_{height}/{parts[1]}"
            return url
        except:
            return url
    
    def get_image_count(self):
        """Get total number of images"""
        return len(self.get_images())
    
    def get_audio_url(self):
        """Get audio URL or default based on category"""
        if self.audio:
            return self.audio.url
        return self.get_default_audio()
    
    # ==================== USER/PROFILE METHODS ====================
    
    def get_username(self):
        """Get creator username"""
        try:
            if self.user and self.user.user:
                return self.user.user.username
            return 'unknown'
        except:
            return 'unknown'
    
    def get_profile_image(self):
        """Get creator profile image with high quality"""
        try:
            if self.user and self.user.image:
                if hasattr(self.user.image, 'url'):
                    return self._get_optimized_url(self.user.image.url, 96, 96)
            return 'https://res.cloudinary.com/dvlgdzood/image/upload/q_90,f_auto,c_fill,w_96,h_96/v1763637368/pp_vvzbcj.jpg'
        except:
            return 'https://res.cloudinary.com/dvlgdzood/image/upload/q_90,f_auto,c_fill,w_96,h_96/v1763637368/pp_vvzbcj.jpg'
    
    def get_location_display(self):
        """Get location for display"""
        try:
            if self.user and self.user.location:
                return self.user.location
            return 'Unknown'
        except:
            return 'Unknown'
    
    def is_verified(self):
        """Check if creator is verified"""
        try:
            return getattr(self.user, 'profile_verified', False)
        except:
            return False
    
    # ==================== COUNT METHODS ====================
    
    def get_love_count(self):
        """Get love count safely"""
        try:
            return self.loves.count()
        except:
            return 0
    
    def get_comment_count(self):
        """Get comment count safely"""
        try:
            return self.comments.count()
        except:
            return 0
    
    def get_follower_count(self):
        """Get follower count safely"""
        try:
            return self.followers.count()
        except:
            return 0
    
    def get_save_count(self):
        """Get save count safely"""
        try:
            from .models import CampaignSave
            return CampaignSave.objects.filter(campaign=self).count()
        except:
            return 0
    
    def get_clone_count(self):
        """Get number of times this campaign has been cloned"""
        try:
            return Campaign.objects.filter(template=self).count()
        except:
            return 0
    
    def get_donor_count(self):
        """Get unique donor count"""
        try:
            if hasattr(self, 'donations'):
                return self.donations.filter(fulfilled=True).values('user').distinct().count()
            return 0
        except:
            return 0
    
    # ==================== TIME METHODS ====================
    
    @property
    def time_ago(self):
        """Get human-readable time ago string"""
        from django.utils.timesince import timesince
        from django.utils.timezone import now
        try:
            return timesince(self.timestamp, now())
        except:
            return 'recently'
    
    def get_current_day(self):
        """Calculate current day of campaign"""
        try:
            start_date = self.journey_start_date or self.timestamp
            
            if not start_date:
                return 1
            
            if self.is_outdated and self.duration:
                return self.duration
            
            now = timezone.now()
            time_since_start = now - start_date
            
            if self.duration_unit == 'minutes':
                minutes_since = int(time_since_start.total_seconds() / 60)
                current_day = minutes_since + 1
            else:
                days_since = time_since_start.days
                current_day = days_since + 1
            
            if self.duration and current_day > self.duration:
                return self.duration
            
            return current_day
        except:
            return 1
    
    def get_current_day_display(self):
        """Get current day with formatting"""
        current = self.get_current_day()
        total = self.duration or 30
        return {
            'current': current,
            'total': total,
            'display': f"Day {current} of {total}"
        }
    
    def get_progress_percentage(self):
        """Get progress percentage for display"""
        try:
            if self.duration and self.duration > 0:
                current = self.get_current_day()
                return min(round((current / self.duration) * 100), 100)
            return 0
        except:
            return 0
    
    # ==================== FUNDING PROPERTIES ====================
    
    @property
    def total_pledges(self):
        try:
            return self.pledge_set.aggregate(total=models.Sum('amount'))['total'] or 0
        except:
            return 0
    
    @property
    def total_donations(self):
        try:
            return self.donations.filter(fulfilled=True).aggregate(
                total=models.Sum('amount')
            )['total'] or 0
        except:
            return 0
    
    @property
    def donation_percentage(self):
        try:
            if self.funding_goal == 0:
                return 0
            return round((self.total_donations / self.funding_goal) * 100, 2)
        except:
            return 0

    @property
    def donation_remaining(self):
        try:
            return max(self.funding_goal - self.total_donations, 0)
        except:
            return 0

    @property
    def love_count(self):
        return self.get_love_count()
    
    # ==================== TIME PROPERTIES ====================
    
    @property
    def is_outdated(self):
        try:
            if self.end_date is None:
                return False
            return timezone.now() > self.end_date
        except:
            return False
    
    @property
    def days_left(self):
        try:
            if self.end_date is None:
                return None
            
            remaining = self.end_date - timezone.now()
            
            if remaining.total_seconds() <= 0:
                return 0
                
            if self.duration_unit == 'minutes':
                return max(int(remaining.total_seconds() // 60), 0)
            else:
                return max(remaining.days, 0)
        except:
            return 0

    # ==================== PREMIUM ACCESS METHODS ====================
    
    def can_access_premium(self, user):
        """Check if user can access premium stats for this campaign"""
        if not user.is_authenticated:
            return False
        
        # Campaign owner always has access
        if self.user and self.user.user == user:
            return True
        
        # Check subscription
        subscription = PremiumSubscription.objects.filter(
            user=user,
            status__in=['active', 'trial']
        ).first()
        
        if subscription and subscription.is_active:
            return True
        
        # Check one-time purchase
        one_time = CampaignPremiumAccess.objects.filter(
            campaign=self,
            purchased_by=user
        ).filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gt=timezone.now())
        ).first()
        
        if one_time:
            return True
        
        # Check free trial
        trial = CampaignFreeTrial.objects.filter(
            campaign=self,
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        return bool(trial)

    def start_free_trial(self, user):
        """Start a free trial for a user"""
        # Deactivate any existing trials
        CampaignFreeTrial.objects.filter(
            campaign=self,
            user=user,
            is_active=True
        ).update(is_active=False)
        
        # Create new trial (30 days)
        trial = CampaignFreeTrial.objects.create(
            campaign=self,
            user=user,
            expires_at=timezone.now() + timedelta(days=30),
            is_active=True
        )
        
        return trial
    def get_share_count(self):
        """Get number of shares"""
        return Share.objects.filter(campaign=self).count()
    
    def get_repeat_donor_count(self):
        """Get number of repeat donors"""
        from django.db.models import Count
        return Donation.objects.filter(
            campaign=self,
            fulfilled=True
        ).values('user').annotate(
            count=Count('id')
        ).filter(count__gt=1).count()
    def get_or_create_prediction(self):
        """Get or generate AI predictions"""
        prediction, created = CampaignPrediction.objects.get_or_create(
            campaign=self
        )
        
        # Update if older than 24 hours
        if not created and (timezone.now() - prediction.last_updated).days >= 1:
            prediction = self.generate_ai_prediction()
        
        return prediction

    def generate_ai_prediction(self):
        """Generate AI predictions based on campaign data"""
        from django.db.models import Q
        
        prediction, _ = CampaignPrediction.objects.get_or_create(campaign=self)
        
        # Get historical data
        total_days = self.get_current_day()
        daily_growth_rate = 0
        
        # Calculate follower growth rate
        follower_count = self.get_follower_count()
        if total_days > 1:
            daily_growth_rate = follower_count / total_days
        
        # Get donation data
        total_donations = float(self.total_donations)
        donor_count = self.get_donor_count()
        avg_donation = total_donations / donor_count if donor_count > 0 else 25
        
        # Get engagement data
        love_count = self.get_love_count()
        comment_count = self.get_comment_count()
        
        # Calculate success probability based on multiple factors
        success_factors = []
        
        # Factor 1: Funding progress (40% weight)
        funding_progress = 0
        if self.funding_goal and self.funding_goal > 0:
            funding_progress = (total_donations / float(self.funding_goal)) * 100
            funding_score = min(funding_progress, 100) * 0.4
            success_factors.append(funding_score)
        
        # Factor 2: Follower engagement (30% weight)
        engagement_rate = 0
        if follower_count > 0:
            engagement_rate = ((love_count + comment_count) / follower_count) * 100
            engagement_score = min(engagement_rate * 3, 100) * 0.3
            success_factors.append(engagement_score)
        
        # Factor 3: Growth momentum (20% weight)
        momentum_score = min(daily_growth_rate * 10, 100) * 0.2
        success_factors.append(momentum_score)
        
        # Factor 4: Time remaining (10% weight)
        days_left = self.days_left or 30
        if days_left > 0:
            time_score = min((days_left / 30) * 100, 100) * 0.1
            success_factors.append(time_score)
        
        # Calculate final probability
        success_probability = sum(success_factors) / len(success_factors) if success_factors else 50
        
        # Predict final amount
        if total_donations > 0 and total_days > 0:
            daily_rate = total_donations / total_days
            remaining_days = self.days_left or 30
            predicted_final = total_donations + (daily_rate * remaining_days)
        else:
            predicted_final = float(self.funding_goal or 1000) * 0.5
        
        # Predict peak day (usually around 30-40% through campaign)
        peak_day = int(total_days * 1.5) if total_days < 10 else total_days
        
        # Generate risk factors
        risk_factors = []
        recommendations = []
        
        if 'funding_progress' in locals() and funding_progress < 20 and total_days > 5:
            risk_factors.append("Low funding progress relative to time elapsed")
            recommendations.append("Share your campaign on social media platforms")
        
        if 'engagement_rate' in locals() and engagement_rate < 5:
            risk_factors.append("Low audience engagement")
            recommendations.append("Post more interactive activities to boost engagement")
        
        if daily_growth_rate < 1:
            risk_factors.append("Slow follower growth")
            recommendations.append("Encourage followers to share your campaign")
        
        if not risk_factors:
            risk_factors.append("No major risks detected")
            recommendations.append("Keep up the great work!")
        
        # Update prediction
        prediction.success_probability = round(success_probability, 1)
        prediction.predicted_final_amount = round(predicted_final, 2)
        prediction.estimated_days_to_goal = max(1, int((float(self.funding_goal or 0) - total_donations) / max(daily_rate, 1)))
        prediction.predicted_peak_day = peak_day
        prediction.predicted_followers_7d = int(follower_count + (daily_growth_rate * 7))
        prediction.predicted_followers_30d = int(follower_count + (daily_growth_rate * 30))
        prediction.predicted_donors_7d = int(donor_count + (donor_count / max(total_days, 1) * 7))
        prediction.predicted_donors_30d = int(donor_count + (donor_count / max(total_days, 1) * 30))
        prediction.predicted_total_loves = int(love_count * 1.5)
        prediction.predicted_total_comments = int(comment_count * 1.5)
        prediction.predicted_total_shares = int(love_count * 0.8)
        prediction.avg_predicted_donation = round(avg_donation, 2)
        prediction.predicted_repeat_donor_rate = round(min(donor_count / max(follower_count, 1) * 100, 30), 1)
        prediction.risk_factors = risk_factors
        prediction.recommendations = recommendations
        prediction.confidence_score = round(min(70 + (total_days * 2), 95), 1)  # More data = higher confidence
        
        prediction.save()
        return prediction
    
    @classmethod
    def search_with_boosts(cls, search_term, user=None):
        """
        Perform search with boosted results at top
        Returns list of dicts with campaign and type info
        """
        from django.db.models import Q
        
        # Get active search boosts for this term
        boosted_journeys = BoostedJourney.objects.get_search_boosts(search_term)
        
        # Get boosted campaign IDs ordered by bid amount
        boosted_campaign_ids = [bj.campaign_id for bj in boosted_journeys]
        
        # Build base search query
        search_filter = Q(title__icontains=search_term) | Q(content__icontains=search_term)
        
        # Get all matching campaigns (excluding soft-deleted or inactive)
        all_campaigns = cls.objects.filter(
            search_filter,
            is_active=True
        ).select_related('user__user').prefetch_related(
            'loves', 'comments', 'boosted_journeys'
        )
        
        # Separate boosted and organic
        boosted_campaigns = []
        organic_campaigns = []
        
        for campaign in all_campaigns:
            if campaign.id in boosted_campaign_ids:
                # Get the boost info
                boost = next(
                    (bj for bj in boosted_journeys if bj.campaign_id == campaign.id), 
                    None
                )
                if boost:
                    boosted_campaigns.append({
                        'campaign': campaign,
                        'type': 'sponsored',
                        'boost': boost,
                        'bid_amount': boost.bid_amount
                    })
            else:
                organic_campaigns.append({
                    'campaign': campaign,
                    'type': 'organic'
                })
        
        # Sort boosted by bid amount (already ordered, but ensure)
        boosted_campaigns.sort(key=lambda x: x['bid_amount'], reverse=True)
        
        # Sort organic by love count or timestamp
        organic_campaigns.sort(
            key=lambda x: (
                x['campaign'].get_love_count(),
                x['campaign'].timestamp
            ), 
            reverse=True
        )
        
        return boosted_campaigns + organic_campaigns

    # ==================== SAVE METHOD ====================
    
    def save(self, *args, **kwargs):
        try:
            is_new = self.pk is None
            
            # Set journey start date for new campaigns
            if is_new and not self.journey_start_date:
                self.journey_start_date = timezone.now()
            
            # Set original duration for new campaigns
            if is_new:
                self.original_duration = self.duration
                self.original_duration_unit = self.duration_unit
                self.duration_last_updated = self.journey_start_date or self.timestamp
            
            # Calculate end date if duration exists
            if self.duration and self.duration_unit:
                self.end_date = self.calculate_end_date()
            
            # Set default funding goal if null
            if self.funding_goal is None:
                self.funding_goal = 0.00
            
            # Call the parent save method
            super().save(*args, **kwargs)
            
        except Exception as e:
            print(f"Error saving campaign: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e

    def calculate_end_date(self):
        try:
            if not self.duration or not self.duration_unit:
                return None
            
            base_time = self.journey_start_date or self.timestamp
            
            if self.duration_unit == 'minutes':
                return base_time + timedelta(minutes=self.duration)
            else:
                return base_time + timedelta(days=self.duration)
        except:
            return None

    def is_day_locked(self, day_number):
        """
        Check if a specific day is locked (future day that hasn't been reached yet)
        Returns True if the day is locked (cannot be posted yet)
        """
        try:
            current_day = self.get_current_day()
            # Day is locked if it's greater than the current real day
            # But days can still be edited if they're already posted
            return day_number > current_day
        except:
            return False
    
    def get_day_status(self, day_number):
        """
        Get the status of a specific day
        Returns: 'locked', 'available', or 'completed'
        """
        try:
            current_day = self.get_current_day()
            
            if day_number > current_day:
                return 'locked'
            elif day_number == current_day:
                return 'available'
            else:
                return 'completed'
        except:
            return 'locked'






# NEW: Campaign Follow through model
class CampaignFollow(models.Model):
    """Model to track users following campaigns"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaign_follows')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_follows')
    followed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'campaign')
        ordering = ['-followed_at']
        indexes = [
            models.Index(fields=['user', '-followed_at']),
            models.Index(fields=['campaign', '-followed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} follows {self.campaign.title}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create notification when someone follows a campaign
        if is_new:
            try:
                Notification.objects.create(
                    user=self.campaign.user.user,  # Campaign owner
                    message=f"{self.user.username} is now following your campaign '{self.campaign.title}'",
                    redirect_link=reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk}),
                    campaign_notification=True,
                    campaign=self.campaign
                )
            except Exception as e:
                print(f"Failed to create follow notification: {e}")


class Tag(models.Model):
    """Model for campaign tags"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CampaignView(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    time_spent = models.DurationField(default=timezone.timedelta(minutes=0))

    class Meta:
        unique_together = ('user', 'campaign')


class Conversation(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_user2')
    updated_at = models.DateTimeField(auto_now=True)
    
    blocked_by_user1 = models.BooleanField(default=False)
    blocked_by_user2 = models.BooleanField(default=False)
    
    muted_by_user1 = models.BooleanField(default=False)
    muted_by_user2 = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user1', 'user2']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"
    
    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        users = sorted([user1, user2], key=lambda u: u.id)
        
        conversation, created = cls.objects.get_or_create(
            user1=users[0],
            user2=users[1],
            defaults={'updated_at': timezone.now()}
        )
        return conversation, created
    
    def get_other_user(self, current_user):
        if current_user == self.user1:
            return self.user2
        return self.user1
    
    def get_unread_count(self, user):
        if user == self.user1 or user == self.user2:
            return self.messages.filter(
                recipient=user,
                read=False,
                deleted_by_recipient=False
            ).count()
        return 0
    
    def is_blocked_for_user(self, user):
        if user == self.user1:
            return self.blocked_by_user2
        elif user == self.user2:
            return self.blocked_by_user1
        return False
    
    def is_muted_for_user(self, user):
        if user == self.user1:
            return self.muted_by_user1
        elif user == self.user2:
            return self.muted_by_user2
        return False
    
    @property
    def last_message(self):
        return self.direct_messages.order_by('-timestamp').first()


class DirectMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='direct_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_direct_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    file = CloudinaryField(
        'file',
        folder='direct_messages_files',
        null=True,
        blank=True,
        resource_type='auto'
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    
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
        self.status = 'Approved'
        self.verified_on = timezone.now()
        self.save()
        Notification.objects.create(user=self.user, message=f"Your verification for {self.document_type} has been approved.")

    def reject(self, reason):
        self.status = 'Rejected'
        self.rejection_reason = reason
        self.save()
        self.notify_user()

    def notify_user(self):
        message = f"Your verification for {self.document_type} has been rejected. Reason: {self.rejection_reason}."
        Notification.objects.create(user=self.user, message=message)

    def __str__(self):
        return f"Verification of {self.user.username} - {self.document_type}"

    class Meta:
        verbose_name = 'User Verification'
        verbose_name_plural = 'User Verifications'
        ordering = ['-submission_date']




def default_content():
    return 'Default content'


class CampaignTag(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_tags')
    tag = models.ForeignKey('Tag', on_delete=models.CASCADE)
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


class Love(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='loves')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'campaign']),
        ]

    def save(self, *args, **kwargs):
        if self.pk is None:
            campaign_title = self.campaign.title
            message = f"{self.user.username} loved your cause '{campaign_title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
            Notification.objects.create(user=self.campaign.user.user, message=message)
        super().save(*args, **kwargs)


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
        if self.pk is None:
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
    is_like = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'comment')
    
    def __str__(self):
        return f"{'Like' if self.is_like else 'Dislike'} by {self.user.user.username} on comment {self.comment.id}"


from django.db import models, transaction

class Activity(models.Model):
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE)
    content = models.TextField(default='content')
    timestamp = models.DateTimeField(auto_now_add=True)

    file = CloudinaryField(
        'file',
        folder='activity_files',
        null=True,
        blank=True,
        resource_type='auto'
    )
    
    is_video = models.BooleanField(default=False, help_text="Whether this activity contains a video")
    video_processed = models.BooleanField(default=False, help_text="Whether video screenshots have been processed")
    screenshot_count = models.IntegerField(default=5, help_text="Number of screenshots to extract from video")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_file = self.file
    
    def _is_video_file(self, file):
        if not file:
            return False
        
        try:
            if hasattr(file, 'resource_type'):
                return file.resource_type == 'video'
            
            if hasattr(file, 'content_type'):
                return file.content_type.startswith('video/')
            
            if hasattr(file, 'url'):
                url = file.url.lower()
                video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v', '.mpg', '.mpeg']
                return any(ext in url for ext in video_extensions)
            
            if hasattr(file, 'name'):
                name = file.name.lower()
                video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v', '.mpg', '.mpeg']
                return any(name.endswith(ext) for ext in video_extensions)
            
            if hasattr(file, 'public_id'):
                public_id = file.public_id.lower()
                video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v', '.mpg', '.mpeg']
                return any(ext in public_id for ext in video_extensions)
            
        except (AttributeError, TypeError):
            pass
        
        return False
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        file_changed = False
        if self.pk and hasattr(self, '_original_file'):
            try:
                file_changed = str(self._original_file) != str(self.file)
            except:
                file_changed = True
        
        if (is_new or file_changed) and self.file:
            self.is_video = self._is_video_file(self.file)
            if self.is_video:
                self.video_processed = False
            else:
                self.video_processed = True
        
        super().save(*args, **kwargs)
        
        if is_new:
            transaction.on_commit(lambda: self.create_notifications_async())
    
    def create_notifications_async(self):
        try:
            from .models import Notification
            
            with transaction.atomic():
                message_owner = f"An activity was added to your cause '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
                Notification.objects.create(user=self.campaign.user.user, message=message_owner)
                
                # UPDATED: Send notifications to campaign followers instead of profile followers
                campaign_followers = self.campaign.followers.all()
                for follower in campaign_followers:
                    message_follower = f"New activity in a campaign you're following: '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Cause</a>"
                    Notification.objects.create(user=follower, message=message_follower)
                    
        except Exception as e:
            print(f"⚠️ Failed to create notifications for activity {self.id}: {e}")
    
    def create_notifications(self):
        self.create_notifications_async()
    
    @property
    def screenshots(self):
        return self.video_screenshots.all().order_by('order')
    
    @property
    def has_screenshots(self):
        return self.video_screenshots.exists()
    
    @property
    def display_media(self):
        if self.is_video and self.has_screenshots:
            return self.screenshots
        return None
    
    @property
    def day_number(self):
        if not self.campaign:
            return 1

        start_date = self.campaign.journey_start_date or self.campaign.timestamp

        if not start_date:
            return 1

        time_since_start = self.timestamp - start_date

        if self.campaign.duration_unit == 'minutes':
            minutes_since = int(time_since_start.total_seconds() / 60)
            day_num = minutes_since + 1
        else:
            days_since = time_since_start.days
            day_num = days_since + 1

        if self.campaign.duration and day_num > self.campaign.duration:
            return self.campaign.duration

        return max(1, day_num)


class VideoScreenshot(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='video_screenshots')
    image = CloudinaryField(
        'screenshot',
        folder='activity_screenshots',
        null=True,
        blank=True
    )
    timestamp = models.FloatField(help_text="Timestamp in seconds where screenshot was taken")
    order = models.IntegerField(default=0, help_text="Order in the story sequence")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['activity', 'order']
    
    def __str__(self):
        return f"Screenshot {self.order} for Activity {self.activity.id} at {self.timestamp}s"


class ActiveAudioSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_sessions')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='audio_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user']
        indexes = [
            models.Index(fields=['user', '-last_heartbeat']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Activity {self.activity.id}"


class ActivityLove(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='loves')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk is None:
            message = f"{self.user.username} loved an activity in your cause '{self.activity.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.activity.campaign.pk})}'>View Cause</a>"
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









class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    viewed = models.BooleanField(default=False)
    campaign_notification = models.BooleanField(default=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True)
    redirect_link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

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
        campaign_count = Campaign.objects.filter(user=user).count()
        
        if campaign_count >= 3:
            award = ChangemakerAward.GOLD
        elif campaign_count == 2:
            award = ChangemakerAward.SILVER
        else:
            award = ChangemakerAward.BRONZE

        latest_campaign = Campaign.objects.filter(user=user).latest('timestamp')

        if not ChangemakerAward.objects.filter(user=user, campaign=latest_campaign).exists():
            ChangemakerAward.objects.create(user=user, campaign=latest_campaign, award=award)

    @staticmethod
    def get_awards(user):
        return ChangemakerAward.objects.filter(user=user)


# marketing 
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
    
    title = models.CharField(max_length=255, help_text="Blog post title (max 255 characters)")
    slug = models.SlugField(unique=True, max_length=255, blank=True, 
                           help_text="URL-friendly version of the title")
    excerpt = models.TextField(max_length=500, blank=True, 
                              help_text="Short summary (shown in listings)")
    content = HTMLField(help_text="Full blog content")
    
    author = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, 
                              related_name='blog_posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, 
                                       help_text="Leave empty for immediate publication")
    
    meta_title = models.CharField(max_length=60, blank=True, 
                                 help_text="SEO title tag (50-60 characters optimal)")
    meta_description = models.TextField(max_length=160, blank=True, 
                                       help_text="SEO description (150-160 characters optimal)")
    focus_keyword = models.CharField(max_length=50, blank=True, 
                                    help_text="Primary keyword for SEO")
    canonical_url = models.URLField(max_length=500, blank=True, 
                                   help_text="Canonical URL if republished from elsewhere")
    
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
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    tags = models.CharField(max_length=255, blank=True, 
                           help_text="Comma-separated tags")
    
    estimated_reading_time = models.PositiveIntegerField(default=5, 
                                                        help_text="Minutes to read")
    view_count = models.PositiveIntegerField(default=0, editable=False)
    like_count = models.PositiveIntegerField(default=0, editable=False)
    share_count = models.PositiveIntegerField(default=0, editable=False)
    
    seo_score = models.PositiveIntegerField(default=0, editable=False, 
                                           help_text="Auto-calculated SEO score")
    
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
        if not self.slug:
            base_slug = slugify(self.title)[:250]
            slug = base_slug
            counter = 1
            while Blog.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        if not self.meta_title:
            self.meta_title = self.title[:60]
        
        if not self.meta_description:
            clean_text = re.sub('<[^<]+?>', '', self.content)
            self.meta_description = clean_text[:160]
        
        if not self.excerpt:
            clean_text = re.sub('<[^<]+?>', '', self.content)
            self.excerpt = clean_text[:500]
        
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        self.calculate_seo_score()
        
        super().save(*args, **kwargs)
    
    def calculate_seo_score(self):
        score = 0
        
        title_len = len(self.meta_title or self.title)
        if 50 <= title_len <= 60:
            score += 20
        elif 40 <= title_len <= 70:
            score += 10
        
        desc_len = len(self.meta_description or '')
        if 150 <= desc_len <= 160:
            score += 20
        elif 130 <= desc_len <= 170:
            score += 10
        
        word_count = len(self.content.split())
        if word_count >= 2000:
            score += 30
        elif word_count >= 1000:
            score += 20
        elif word_count >= 500:
            score += 10
        
        if self.featured_image:
            score += 10
        
        if self.focus_keyword:
            score += 10
        
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
        words_per_minute = 200
        return max(1, round(len(self.content.split()) / words_per_minute))


class CampaignStory(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()

    image = CloudinaryField(
        'image',
        folder='story_images',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
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



# Add these models to your models.py file

class CampaignWatchTime(models.Model):
    """Track how long users watch each campaign"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='watch_times')
    session_id = models.CharField(max_length=100, blank=True)  # For anonymous users
    watch_time_seconds = models.FloatField(default=0)  # Total seconds watched
    completed = models.BooleanField(default=False)  # Did they watch the whole journey?
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['campaign', '-watch_time_seconds']),
            models.Index(fields=['user', 'campaign']),
        ]
    
    def __str__(self):
        return f"{self.user or 'Anonymous'} watched {self.campaign.title} for {self.watch_time_seconds}s"


class CampaignSave(models.Model):
    """Track users who save/bookmark campaigns"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'campaign')
        indexes = [
            models.Index(fields=['campaign', '-saved_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} saved {self.campaign.title}"


class CampaignShare(models.Model):
    """Track how many times campaigns are shared"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='shares')
    shared_at = models.DateTimeField(auto_now_add=True)
    platform = models.CharField(max_length=50, blank=True)  # twitter, facebook, copy link, etc.
    
    class Meta:
        indexes = [
            models.Index(fields=['campaign', '-shared_at']),
        ]
    
    def __str__(self):
        return f"{self.user or 'Anonymous'} shared {self.campaign.title}"




# ============================================================================
# BOOSTED JOURNEY / MONETIZATION MODELS
# ============================================================================

# FIRST: Define the Manager
class BoostedJourneyManager(models.Manager):
    def get_active_for_placement(self, placement_type):
        """Get all active boosts for a specific placement"""
        now = timezone.now()
        return self.filter(
            placement_type=placement_type,
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        )
    
    def get_search_boosts(self, search_terms):
        """
        Get active search boosts matching keywords
        Returns: bids first (highest), then flat fees (highest)
        """
        now = timezone.now()
        
        # Split search terms into list
        if isinstance(search_terms, str):
            search_words = search_terms.lower().split()
        else:
            search_words = search_terms
        
        # Build Q objects for keyword matching
        keyword_queries = models.Q()
        for word in search_words:
            keyword_queries |= models.Q(keywords__icontains=word)
        
        # Get all matching boosts
        all_boosts = self.filter(
            placement_type='search',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        ).filter(keyword_queries)
        
        # Separate and order: bids first by amount, then flat fees by amount
        bid_boosts = all_boosts.filter(bid_amount__gt=0).order_by('-bid_amount')
        flat_boosts = all_boosts.filter(bid_amount=0, flat_fee__gt=0).order_by('-flat_fee')
        
        # Combine: all bids first, then all flat fees
        return list(bid_boosts) + list(flat_boosts)
    
    def get_featured_boosts(self, limit=5):
        """
        Get active featured section boosts with weighted rotation
        Higher payment = more chances to appear
        """
        now = timezone.now()
        
        # Get all active featured boosts
        boosts = self.filter(
            placement_type='featured',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        if not boosts.exists():
            return []
        
        # Create weighted list: every $10 = 1 entry in the pool
        weighted_pool = []
        for boost in boosts:
            # Minimum weight of 1, even for $1
            weight = max(1, int(boost.flat_fee / 10))
            weighted_pool.extend([boost] * weight)
        
        # Select randomly from weighted pool without duplicates
        selected = []
        selected_ids = set()
        
        # Shuffle for randomness
        import random
        random.shuffle(weighted_pool)
        
        for boost in weighted_pool:
            if len(selected) >= limit:
                break
            if boost.id not in selected_ids:
                selected.append(boost)
                selected_ids.add(boost.id)
        
        # If we need more, fill with remaining boosts
        if len(selected) < limit:
            remaining = boosts.exclude(id__in=selected_ids).order_by('?')
            selected.extend(list(remaining)[:limit - len(selected)])
        
        return selected
    
    def get_category_boosts(self, category, limit=3):
        """
        Get active category page boosts for specific category
        Ordered by flat_fee (highest first)
        """
        now = timezone.now()
        return self.filter(
            placement_type='category',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now,
            categories__icontains=category
        ).order_by('-flat_fee')[:limit]
    
    def get_bundled_boosts(self):
        """Get active bundle placements"""
        now = timezone.now()
        return self.filter(
            placement_type='bundle',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        )

# SECOND: Define the BoostedJourney model
class BoostedJourney(models.Model):
    """
    Model for campaign boosting/promotion across different placement types
    """
    PLACEMENT_CHOICES = (
        ('featured', 'Featured Section (Right Sidebar)'),
        ('search', 'Search Results Top Spot'),
        ('category', 'Category Page Spotlight'),
        ('bundle', 'All Placements Bundle'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('pending', 'Pending Payment'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )
    
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='boosted_journeys')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_boosts')
    
    # Placement & targeting
    placement_type = models.CharField(max_length=20, choices=PLACEMENT_CHOICES)
    keywords = models.CharField(max_length=500, blank=True, 
                               help_text="Comma-separated keywords for search targeting")
    categories = models.CharField(max_length=500, blank=True,
                                 help_text="Comma-separated categories for category targeting")
    
    # Bidding & pricing
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                    help_text="Bid amount for search auctions (if applicable)")
    flat_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                  help_text="Flat fee for non-auction placements")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Duration & scheduling
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    duration_days = models.PositiveIntegerField(default=3, help_text="Duration in days")
    
    # Status & tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=255, blank=True, help_text="PayPal transaction ID")
    
    # Performance tracking
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    last_impression_at = models.DateTimeField(null=True, blank=True)
    last_click_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add the manager here
    objects = BoostedJourneyManager()
    
    class Meta:
        indexes = [
            models.Index(fields=['placement_type', 'status', 'end_date']),
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['keywords']),  # For search matching
            models.Index(fields=['-bid_amount']),  # For auction sorting
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.campaign.title} - {self.get_placement_type_display()}"
    
    def save(self, *args, **kwargs):
        # Calculate end date based on duration if not set
        if not self.end_date and self.duration_days:
            self.end_date = self.start_date + timedelta(days=self.duration_days)
        
        # Calculate total paid based on placement type
        if not self.total_paid and self.flat_fee:
            self.total_paid = self.flat_fee
        
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if boost is currently active"""
        now = timezone.now()
        return (self.status == 'active' and 
                self.start_date <= now <= self.end_date and 
                self.is_paid)
    
    @property
    def days_remaining(self):
        """Get days remaining in boost period"""
        if not self.is_active:
            return 0
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)
    
    @property
    def click_through_rate(self):
        """Calculate CTR as percentage"""
        if self.impressions > 0:
            return round((self.clicks / self.impressions) * 100, 2)
        return 0
    
    def record_impression(self):
        """Record an impression for this boost"""
        self.impressions += 1
        self.last_impression_at = timezone.now()
        self.save(update_fields=['impressions', 'last_impression_at'])
    
    def record_click(self):
        """Record a click for this boost"""
        self.clicks += 1
        self.last_click_at = timezone.now()
        self.save(update_fields=['clicks', 'last_click_at'])
    
    def activate(self):
        """Activate the boost after payment"""
        self.status = 'active'
        self.is_paid = True
        self.start_date = timezone.now()
        if self.duration_days:
            self.end_date = self.start_date + timedelta(days=self.duration_days)
        self.save()
    
    def expire(self):
        """Mark boost as expired"""
        self.status = 'expired'
        self.save()


# THIRD: Define the other related models
class BoostedJourneyImpression(models.Model):
    """Track individual impressions for analytics"""
    boosted_journey = models.ForeignKey(BoostedJourney, on_delete=models.CASCADE, 
                                       related_name='impression_records')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    placement_context = models.CharField(max_length=50, blank=True,  # 'search', 'category', 'featured'
                                       help_text="Where the impression occurred")
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['boosted_journey', '-viewed_at']),
            models.Index(fields=['placement_context', '-viewed_at']),
        ]
    
    def __str__(self):
        return f"Impression for {self.boosted_journey} at {self.viewed_at}"


class BoostedJourneyClick(models.Model):
    """Track individual clicks for analytics"""
    boosted_journey = models.ForeignKey(BoostedJourney, on_delete=models.CASCADE,
                                       related_name='click_records')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    placement_context = models.CharField(max_length=50, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['boosted_journey', '-clicked_at']),
        ]
    
    def __str__(self):
        return f"Click for {self.boosted_journey} at {self.clicked_at}"


class KeywordBidAuction(models.Model):
    """
    Track keyword bidding auction history
    """
    keyword = models.CharField(max_length=100, db_index=True)
    boosted_journey = models.ForeignKey(BoostedJourney, on_delete=models.CASCADE,
                                       related_name='bid_auctions')
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    position = models.PositiveIntegerField(help_text="Auction position at time of bid")
    auction_date = models.DateTimeField(auto_now_add=True)
    was_winning = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['keyword', '-auction_date']),
        ]
        ordering = ['-auction_date']
    
    def __str__(self):
        return f"{self.keyword} - ${self.bid_amount} (Position {self.position})"


class BoostedJourneyPackage(models.Model):
    """
    Pre-defined packages for easy purchasing
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    
    # Placement types included
    include_featured = models.BooleanField(default=False)
    include_search = models.BooleanField(default=False)
    include_category = models.BooleanField(default=False)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.PositiveIntegerField(default=0, 
                                                      help_text="Discount compared to buying separately")
    
    # Duration
    duration_days = models.PositiveIntegerField(default=7)
    
    # Features
    max_keywords = models.PositiveIntegerField(default=5, help_text="Max keywords for search targeting")
    priority_support = models.BooleanField(default=False)
    analytics_access = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def placement_count(self):
        count = 0
        if self.include_featured:
            count += 1
        if self.include_search:
            count += 1
        if self.include_category:
            count += 1
        return count



# ============================================================================
# EXISTING MONETIZATION MODELS - DO NOT MODIFY
# ============================================================================
# These models are already implemented and working:
# - Donation, Pledge, CampaignProduct, Transaction, Cart, CartItem
# ============================================================================


# models.py - Add this after your Activity model

class PostJourneyProduct(models.Model):
    """Products creators can sell after journey completes"""
    
    PRODUCT_TYPES = (
        ('blueprint', 'Blueprint PDF'),
        ('behind_scenes', 'Behind the Scenes Video'),
        ('coaching', 'One-on-One Coaching'),
        ('bundle', 'Complete Bundle'),
    )
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='post_journey_products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    
    # For blueprint (PDF)
    pdf_file = CloudinaryField('pdf', folder='post_journey_pdfs', null=True, blank=True, resource_type='raw')
    
    # For behind scenes (video)
    video_file = CloudinaryField('video', folder='post_journey_videos', null=True, blank=True, resource_type='video')
    
    # For coaching
    coaching_calendar_link = models.URLField(blank=True, help_text="Google Calendar or Calendly link")
    coaching_duration = models.IntegerField(default=60, help_text="Minutes per session")
    
    # For bundle (combines multiple)
    bundle_products = models.ManyToManyField('self', blank=True, symmetrical=False, 
                                             help_text="Products included in bundle")
    
    # Stats
    sold_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.campaign.title} - {self.get_product_type_display()}"





# Add to your models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count, Avg, Sum
import json

class PremiumSubscription(models.Model):
    """Tracks premium subscriptions for users"""
    PLAN_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trial', 'Trial'),
    )
    
    # Pricing (you can adjust these)
    PRICING = {
        'monthly': 9.99,
        'yearly': 79.99,  # 2 months free
        'lifetime': 299.99,
    }
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='premium_subscriptions')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    
    # Payment info (placeholder for now)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Features access flags
    can_view_advanced_stats = models.BooleanField(default=True)
    can_export_data = models.BooleanField(default=True)
    can_compare_campaigns = models.BooleanField(default=True)
    can_access_predictive = models.BooleanField(default=True)
    can_view_demographics = models.BooleanField(default=True)
    can_view_trends = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['end_date']),
            models.Index(fields=['user', '-start_date']),
        ]
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        if self.status == 'active' or self.status == 'trial':
            if self.end_date and self.end_date < timezone.now():
                return False
            return True
        return False
    
    @property
    def days_remaining(self):
        """Get days remaining in subscription"""
        if not self.end_date:
            return None
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)
    
    @property
    def price(self):
        """Get price for this plan"""
        return self.PRICING.get(self.plan, 0)
    
    def get_features_list(self):
        """Get list of active features"""
        features = []
        if self.can_view_advanced_stats:
            features.append('Advanced Statistics')
        if self.can_export_data:
            features.append('Data Export')
        if self.can_compare_campaigns:
            features.append('Campaign Comparison')
        if self.can_access_predictive:
            features.append('AI Predictions')
        if self.can_view_demographics:
            features.append('Donor Demographics')
        if self.can_view_trends:
            features.append('Trend Analysis')
        return features
    
    def cancel(self):
        """Cancel subscription"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save()
    
    def renew(self):
        """Renew subscription for another period"""
        if self.plan == 'monthly':
            self.end_date = timezone.now() + timedelta(days=30)
        elif self.plan == 'yearly':
            self.end_date = timezone.now() + timedelta(days=365)
        elif self.plan == 'lifetime':
            self.end_date = None
        
        self.status = 'active'
        self.start_date = timezone.now()
        self.save()
    
    @classmethod
    def get_user_subscription(cls, user):
        """Get user's active subscription"""
        if not user.is_authenticated:
            return None
        
        return cls.objects.filter(
            user=user,
            status__in=['active', 'trial']
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
        ).first()
    
    @classmethod
    def start_trial(cls, user):
        """Start a 14-day trial for user"""
        # Check if user already had a trial
        existing_trial = cls.objects.filter(
            user=user,
            plan='trial'
        ).exists()
        
        if existing_trial:
            return None
        
        trial = cls.objects.create(
            user=user,
            plan='monthly',
            status='trial',
            trial_end_date=timezone.now() + timedelta(days=14),
            end_date=timezone.now() + timedelta(days=14)
        )
        
        return trial


class CampaignPremiumAccess(models.Model):
    """One-time purchases for individual campaign stats"""
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='premium_access')
    purchased_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchased_campaign_stats')
    purchase_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)  # Null = lifetime
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment info
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['campaign', 'purchased_by']),
            models.Index(fields=['expiry_date']),
        ]
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"{self.purchased_by.username} - {self.campaign.title}"
    
    @property
    def is_valid(self):
        if not self.expiry_date:
            return True
        return self.expiry_date > timezone.now()


class CampaignPrediction(models.Model):
    """Store AI predictions for campaigns"""
    campaign = models.OneToOneField('Campaign', on_delete=models.CASCADE, related_name='prediction')
    last_updated = models.DateTimeField(auto_now=True)
    
    # Success prediction
    success_probability = models.FloatField(default=0, help_text="0-100% chance of reaching funding goal")
    predicted_final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timeline predictions
    estimated_days_to_goal = models.IntegerField(default=0, help_text="Predicted days until funding goal reached")
    predicted_peak_day = models.IntegerField(default=0, help_text="Day when engagement will peak")
    
    # Growth predictions
    predicted_followers_7d = models.IntegerField(default=0)
    predicted_followers_30d = models.IntegerField(default=0)
    predicted_donors_7d = models.IntegerField(default=0)
    predicted_donors_30d = models.IntegerField(default=0)
    
    # Engagement predictions
    predicted_total_loves = models.IntegerField(default=0)
    predicted_total_comments = models.IntegerField(default=0)
    predicted_total_shares = models.IntegerField(default=0)
    
    # Donor insights
    avg_predicted_donation = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    predicted_repeat_donor_rate = models.FloatField(default=0)
    
    # Risk factors
    risk_factors = models.JSONField(default=list, help_text="List of risk factors identified")
    recommendations = models.JSONField(default=list, help_text="AI recommendations to improve")
    
    # Confidence score
    confidence_score = models.FloatField(default=0, help_text="AI confidence in predictions 0-100%")
    
    # Add these fields
    seven_day_trend = models.JSONField(default=dict, help_text="7-day prediction percentages")
    peak_day_name = models.CharField(max_length=20, default="Day 5")
    
    def save(self, *args, **kwargs):
        # Generate 7-day trend
        if not self.seven_day_trend:
            self.seven_day_trend = {
                'day1': 60,
                'day2': 65,
                'day3': 72,
                'day4': 80,
                'day5': 85,
                'day6': 82,
                'day7': 78
            }
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['campaign', '-last_updated']),
        ]
    
    def __str__(self):
        return f"Prediction for {self.campaign.title}"
    
    def get_risk_factors_display(self):
        """Get formatted risk factors"""
        return [factor for factor in self.risk_factors if factor]
    
    def get_recommendations_display(self):
        """Get formatted recommendations"""
        return [rec for rec in self.recommendations if rec]


class CampaignAnalytics(models.Model):
    """Advanced analytics for campaigns"""
    campaign = models.OneToOneField('Campaign', on_delete=models.CASCADE, related_name='analytics')
    last_updated = models.DateTimeField(auto_now=True)
    
    # Donor demographics
    donor_demographics = models.JSONField(default=dict, help_text="Age, location, etc.")
    donor_retention_rate = models.FloatField(default=0)
    avg_donation_per_donor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Engagement metrics
    engagement_rate = models.FloatField(default=0)
    viral_coefficient = models.FloatField(default=0, help_text="How many new users each user brings")
    share_conversion_rate = models.FloatField(default=0)
    
    # Time-based metrics
    best_posting_times = models.JSONField(default=list)
    peak_hours = models.JSONField(default=list)
    
    # Trend analysis
    growth_trend = models.CharField(max_length=20, choices=(
        ('accelerating', 'Accelerating'),
        ('steady', 'Steady'),
        ('slowing', 'Slowing'),
        ('declining', 'Declining'),
    ), default='steady')
    
    predicted_trend = models.JSONField(default=list, help_text="7-day prediction data points")
    # Add these fields
    avg_engagement_rate = models.FloatField(default=3.2)
    peak_activity_times = models.JSONField(default=dict)
    best_posting_time = models.CharField(max_length=50, default="Thursday 7PM")
    
    def calculate_peak_times(self):
        """Calculate peak activity times from real data"""
        # Implement based on your activity logs
        pass
    class Meta:
        indexes = [
            models.Index(fields=['campaign', '-last_updated']),
        ]

class OwnerTrial(models.Model):
    """Track 30-day free trials for campaign owners"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='owner_trials')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaign_trials')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('campaign', 'owner')
        indexes = [
            models.Index(fields=['owner', 'is_active', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Trial for {self.campaign.title} - {self.owner.username}"
    
    @property
    def days_remaining(self):
        remaining = self.expires_at - timezone.now()
        return max(0, remaining.days)
    
    def is_valid(self):
        return self.is_active and self.expires_at > timezone.now()
    
    def check_expiry(self):
        """Auto-expire if past date"""
        if self.is_active and self.expires_at <= timezone.now():
            self.is_active = False
            self.save()
            return True
        return False

class Share(models.Model):
    """Track shares of campaigns"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='share_records')  # Changed from 'shares'
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.CharField(max_length=20, choices=(
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('whatsapp', 'WhatsApp'),
        ('linkedin', 'LinkedIn'),
        ('copy', 'Copy Link'),
        ('other', 'Other'),
    ), default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['campaign', '-created_at']),
        ]
        verbose_name = 'Share Record'
        verbose_name_plural = 'Share Records'
    
    def __str__(self):
        return f"Share of {self.campaign.title} on {self.platform}"





    
    def __str__(self):
        return f"Share of {self.campaign.title} on {self.platform}"

class CampaignComparison(models.Model):
    """Saved campaign comparisons"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_comparisons')
    name = models.CharField(max_length=100)
    campaigns = models.ManyToManyField('Campaign', related_name='comparisons')
    created_at = models.DateTimeField(auto_now_add=True)
    last_viewed = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['share_token']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def get_campaign_count(self):
        return self.campaigns.count()
    
    def generate_share_token(self):
        import secrets
        self.share_token = secrets.token_urlsafe(32)
        self.save()
        return self.share_token


class ExportJob(models.Model):
    """Track data export jobs"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    EXPORT_TYPES = (
        ('campaign_stats', 'Campaign Statistics'),
        ('donor_data', 'Donor Data'),
        ('predictions', 'Predictions'),
        ('comparison', 'Comparison'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_jobs')
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_url = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    parameters = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.export_type} ({self.status})"
    
    def mark_completed(self, file_url):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.file_url = file_url
        self.save()
    
    def mark_failed(self, error):
        self.status = 'failed'
        self.error_message = str(error)
        self.save()



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
    paypal_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    paypal_payout_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} donated ${self.amount} to {self.campaign.title}"


class Pledge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='pledges')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    contact = models.EmailField(blank=True, null=True)
    is_fulfilled = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    anonymous_name = models.CharField(max_length=100, blank=True, null=True)

    paypal_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    paypal_payout_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='pending', choices=(
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ))
    
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
        if self.stock_status == 'out_of_stock':
            return "Out of Stock"
        elif self.stock_status == 'low_stock':
            return f"Only {self.stock_quantity} left"
        elif self.stock_status == 'preorder':
            return "Available for Preorder"
        elif self.stock_status == 'discontinued':
            return "Discontinued"
        else:
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
        
        if self.product.stock_quantity >= self.quantity:
            self.product.stock_quantity -= self.quantity
            self.product.save()


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


from django.db.models.signals import post_delete
from django.dispatch import receiver
from cloudinary.uploader import destroy
from .models import Campaign

@receiver(post_delete, sender=Campaign)
def delete_campaign_files(sender, instance, **kwargs):
    if instance.poster:
        destroy(instance.poster.public_id)

    if instance.audio:
        destroy(instance.audio.public_id, resource_type="video")

# ============================================================================
# FUTURE MONETIZATION MODELS - PHASE 2 & 3 (EXCLUDING SOUND TRIBE)
# ============================================================================
# NEXT STRATEGY TO IMPLEMENT: Transaction Fee on Donations (3-5%)
#
# Implementation order recommendation (per your monetization plan):
# PHASE 2 (Year 2-3):
# 1. ⬜ Transaction Fee on Donations (CURRENT - to be implemented)
# 2. ⬜ Optional Tips for Platform (next)
# 3. ⬜ Featured Listings (next)
#
# PHASE 3 (Year 3-4):
# 4. ⬜ Creator Subscription (Tiers)
# 5. ⬜ Super Likes/Spotlight
#
# PHASE 4 (Year 4-5):
# 6. ⬜ Brand/Corporate Partnerships
# 7. ⬜ API Access for Developers
# 8. ⬜ Data Insights Reports
# 9. ⬜ Journey Completion Awards
#
# PHASE 5 (Year 5+):
# 10. ⬜ Marketplace (for merchandise)
# 11. ⬜ Journey Consulting/Coaching
# 12. ⬜ Impact Investment Platform
# 13. ⬜ White Label Solution
#
# NOTE: Sound Tribe monetization should be implemented separately in Phase 3.
# ============================================================================

# === PHASE 2: INITIAL MONETIZATION ===

class PlatformFee(models.Model):
    """Model for tracking transaction fees on donations/pledges"""
    # To be implemented when adding transaction fees
    pass


class PlatformTip(models.Model):
    """Model for optional tips to support the platform during checkout"""
    # To be implemented when adding optional tips
    pass


class FeaturedListing(models.Model):
    """Model for creators paying to have their cause featured"""
    # To be implemented when adding featured listings
    pass


# === PHASE 3: PREMIUM FEATURES ===

class CreatorSubscription(models.Model):
    """Model for creator subscription tiers (Pro, Organization)"""
    # To be implemented when adding creator subscriptions
    pass


class SuperLike(models.Model):
    """Model for supporters paying to spotlight a cause"""
    # To be implemented when adding super likes/spotlight
    pass


# === PHASE 4: ADVANCED MONETIZATION ===

class BrandPartnership(models.Model):
    """Model for corporate sponsorships and brand partnerships"""
    # To be implemented when adding brand partnerships
    pass


class APIAccess(models.Model):
    """Model for developer API access tiers"""
    # To be implemented when adding API access
    pass


class DataInsightReport(models.Model):
    """Model for selling anonymized trend reports"""
    # To be implemented when adding data insights
    pass


class JourneyCompletionAward(models.Model):
    """Model for physical awards/merchandise for completed journeys"""
    # To be implemented when adding completion awards
    pass


# === PHASE 5: ECOSYSTEM MONETIZATION ===

class Marketplace(models.Model):
    """Model for creators selling merchandise related to their cause"""
    # To be implemented when adding marketplace
    pass


class ConsultingBooking(models.Model):
    """Model for connecting experienced changemakers with new creators"""
    # To be implemented when adding consulting/coaching
    pass


class ImpactInvestment(models.Model):
    """Model for connecting causes with larger investors/foundations"""
    # To be implemented when adding impact investment platform
    pass


class WhiteLabelInstance(models.Model):
    """Model for corporate white-label solutions"""
    # To be implemented when adding white label solutions
    pass


# In your models.py, add these indexes:
class Meta:
    indexes = [
        models.Index(fields=['-timestamp']),
        models.Index(fields=['campaign', '-timestamp']),
        models.Index(fields=['user', '-timestamp']),
    ]








