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
        folder='profile_pics',  # Cloudinary folder
        default='v1763637368/pp_vvzbcj'  # Make sure this exists in Cloudinary
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


    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            return age
        return None

    def update_verification_status(self):
        """Update verification status."""
        self.profile_verified = True
        self.save(update_fields=['profile_verified'])

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def total_loves(self):
        # Sum the loves for all campaigns owned by the user
        from .models import Love  # Import here to avoid circular imports
        return Love.objects.filter(campaign__user=self).count()

    def is_changemaker(self):
        # Correct the query to reflect the relationship with the Campaign model
        from .models import Activity, ActivityLove  # Import here to avoid circular imports
        activity_count = Activity.objects.filter(campaign__user=self).count()
        activity_love_count = ActivityLove.objects.filter(activity__campaign__user=self).count()
        return activity_count >= 1 and activity_love_count >= 1

    
  
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create user profile when new user is created
        Profile.objects.create(user=instance)
    else:
        # Save existing profile on user update
        instance.profile.save()






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

from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

class Campaign(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_campaigns')
    title = models.CharField(max_length=300)
    timestamp = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    poster = CloudinaryField('image', folder='campaign_files', null=True, blank=True)
    # Add this new field for multiple images
    additional_images = models.JSONField(default=list, blank=True, 
                                       help_text="List of additional image URLs for slideshow")
    audio = models.FileField(upload_to='campaign_audio', null=True, blank=True)
    is_active = models.BooleanField(default=True)  # Stops donations when target is met
   
    CATEGORY_CHOICES = (

        # Basic Needs
        ('Poverty and Hunger', 'Poverty and Hunger'),
        ('Clean Water and Sanitation', 'Clean Water and Sanitation'),
        ('Disaster Relief', 'Disaster Relief'),
    
         # Health
        ('Healthcare and Medicine', 'Healthcare and Medicine'),
        ('Mental Health', 'Mental Health'),
    
        # Social Justice
        ('Human Rights and Equality', 'Human Rights and Equality'),
        ('Peace and Justice', 'Peace and Justice'),
    
         # Education/Economy
        ('Education for All', 'Education for All'),
        ('Economic Empowerment', 'Economic Empowerment'),
    
         # Environment
        ('Climate Action', 'Climate Action'),
        ('Wildlife and Conservation', 'Wildlife and Conservation'),
    
        # Technology
       ('Tech for Humanity', 'Tech for Humanity'),
    
       # Community
       ('Community Development', 'Community Development'),
       ('Arts and Culture', 'Arts and Culture'),
    
       # Other
       ('Other', 'Other'),
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='Education for All')

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
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Enter duration.")
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNITS, default='days')
    funding_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tags = models.ManyToManyField(Tag, through='CampaignTag', related_name='campaigns', blank=True)




    def get_sound_tribe_members_count(self):
        """
        Get the number of members in the sound tribe for this campaign
        """
        return SoundTribe.objects.filter(campaign=self).count()
    
    def has_user_joined_tribe(self, user_profile):
        """
        Check if a specific user has joined the sound tribe
        """
        if not user_profile:
            return False
        return SoundTribe.objects.filter(
            user=user_profile,
            campaign=self
        ).exists()
    
    def get_recent_tribe_members(self, limit=6):
        """
        Get recent tribe members with profile data
        """
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


    @property
    def total_pledges(self):
        return self.pledge_set.aggregate(total=models.Sum('amount'))['total'] or 0
    @property
    def total_donations(self):
        return self.donations.aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def donation_percentage(self):
        if self.funding_goal == 0:
            return 0
        return round((self.total_donations / self.funding_goal) * 100, 2)

    @property
    def donation_remaining(self):
        return max(self.funding_goal - self.total_donations, 0)    
   
    @property
    def is_outdated(self):
        """Check if the campaign is outdated based on duration and unit."""
        if self.duration is None:
            return False  # Ongoing campaigns never expire

        if self.duration_unit == 'minutes':
            expiration_date = self.timestamp + timedelta(minutes=self.duration)
        else:
            expiration_date = self.timestamp + timedelta(days=self.duration)

        return timezone.now() > expiration_date
    
    @property
    def days_left(self):
        if self.duration is None:
            return None

        if self.duration_unit == 'minutes':
            end_time = self.timestamp + timedelta(minutes=self.duration)
            remaining = end_time - timezone.now()
            return max(int(remaining.total_seconds() // 60), 0)
        else:
            end_time = self.timestamp + timedelta(days=self.duration)
            remaining = end_time - timezone.now()
            return max(remaining.days, 0)







    def __str__(self):
        return self.title


    def save(self, *args, **kwargs):
        # Check if the campaign is new or if visibility has changed
        is_new = self.pk is None
        if not is_new:
            old_instance = Campaign.objects.get(pk=self.pk)
            visibility_changed = old_instance.visibility != self.visibility
        else:
            visibility_changed = False

        # Save the campaign
        super().save(*args, **kwargs)

        # Notify followers if the campaign has become private or if it's a new campaign
        if self.visibility == 'private' or is_new:
            if is_new or visibility_changed:
                self.notify_visible_to_followers()

    def notify_visible_to_followers(self):
        for profile in self.visible_to_followers.all():
            user = profile.user  # Ensure this relationship is correctly set
            message = (
                f'You have been granted access to a private campaign: {self.title}. '
                f'<a href="{reverse("view_campaign", kwargs={"campaign_id": self.pk})}">View Campaign</a>'
            )
            Notification.objects.create(
                user=user,
                message=message,
                timestamp=timezone.now(),
                campaign_notification=True,
                campaign=self,
                redirect_link=f'/campaigns/{self.pk}/'
            )


    @property
    def love_count(self):
        return self.loves.count()
        

    @property
    def is_changemaker(self):
        """Check if the user qualifies as a changemaker."""
        activity_count = self.activity_set.count()
        activity_love_count = ActivityLove.objects.filter(activity__campaign=self).count()
        return activity_count >= 1 and activity_love_count >= 1

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Automatically award changemaker status if criteria are met
        if self.is_changemaker:
            self.award_changemaker_status()

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
        'Poverty and Hunger': {
            'Goals': [
                'Reduce poverty and hunger by providing immediate and long-term support.',
                'Empower communities with resources for food security and income generation.'
            ],
            'Activities': [
                'Distribute food packages or meals to low-income families.',
                'Fund community farming or cooperative initiatives.',
                'Launch skills training or small-business grants for unemployed individuals.',
                'Support food banks or hunger relief programs.',
                'Organize donation drives for clothes and daily essentials.'
            ]
        },
        'Clean Water and Sanitation': {
            'Goals': [
                'Ensure access to clean drinking water and improved sanitation.',
                'Raise awareness about hygiene and waterborne diseases.'
            ],
            'Activities': [
                'Build or repair wells, boreholes, or water systems.',
                'Distribute water filters or hygiene kits to communities.',
                'Conduct sanitation awareness campaigns.',
                'Partner with engineers to develop sustainable water solutions.',
                'Install toilets and handwashing facilities in underserved areas.'
            ]
        },
        'Disaster Relief': {
            'Goals': [
                'Provide emergency aid to victims of natural or human-made disasters.',
                'Support recovery and rebuilding efforts.'
            ],
            'Activities': [
                'Distribute emergency supplies like food, blankets, and medicine.',
                'Raise funds for rebuilding homes and schools.',
                'Mobilize volunteers for rescue and relief operations.',
                'Partner with emergency response organizations.',
                'Provide temporary shelter and medical services.'
            ]
        },
        'Healthcare and Medicine': {
            'Goals': [
                'Improve access to medical care and essential medicines.',
                'Support health infrastructure in low-resource settings.'
            ],
            'Activities': [
                'Fund surgeries or treatments for patients in need.',
                'Provide medical equipment or ambulances to rural clinics.',
                'Organize blood donation or vaccination drives.',
                'Train health workers in local communities.',
                'Create mobile health clinics or telemedicine services.'
            ]
        },
        'Mental Health': {
            'Goals': [
                'Raise awareness about mental health challenges.',
                'Provide accessible support and counseling services.'
            ],
            'Activities': [
                'Launch online or in-person mental health counseling programs.',
                'Train community members as mental health first responders.',
                'Fund hotlines or mental health apps.',
                'Host awareness events to fight stigma.',
                'Create support groups for anxiety, depression, or trauma recovery.'
            ]
        },
        'Human Rights and Equality': {
            'Goals': [
                'Promote and protect fundamental human rights.',
                'Fight discrimination and injustice in all forms.'
            ],
            'Activities': [
                'Advocate for refugee rights or gender equality.',
                'Organize legal aid or education workshops.',
                'Support organizations working on human rights issues.',
                'Launch campaigns to expose injustice or systemic discrimination.',
                'Provide safe havens or shelters for vulnerable groups.'
            ]
        },
        'Peace and Justice': {
            'Goals': [
                'Support justice systems and conflict resolution.',
                'Promote peacebuilding and reconciliation in conflict zones.'
            ],
            'Activities': [
                'Train youth in conflict resolution and mediation.',
                'Support rehabilitation programs for former offenders or soldiers.',
                'Organize peace dialogues between divided communities.',
                'Fund legal defense for marginalized populations.',
                'Document and report human rights abuses.'
            ]
        },
        'Education for All': {
            'Goals': [
                'Ensure equitable access to quality education.',
                'Reduce school dropout rates and promote literacy.'
            ],
            'Activities': [
                'Build classrooms or learning centers.',
                'Fund school supplies, tuition, or scholarships.',
                'Train teachers and provide educational resources.',
                'Host community literacy campaigns.',
                'Create inclusive education programs for girls and disabled students.'
            ]
        },
        'Economic Empowerment': {
            'Goals': [
                'Promote entrepreneurship and job creation.',
                'Support marginalized groups through income-generating activities.'
            ],
            'Activities': [
                'Provide startup capital to small businesses.',
                'Offer vocational training and mentorship programs.',
                'Launch financial literacy and savings programs.',
                'Support women-led enterprises.',
                'Connect job seekers to employment opportunities.'
            ]
        },
        'Climate Action': {
            'Goals': [
                'Combat climate change and its effects.',
                'Promote community-based solutions to environmental challenges.'
            ],
            'Activities': [
                'Raise awareness about carbon emissions and climate change.',
                'Organize reforestation or carbon offset programs.',
                'Support renewable energy projects.',
                'Develop sustainable agriculture initiatives.',
                'Advocate for green policies and eco-justice.'
            ]
        },
        'Wildlife and Conservation': {
            'Goals': [
                'Protect biodiversity, forests, oceans, and wildlife.',
                'Promote sustainable and ethical environmental practices.'
            ],
            'Activities': [
                'Fund rescue and rehabilitation of endangered species.',
                'Organize beach cleanups and marine conservation efforts.',
                'Create campaigns to stop deforestation.',
                'Partner with conservation groups on wildlife protection.',
                'Educate communities on eco-friendly lifestyles.'
            ]
        },
        'Tech for Humanity': {
            'Goals': [
                'Leverage technology to solve social and environmental problems.',
                'Bridge the digital divide.'
            ],
            'Activities': [
                'Donate laptops or tablets to students in need.',
                'Develop tech tools for health, education, or disaster response.',
                'Offer coding and digital literacy workshops.',
                'Support innovation hubs or tech incubators for social good.',
                'Create platforms or apps that connect underserved communities.'
            ]
        },
        'Community Development': {
            'Goals': [
                'Enhance the quality of life in local communities.',
                'Build strong and resilient local systems.'
            ],
            'Activities': [
                'Renovate community centers or build shared spaces.',
                'Support local artists or cultural initiatives.',
                'Create neighborhood safety and youth empowerment programs.',
                'Fund micro-infrastructure like street lights or boreholes.',
                'Organize community festivals and forums.'
            ]
        },
        'Arts and Culture': {
            'Goals': [
                'Encourage creativity and artistic expression.'
                'Preserve and promote cultural heritage.',
                
            ],
            'Activities': [
                'Fund art exhibitions and cultural festivals.',
                'Support local artisans and craftspeople.',
                'Provide arts education for youth.',
                'Document and archive cultural traditions.',
                'Promote cultural exchange programs.'
            ]
        },
        'Other': {
            'Goals': [
                'Support causes that don’t fit into predefined categories.',
                'Provide flexibility for unique community needs.'
            ],
            'Activities': [
                'Launch one-time campaigns for urgent needs.',
                'Fundraise for emerging or unexpected challenges.',
                'Engage in storytelling to raise awareness.',
                'Partner with local influencers or activists.',
                'Customize support efforts to individual or group-specific cases.'
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
            message = f"{self.user.user.username} joined your Soundmark Tribe. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Campaign</a>"
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
            message = f"{self.user.username} loved your campaign '{campaign_title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Campaign</a>"
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
                message = f"{commenter_username} commented on your campaign '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Campaign</a>"
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

    # ✅ Cloudinary version of file upload
    file = CloudinaryField(
        'file',
        folder='activity_files',
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new activity
            # Create the notification message for the campaign owner
            message_owner = f"An activity was added to your campaign '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Campaign</a>"
            # Create the notification for the campaign owner
            Notification.objects.create(user=self.campaign.user.user, message=message_owner)
            followers = self.campaign.user.followers.all()
            for follower in followers:
                message_follower = f"An activity was added to a campaign you're following: '{self.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.campaign.pk})}'>View Campaign</a>"
                Notification.objects.create(user=follower, message=message_follower)


        super().save(*args, **kwargs)







class ActivityLove(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='loves')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk is None:  # If this is a new love
            # Create the notification message
            message = f"{self.user.username} loved an activity in your campaign '{self.activity.campaign.title}'. <a href='{reverse('view_campaign', kwargs={'campaign_id': self.activity.campaign.pk})}'>View Campaign</a>"
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



class Blog(models.Model):
    CATEGORY_CHOICES = [
        ('RallyNex-Led', 'RallyNex-Led'),
        ('Tips', 'Tips'),
        ('Spotlight', 'Spotlight'),
        ('Other', 'Other'),
    ]
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    author = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ✅ Cloudinary image field
    image = CloudinaryField(
        'image',
        folder='blog_images',
        null=True,
        blank=True
    )

    is_published = models.BooleanField(default=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    estimated_reading_time = models.PositiveIntegerField(default=5)  # minutes
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


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

