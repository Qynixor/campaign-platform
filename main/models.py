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

class Campaign(models.Model):
    user = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='user_campaigns')
    title = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    journey_start_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    content = models.TextField(max_length=150)
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
    
    is_active = models.BooleanField(default=True)
    premium_activated = models.BooleanField(default=False, help_text="Whether premium stats have been activated for this campaign")   
    
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
        ('Religious & Spiritual Causes', 'Religious & Spiritual Causes'),  # NEW CATEGORY
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
        'Religious & Spiritual Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201319/peace_lgzimr.mp3',  # Peaceful audio for religious causes
        'Other Causes': 'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3',
    }

    def get_default_audio(self):
        return self.DEFAULT_CATEGORY_AUDIO.get(
            self.category,
            'https://res.cloudinary.com/dvlgdzood/video/upload/v1765201313/Equality_h3fufa.mp3'
        )

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
    
    funding_goal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,
        blank=True,
        default=0.00
    )
    
    tags = models.ManyToManyField('Tag', through='CampaignTag', related_name='campaigns', blank=True)
    
    # Campaign following system
    followers = models.ManyToManyField(
        User, 
        through='CampaignFollow',
        related_name='following_campaigns',
        blank=True,
        help_text="Users following this campaign"
    )

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
        try:
            return self.loves.count()
        except:
            return 0
    
    @property
    def is_changemaker(self):
        return False

    # ==================== TIME/DURATION PROPERTIES ====================
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

    @property
    def elapsed_time(self):
        try:
            start_date = self.journey_start_date or self.timestamp
            elapsed = timezone.now() - start_date
            return elapsed
        except:
            return timedelta(0)
    
    @property
    def remaining_percentage(self):
        try:
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
        except:
            return 100

    # ==================== FIXED DAY TRACKING METHODS ====================
    def get_current_day(self):
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

    def is_day_locked(self, day_number):
        try:
            current_day = self.get_current_day()
            return day_number > current_day
        except:
            return True

    def get_day_unlock_date(self, day_number):
        try:
            start_date = self.journey_start_date or self.timestamp
            
            if day_number <= 1:
                return start_date
            
            if self.duration_unit == 'minutes':
                unlock_time = start_date + timedelta(minutes=day_number - 1)
            else:
                unlock_time = start_date + timedelta(days=day_number - 1)
            
            return unlock_time
        except:
            return timezone.now()

    def get_day_status(self, day_number):
        try:
            now = timezone.now()
            current_day = self.get_current_day()
            
            if day_number < current_day:
                return {
                    'status': 'completed',
                    'can_upload': False,
                    'message': f'Day {day_number} completed',
                    'unlock_date': None,
                    'unlock_date_formatted': None,
                    'hours_remaining': 0,
                    'days_remaining': 0,
                }
            
            elif day_number == current_day:
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
                unlock_date = self.get_day_unlock_date(day_number)
                time_until_unlock = unlock_date - now
                
                days_remaining = time_until_unlock.days
                hours_remaining = int(time_until_unlock.total_seconds() / 3600)
                minutes_remaining = int(time_until_unlock.total_seconds() / 60)
                
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
                    'unlock_date_formatted': unlock_date.strftime('%b %d, %Y at %I:%M %p') if unlock_date else None,
                    'days_remaining': days_remaining,
                    'hours_remaining': hours_remaining,
                    'minutes_remaining': minutes_remaining,
                }
        except Exception as e:
            return {
                'status': 'error',
                'can_upload': False,
                'message': 'Error loading day status',
                'unlock_date': None,
                'unlock_date_formatted': None,
                'hours_remaining': 0,
                'days_remaining': 0,
            }

    def get_day_range(self, max_days=None):
        try:
            if max_days:
                return range(1, max_days + 1)
            elif self.duration:
                return range(1, self.duration + 1)
            else:
                return range(1, 8)
        except:
            return range(1, 8)

    def get_completed_days_count(self):
        try:
            if hasattr(self, 'activity_set'):
                return self.activity_set.count()
            return 0
        except:
            return 0

    def get_remaining_days_count(self):
        try:
            if not self.duration:
                return 0
            completed = self.get_completed_days_count()
            return max(0, self.duration - completed)
        except:
            return 0

    # Campaign follower methods
    @property
    def follower_count(self):
        try:
            return self.followers.count()
        except:
            return 0
    
    def is_followed_by(self, user):
        """Check if a user follows this campaign"""
        try:
            if not user or not user.is_authenticated:
                return False
            return self.followers.filter(id=user.id).exists()
        except:
            return False

    # ==================== FIXED SAVE METHOD ====================
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
            
            # CRITICAL: Call the parent save method
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

    def notify_visible_to_followers(self):
        pass

    def award_changemaker_status(self):
        try:
            from .models import ChangemakerAward
            
            if not ChangemakerAward.objects.filter(user=self.user, campaign=self).exists():
                changemaker_campaigns = Campaign.objects.filter(user=self.user, activity__isnull=False).distinct()
                campaign_count = changemaker_campaigns.count()
                if campaign_count >= 3:
                    award_type = 'Gold'
                elif campaign_count >= 2:
                    award_type = 'Silver'
                else:
                    award_type = 'Bronze'

                ChangemakerAward.objects.create(
                    user=self.user,
                    campaign=self,
                    award=award_type,
                    timestamp=timezone.now()
                )
        except:
            pass

    # ==================== ENHANCED STATS METHODS (SAFE VERSION) ====================
    
    def get_avg_daily_views(self):
        """Calculate average daily views"""
        return 0
    
    def get_new_followers_last_7_days(self):
        """Count new followers in the last 7 days"""
        try:
            seven_days_ago = timezone.now() - timedelta(days=7)
            if hasattr(self, 'campaign_follows'):
                return self.campaign_follows.filter(
                    followed_at__gte=seven_days_ago
                ).count()
            return 0
        except:
            return 0
    
    def get_new_followers_last_30_days(self):
        """Count new followers in the last 30 days"""
        try:
            thirty_days_ago = timezone.now() - timedelta(days=30)
            if hasattr(self, 'campaign_follows'):
                return self.campaign_follows.filter(
                    followed_at__gte=thirty_days_ago
                ).count()
            return 0
        except:
            return 0
    
    def get_follower_growth_rate(self):
        """Calculate follower growth rate (percentage)"""
        try:
            total = self.follower_count
            if total == 0:
                return 0
            
            new_7d = self.get_new_followers_last_7_days()
            return round((new_7d / total) * 100, 1)
        except:
            return 0
    
    def get_avg_donation(self):
        """Calculate average donation amount"""
        try:
            if hasattr(self, 'donations'):
                donations = self.donations.filter(fulfilled=True)
                avg = donations.aggregate(avg=Avg('amount'))['avg']
                return float(avg) if avg else 0
            return 0
        except:
            return 0
    
    def get_total_donors(self):
        """Count unique donors"""
        try:
            if hasattr(self, 'donations'):
                return self.donations.filter(fulfilled=True).values('user').distinct().count()
            return 0
        except:
            return 0
    
    def get_total_pledgers(self):
        """Count unique pledgers"""
        try:
            if hasattr(self, 'pledges'):
                return self.pledges.values('user').distinct().count()
            return 0
        except:
            return 0
    
    def get_donation_conversion_rate(self):
        """Percentage of followers who donated"""
        try:
            followers = self.follower_count
            if followers == 0:
                return 0
            
            donors = self.get_total_donors()
            return round((donors / followers) * 100, 1)
        except:
            return 0
    
    def get_activity_completion_rate(self):
        """Percentage of days completed vs total duration"""
        try:
            if not self.duration or self.duration == 0:
                return 0
            
            if not hasattr(self, 'activity_set'):
                return 0
                
            completed = self.activity_set.count()
            if completed == 0:
                return 0
                
            return round((completed / self.duration) * 100, 1)
        except:
            return 0
    
    def get_engagement_score(self):
        """Calculate overall engagement score (0-100)"""
        try:
            score = 0
            follower_count = self.follower_count
            
            if follower_count == 0:
                return 0
            
            # Love engagement (40% of score)
            love_ratio = self.love_count / follower_count
            score += min(love_ratio * 40, 40)
            
            # Comment engagement (30% of score)
            try:
                if hasattr(self, 'comments'):
                    comment_count = self.comments.count()
                    if comment_count > 0:
                        comment_ratio = comment_count / follower_count
                        score += min(comment_ratio * 30, 30)
            except:
                pass
            
            # Activity consistency (30% of score)
            completion_rate = self.get_activity_completion_rate()
            if completion_rate > 0:
                score += (completion_rate / 100) * 30
            
            return min(round(score), 100)
        except:
            return 0
    
    def get_category_ranking(self):
        """Get campaign's ranking in its category"""
        try:
            return {
                'rank': 'N/A',
                'total': Campaign.objects.filter(category=self.category).count(),
                'percentile': 'N/A'
            }
        except:
            return {
                'rank': 'N/A',
                'total': 0,
                'percentile': 'N/A'
            }
    
    def get_daily_stats(self, days=7):
        """Get daily stats for charts"""
        try:
            from django.db.models import Count, Sum
            from django.db.models.functions import TruncDate
            
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            result = {
                'followers': [],
                'donations': [],
            }
            
            if hasattr(self, 'campaign_follows'):
                daily_followers = self.campaign_follows.filter(
                    followed_at__gte=start_date
                ).annotate(
                    date=TruncDate('followed_at')
                ).values('date').annotate(
                    count=Count('id')
                ).order_by('date')
                result['followers'] = list(daily_followers)
            
            if hasattr(self, 'donations'):
                daily_donations = self.donations.filter(
                    fulfilled=True,
                    timestamp__gte=start_date
                ).annotate(
                    date=TruncDate('timestamp')
                ).values('date').annotate(
                    total=Sum('amount'),
                    count=Count('id')
                ).order_by('date')
                result['donations'] = list(daily_donations)
            
            return result
        except:
            return {'followers': [], 'donations': []}
   
    # ==================== PREMIUM STATS METHODS ====================
    
    def can_view_premium_stats(self, user):
        """Check if user can view premium stats for this campaign"""
        try:
            if not user or not user.is_authenticated:
                return False
            
            # Campaign owner always gets premium stats for their own campaigns
            if hasattr(self, 'user') and hasattr(self.user, 'user'):
                if user == self.user.user:
                    return True
            
            # Check if user has active premium subscription
            if hasattr(user, 'premium_subscriptions'):
                active_sub = user.premium_subscriptions.filter(
                    Q(status='active') | Q(status='trial'),
                    Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
                ).first()
                if active_sub:
                    return True
            
            # Check if user purchased this specific campaign's stats
            if hasattr(self, 'premium_access'):
                if self.premium_access.filter(
                    purchased_by=user,
                    expiry_date__gt=timezone.now()
                ).exists():
                    return True
            
            return False
        except:
            return False
    
    def get_follower_growth_chart(self, days=30):
        """Daily follower growth data for charts"""
        try:
            from django.db.models import Count
            from django.db.models.functions import TruncDate
            
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            if not hasattr(self, 'campaign_follows'):
                return []
            
            daily_data = self.campaign_follows.filter(
                followed_at__gte=start_date
            ).annotate(
                date=TruncDate('followed_at')
            ).values('date').annotate(
                new_followers=Count('id')
            ).order_by('date')
            
            # Create complete date range with zeros
            date_range = []
            current = start_date.date()
            while current <= end_date.date():
                date_range.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'new_followers': 0,
                    'cumulative': 0
                })
                current += timedelta(days=1)
            
            # Fill in actual data
            cumulative = 0
            if hasattr(self, 'campaign_follows'):
                cumulative = self.campaign_follows.filter(followed_at__lt=start_date).count()
            
            for i, day in enumerate(date_range):
                for data in daily_data:
                    if data['date'] and data['date'].strftime('%Y-%m-%d') == day['date']:
                        day['new_followers'] = data['new_followers']
                        break
                cumulative += day['new_followers']
                day['cumulative'] = cumulative
            
            return date_range
        except Exception as e:
            print(f"Error in follower growth chart: {e}")
            return []
    
    def get_donor_demographics(self):
        """Geographic and demographic breakdown of donors"""
        try:
            if not hasattr(self, 'donations'):
                return {
                    'locations': {},
                    'brackets': {},
                    'total_donors': 0,
                    'repeat_donors': 0
                }
            
            donors = self.donations.filter(fulfilled=True).select_related('user__profile')
            
            # Geographic distribution
            locations = {}
            for donation in donors:
                try:
                    if hasattr(donation.user, 'profile') and hasattr(donation.user.profile, 'location'):
                        location = donation.user.profile.location or 'Unknown'
                    else:
                        location = 'Unknown'
                    locations[location] = locations.get(location, 0) + 1
                except:
                    locations['Unknown'] = locations.get('Unknown', 0) + 1
            
            # Donation size brackets
            brackets = {
                'under_10': 0,
                '10_50': 0,
                '50_100': 0,
                '100_500': 0,
                'over_500': 0
            }
            
            for donation in donors:
                try:
                    amount = float(donation.amount)
                    if amount < 10:
                        brackets['under_10'] += 1
                    elif amount < 50:
                        brackets['10_50'] += 1
                    elif amount < 100:
                        brackets['50_100'] += 1
                    elif amount < 500:
                        brackets['100_500'] += 1
                    else:
                        brackets['over_500'] += 1
                except:
                    brackets['over_500'] += 1
            
            # Return top locations
            top_locations = dict(sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10])
            
            return {
                'locations': top_locations,
                'brackets': brackets,
                'total_donors': donors.count(),
                'repeat_donors': 0
            }
        except Exception as e:
            print(f"Error in donor demographics: {e}")
            return {
                'locations': {},
                'brackets': {},
                'total_donors': 0,
                'repeat_donors': 0
            }
    
    def get_conversion_funnel(self):
        """Viewers → Followers → Pledgers → Donors"""
        try:
            total_views = 0
            if hasattr(self, 'views'):
                total_views = self.views.count()
            
            funnel = {
                'views': total_views,
                'followers': self.follower_count,
                'pledgers': 0,
                'donors': 0,
                'view_to_follower': 0,
                'follower_to_pledger': 0,
                'pledger_to_donor': 0
            }
            
            if hasattr(self, 'pledges'):
                funnel['pledgers'] = self.pledges.values('user').distinct().count()
            
            if hasattr(self, 'donations'):
                funnel['donors'] = self.donations.filter(fulfilled=True).values('user').distinct().count()
            
            # Calculate conversion rates
            if funnel['views'] > 0:
                funnel['view_to_follower'] = round((funnel['followers'] / funnel['views']) * 100, 1)
            
            if funnel['followers'] > 0:
                funnel['follower_to_pledger'] = round((funnel['pledgers'] / funnel['followers']) * 100, 1)
            
            if funnel['pledgers'] > 0:
                funnel['pledger_to_donor'] = round((funnel['donors'] / funnel['pledgers']) * 100, 1)
            
            return funnel
        except Exception as e:
            print(f"Error in conversion funnel: {e}")
            return {
                'views': 0,
                'followers': 0,
                'pledgers': 0,
                'donors': 0,
                'view_to_follower': 0,
                'follower_to_pledger': 0,
                'pledger_to_donor': 0
            }
    
    def get_predictive_insights(self):
        """AI-powered predictions and recommendations"""
        try:
            # Calculate current trajectory
            days_elapsed = self.get_current_day() - 1
            if days_elapsed > 0:
                daily_avg = self.total_donations / days_elapsed
                projected = daily_avg * (self.duration or 30)
            else:
                projected = 0
            
            # Success probability based on historical data
            probability = 'N/A'
            if self.funding_goal and self.funding_goal > 0:
                progress_rate = self.donation_percentage / 100
                days_remaining = self.days_left or 0
                
                if days_elapsed < 7:
                    probability = 'estimating...'
                elif progress_rate >= 0.7 and days_remaining > 0:
                    probability = 'High'
                elif progress_rate >= 0.4 and days_remaining > days_elapsed:
                    probability = 'Medium'
                else:
                    probability = 'Needs attention'
            
            # Recommendations
            recommendations = []
            
            if self.follower_count > 0 and self.get_donation_conversion_rate() < 5:
                recommendations.append("Share your campaign story more - your conversion rate is below average")
            
            if self.days_left and self.days_left < 7 and self.donation_percentage < 50:
                recommendations.append("Last week push! Consider reaching out to your followers directly")
            
            if self.get_activity_completion_rate() < 50:
                recommendations.append("You're behind on daily activities - consistent updates increase donations by 40%")
            
            if not recommendations:
                recommendations.append("You're on track! Keep up the great work")
            
            estimated_date = 'N/A'
            if self.timestamp and self.duration:
                estimated_date = (self.timestamp + timedelta(days=self.duration or 30)).strftime('%b %d, %Y')
            
            return {
                'projected_final': round(projected, 2),
                'success_probability': probability,
                'recommendations': recommendations,
                'estimated_completion_date': estimated_date
            }
        except Exception as e:
            print(f"Error in predictive insights: {e}")
            return {
                'projected_final': 0,
                'success_probability': 'N/A',
                'recommendations': ['Stay active and engage with your followers!'],
                'estimated_completion_date': 'N/A'
            }
    
    def get_category_benchmarks(self):
        """Compare this campaign to others in same category"""
        try:
            category_campaigns = Campaign.objects.filter(
                category=self.category,
                is_active=True
            ).exclude(id=self.id)
            
            if not category_campaigns.exists():
                return None
            
            # Average stats for category
            avg_followers = category_campaigns.aggregate(
                avg=Avg('follower_count')
            )['avg'] or 0
            
            avg_donations = 0
            for campaign in category_campaigns:
                avg_donations += campaign.total_donations
            avg_donations = avg_donations / category_campaigns.count() if category_campaigns.count() > 0 else 0
            
            avg_activities = 0
            for campaign in category_campaigns:
                if hasattr(campaign, 'activity_set'):
                    avg_activities += campaign.activity_set.count()
            avg_activities = avg_activities / category_campaigns.count() if category_campaigns.count() > 0 else 0
            
            # Percentile rankings (simplified)
            def calculate_percentile(value, values_list):
                if not values_list or value == 0:
                    return 100
                better_than = sum(1 for v in values_list if v <= value)
                return round((better_than / len(values_list)) * 100)
            
            follower_values = [c.follower_count for c in category_campaigns]
            donation_values = [c.total_donations for c in category_campaigns]
            activity_values = [c.activity_set.count() if hasattr(c, 'activity_set') else 0 for c in category_campaigns]
            
            return {
                'category': self.category,
                'total_in_category': category_campaigns.count(),
                'averages': {
                    'followers': round(avg_followers, 1),
                    'donations': round(avg_donations, 2),
                    'activities': round(avg_activities, 1),
                },
                'your_rank': {
                    'followers': f"Top {calculate_percentile(self.follower_count, follower_values)}%",
                    'donations': f"Top {calculate_percentile(self.total_donations, donation_values)}%",
                    'activities': f"Top {calculate_percentile(self.get_activity_completion_rate(), activity_values)}%",
                }
            }
        except Exception as e:
            print(f"Error in category benchmarks: {e}")
            return None

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
            # NEW: Religious & Spiritual Causes
            'Religious & Spiritual Causes': {
                'Goals': [
                    'Support religious institutions, missions, and spiritual outreach programs.',
                    'Fund community worship spaces, events, and religious education.',
                    'Help spread faith, provide spiritual guidance, and support religious communities.'
                ],
                'Activities': [
                    'Share updates on religious events, services, and community gatherings.',
                    'Document mission trips, outreach programs, and charitable work.',
                    'Post inspirational messages, sermons, or spiritual reflections.',
                    'Show progress on building or renovating worship spaces.',
                    'Highlight stories of faith, hope, and community support.',
                    'Organize fundraising for religious holidays, festivals, or special events.'
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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='premium_subscriptions')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    
    # Payment info
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_agreement_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Features
    can_view_advanced_stats = models.BooleanField(default=True)
    can_export_data = models.BooleanField(default=False)
    can_compare_campaigns = models.BooleanField(default=False)
    can_access_predictive = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.plan} ({self.status})"
    
    @property
    def is_active(self):
        if self.status == 'active' or self.status == 'trial':
            if self.end_date and self.end_date < timezone.now():
                return False
            return True
        return False
    
    @property
    def days_remaining(self):
        if not self.end_date:
            return None
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)


class CampaignPremiumAccess(models.Model):
    """One-time purchases for individual campaign stats"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='premium_access')
    purchased_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchased_campaign_stats')
    purchase_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)  # Null = lifetime
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment info
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    paypal_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.purchased_by.username} - {self.campaign.title}"
    
    @property
    def is_valid(self):
        if not self.expiry_date:
            return True
        return self.expiry_date > timezone.now()


class StatViewLog(models.Model):
    """Track which premium stats are viewed (for analytics)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    stat_type = models.CharField(max_length=50)  # 'follower_chart', 'donor_demographics', etc.
    viewed_at = models.DateTimeField(auto_now_add=True)
    was_premium = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['campaign', 'stat_type']),
        ]








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











