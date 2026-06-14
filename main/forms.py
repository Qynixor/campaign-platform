from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator, EmailValidator
from django.core.exceptions import ValidationError
from cloudinary.forms import CloudinaryFileField
from .models import (
    Profile, SocialConnection, ImportedContent,
    Journey, Activity, JourneyFollow, Tag,
    ActivityComment, Donation, PostJourneyProduct,
    Report, 
)
import re
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


# ============================================================================
# AUTHENTICATION FORMS
# ============================================================================

class SignUpForm(UserCreationForm):
    """User registration form"""
    
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@email.com',
            'autocomplete': 'email'
        })
    )
    
    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'username',
            'autocomplete': 'username'
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        })
    )
    
    # Optional profile fields
    tiktok_username = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@username (optional)'
        })
    )
    
    instagram_username = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@username (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_username(self):
        username = self.cleaned_data.get('username', '').lower()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters.')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Username can only contain letters, numbers, and underscores.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already registered.')
        return email
    
    def clean_tiktok_username(self):
        username = self.cleaned_data.get('tiktok_username', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username
    
    def clean_instagram_username(self):
        username = self.cleaned_data.get('instagram_username', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
            # Update profile with social usernames
            profile = user.profile
            profile.tiktok_username = self.cleaned_data.get('tiktok_username', '')
            profile.instagram_username = self.cleaned_data.get('instagram_username', '')
            profile.save()
        return user


class LoginForm(AuthenticationForm):
    """User login form"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username or Email',
            'autocomplete': 'username'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )


# ============================================================================
# PROFILE FORMS
# ============================================================================

class ProfileForm(forms.ModelForm):
    """Edit profile information"""
    
    image = CloudinaryFileField(
        required=False,
        options={
            'folder': 'profile_pics',
            'transformation': [
                {'width': 400, 'height': 400, 'crop': 'fill'},
                {'quality': 'auto:best', 'fetch_format': 'auto'}
            ],
            'format': 'webp'
        },
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*'
        })
    )
    
    bio = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Tell us about yourself...',
            'rows': 3
        })
    )
    
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'City, Country'
        })
    )
    
    tiktok_username = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@username'
        })
    )
    
    instagram_username = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@username'
        })
    )
    
    youtube_channel = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@channel'
        })
    )
    
    paypal_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@paypal.com'
        })
    )
    
    class Meta:
        model = Profile
        fields = ['image', 'bio', 'location', 'tiktok_username', 
                  'instagram_username', 'youtube_channel', 'paypal_email']
    
    def clean_tiktok_username(self):
        username = self.cleaned_data.get('tiktok_username', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username
    
    def clean_instagram_username(self):
        username = self.cleaned_data.get('instagram_username', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username


# ============================================================================
# JOURNEY FORMS
# ============================================================================
class JourneyForm(forms.ModelForm):
    """Create/Edit a journey"""
    
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 30 Days of Yoga',
            'autofocus': True
        })
    )
    
    description = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'What is this journey about? What will followers experience?',
            'rows': 4
        })
    )
    
    category = forms.ChoiceField(
        choices=Journey.CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    journey_type = forms.ChoiceField(
        choices=Journey.JOURNEY_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-trigger': 'journey-type-change'
        })
    )
    
    TEMPLATE_STYLE_CHOICES = [
        ('default', '📱 Classic — Simple day-by-day strip, works for everything'),
        ('fitness', '🏋️ Fitness — Progress gallery, workout counter, red energy theme'),
        ('portfolio', '💼 Portfolio — Professional cards, milestone dates, blue trust theme'),
        ('startup', '🚀 Startup — Build-in-public roadmap, shipping tracker, green theme'),
    ]
    
    template_style = forms.ChoiceField(
        choices=TEMPLATE_STYLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'template-style-radio'
        }),
        initial='default',
        label='🎨 Journey Display Style',
        help_text='How your journey looks to followers. Pick the vibe that matches your goal.'
    )
    
    cover_image = CloudinaryFileField(
        required=False,
        options={
            'folder': 'journey_covers',
            'transformation': [
                {'width': 1200, 'height': 630, 'crop': 'fill'},
                {'quality': 'auto:best', 'fetch_format': 'auto'}
            ],
            'format': 'webp'
        },
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*'
        })
    )
    
    cover_video = CloudinaryFileField(
        required=False,
        options={
            'folder': 'journey_covers',
            'resource_type': 'video'
        },
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'video/*'
        })
    )
    
    duration = forms.IntegerField(
        min_value=1,
        max_value=365,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '30',
            'min': 1,
            'max': 365
        })
    )
    
    # FIXED: Allow creators to jump to their current day
    current_day_override = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 34',
            'min': 1
        }),
        help_text="Already started? Enter your current day number. Leave blank to start from Day 1."
    )
    
    start_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-input',
            'type': 'datetime-local'
        })
    )
    
    is_public = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    allow_comments = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    auto_import_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    import_hashtag = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '#MyJourney'
        })
    )
    
    funding_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    funding_goal = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '1000.00',
            'step': '0.01'
        })
    )
    
    funding_description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'What are you raising funds for?',
            'rows': 3
        })
    )
    
    tags_input = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'fitness, yoga, wellness, challenge'
        }),
        help_text="Separate tags with commas (max 10)"
    )
    
    milestones_input = forms.CharField(
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Enter each milestone on a new line...',
            'rows': 5
        }),
        help_text="One milestone per line (for milestone journeys)"
    )
    
    class Meta:
        model = Journey
        fields = [
            'title', 'description', 'category', 'journey_type',
            'template_style', 'cover_image', 'cover_video',
            'duration', 'current_day_override', 'start_date',
            'is_public', 'allow_comments', 'auto_import_enabled', 'import_hashtag',
            'funding_enabled', 'funding_goal', 'funding_description'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            self.fields['template_style'].initial = self.instance.template_style or 'default'
            
            # FIXED: Populate current_day_override
            self.fields['current_day_override'].initial = self.instance.current_day_override
            
            tags = self.instance.tags.all()
            if tags.exists():
                self.fields['tags_input'].initial = ', '.join([tag.name for tag in tags])
            
            if self.instance.milestones:
                self.fields['milestones_input'].initial = '\n'.join(self.instance.milestones)
    
    def clean_current_day_override(self):
        override = self.cleaned_data.get('current_day_override')
        duration = self.cleaned_data.get('duration', 30)
        
        if override and override > duration:
            raise ValidationError(f"Current day can't exceed the duration ({duration} days).")
        
        return override
    
    def clean_import_hashtag(self):
        hashtag = self.cleaned_data.get('import_hashtag', '')
        if hashtag and not hashtag.startswith('#'):
            hashtag = '#' + hashtag
        return hashtag
    
    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if tags_input:
            tag_list = [t.strip() for t in tags_input.split(',') if t.strip()]
            if len(tag_list) > 10:
                raise ValidationError('You can add a maximum of 10 tags.')
        return tags_input
    
    def clean_milestones_input(self):
        milestones_input = self.cleaned_data.get('milestones_input', '')
        journey_type = self.cleaned_data.get('journey_type')
        
        if journey_type == 'milestone':
            milestone_list = [m.strip() for m in milestones_input.split('\n') if m.strip()]
            duration = self.cleaned_data.get('duration')
            
            if duration and len(milestone_list) > duration:
                raise ValidationError(f"Number of milestones ({len(milestone_list)}) exceeds duration ({duration}).")
        
        return milestones_input
    
    def clean(self):
        cleaned_data = super().clean()
        template_style = cleaned_data.get('template_style')
        journey_type = cleaned_data.get('journey_type')
        
        # Smart defaults based on template style
        if template_style and template_style != 'default':
            style_category_map = {
                'fitness': 'fitness',
                'portfolio': 'creative',
                'startup': 'business',
            }
            if template_style in style_category_map:
                cleaned_data['category'] = style_category_map[template_style]
            
            style_type_map = {
                'fitness': 'daily',
                'portfolio': 'milestone',
                'startup': 'daily',
            }
            if template_style in style_type_map and not cleaned_data.get('journey_type'):
                cleaned_data['journey_type'] = style_type_map[template_style]
        
        # FIXED: Validate current_day_override against journey_type
        current_day_override = cleaned_data.get('current_day_override')
        if current_day_override and journey_type == 'milestone':
            self.add_error('current_day_override', 'Day override is only for daily challenges, not milestone journeys.')
        
        return cleaned_data
    
    def save(self, commit=True):
        journey = super().save(commit=False)
        
        # FIXED: Save the override
        journey.current_day_override = self.cleaned_data.get('current_day_override')
        
        if commit:
            journey.save()
            
            # Auto-generate milestones based on template
            milestones_input = self.cleaned_data.get('milestones_input', '')
            if milestones_input:
                milestone_list = [m.strip() for m in milestones_input.split('\n') if m.strip()]
                journey.milestones = milestone_list
            elif not journey.milestones:
                if journey.template_style == 'startup':
                    journey.milestones = [
                        "Idea Validation & Research",
                        "MVP Planning & Wireframes",
                        "First Prototype Built",
                        "User Testing Round 1",
                        "Iterate Based on Feedback",
                        "Beta Launch",
                        "First Paying Customer",
                        "Public Launch 🚀",
                    ]
                elif journey.template_style == 'portfolio':
                    journey.milestones = [
                        "Project Kickoff",
                        "Research & Discovery",
                        "First Draft Complete",
                        "Client Review",
                        "Revisions & Polish",
                        "Final Delivery ✅",
                    ]
            
            journey.save(update_fields=['milestones', 'current_day_override'])
            
            # Save tags
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                journey.tags.clear()
                tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                for tag_name in tag_names[:10]:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    journey.tags.add(tag)
        
        return journey

class JourneySettingsForm(forms.ModelForm):
    """Quick settings update for existing journey"""
    
    class Meta:
        model = Journey
        fields = ['is_public', 'allow_comments', 'auto_import_enabled', 'import_hashtag']
        widgets = {
            'import_hashtag': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '#MyJourney'
            })
        }


# ============================================================================
# ACTIVITY FORMS
# ============================================================================
class ActivityForm(forms.ModelForm):
    """Post/Edit a day's activity"""
    
    content = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': "What happened? Share your progress...",
            'rows': 4
        })
    )
    
    file = CloudinaryFileField(
        required=False,
        options={
            'folder': 'activity_files',
            'resource_type': 'auto',
            'transformation': [
                {'quality': 'auto:best', 'fetch_format': 'auto'}
            ]
        },
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*,video/*'
        })
    )
    
    day_number_field = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    # NEW: Actual date field for milestone journeys
    actual_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        }),
        help_text="When did this actually happen? (For portfolio/trust building)"
    )
    
    class Meta:
        model = Activity
        fields = ['content', 'file', 'day_number_field', 'actual_date']
    
    def __init__(self, *args, **kwargs):
        self.journey = kwargs.pop('journey', None)
        self.day_number = kwargs.pop('day_number', None)
        super().__init__(*args, **kwargs)
        
        if self.day_number:
            self.fields['day_number_field'].initial = self.day_number
        
        # Customize placeholder based on journey type
        if self.journey:
            if self.journey.journey_type == 'milestone':
                self.fields['content'].widget.attrs['placeholder'] = f"What did you achieve in Milestone {self.day_number}?"
                
                # Make actual_date more prominent for milestones
                self.fields['actual_date'].help_text = "Add the real date this milestone was completed"
            else:
                self.fields['content'].widget.attrs['placeholder'] = f"What happened on Day {self.day_number}? Share your progress..."
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        if not content.strip():
            if self.journey and self.journey.journey_type == 'milestone':
                raise ValidationError('Please describe what you achieved in this milestone.')
            else:
                raise ValidationError('Please write something about this day.')
        return content
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.journey:
            day_number = cleaned_data.get('day_number_field') or self.day_number
            
            if day_number:
                # Check if day is locked (future day)
                # For milestone journeys, is_day_locked returns False so this passes
                if self.journey.is_day_locked(day_number):
                    if self.journey.journey_type == 'daily':
                        raise ValidationError(f"Day {day_number} is not available yet.")
                
                # Check if activity already exists for this day
                existing = Activity.objects.filter(
                    journey=self.journey,
                    day_number_field=day_number
                )
                if self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)
                
                if existing.exists():
                    if self.journey.journey_type == 'milestone':
                        raise ValidationError(f"Milestone {day_number} already has content posted. You can edit it instead.")
                    else:
                        raise ValidationError(f"Day {day_number} already has content posted.")
        
        return cleaned_data
    
    def save(self, commit=True):
        activity = super().save(commit=False)
        
        if self.journey:
            activity.journey = self.journey
        
        if self.day_number and not activity.day_number_field:
            activity.day_number_field = self.day_number
        
        if commit:
            activity.save()
        
        return activity

class QuickImportForm(forms.Form):
    """Smart Import - Paste link, auto-detect platform, preview content"""
    
    url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://www.tiktok.com/@username/video/123456789',
            'autofocus': True
        })
    )
    
    journey = forms.ModelChoiceField(
        queryset=Journey.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    day_number = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Day number',
            'min': 1
        })
    )
    
    # NEW: Caption field (editable by user)
    caption = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Describe this update...',
            'rows': 2
        })
    )
    
    # NEW: Hidden fields for platform detection and embed data
    detected_platform = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    embed_html = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    thumbnail_url = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['journey'].queryset = Journey.objects.filter(
                creator__user=user,
                is_active=True
            ).order_by('-created_at')
    
    def clean_url(self):
        url = self.cleaned_data.get('url', '').strip()
        
        if not url:
            raise ValidationError('Please enter a URL.')
        
        # Platform detection
        platform = None
        if 'tiktok.com' in url:
            platform = 'tiktok'
        elif 'instagram.com' in url:
            platform = 'instagram'
        elif 'youtube.com' in url or 'youtu.be' in url:
            platform = 'youtube'
        elif 'facebook.com' in url or 'fb.com' in url:
            platform = 'facebook'
        elif 'twitter.com' in url or 'x.com' in url:
            platform = 'twitter'
        else:

            raise ValidationError('Please enter a valid TikTok, Instagram, YouTube, Facebook or X/Twitter URL.')
        
        self.cleaned_data['detected_platform'] = platform
        return url
    
    def clean_day_number(self):
        day_number = self.cleaned_data.get('day_number')
        journey = self.cleaned_data.get('journey')
        
        if not day_number:
            raise ValidationError('Please enter a day number.')
        
        if day_number < 1:
            raise ValidationError('Day number must be at least 1.')
        
        if journey:
            # Check if day is locked (only for daily challenges)
            if journey.is_day_locked(day_number):
                if journey.journey_type == 'daily':
                    raise ValidationError(f"Day {day_number} is not available yet.")
            
            # Check if day already has content (warning, not error)
            existing = Activity.objects.filter(journey=journey, day_number_field=day_number).first()
            if existing:
                # Store existing activity for warning message
                self.existing_activity = existing
        
        return day_number
    
    def clean_caption(self):
        caption = self.cleaned_data.get('caption', '').strip()
        
        # If no caption provided, we'll generate one in the view
        return caption
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure journey belongs to the user
        journey = cleaned_data.get('journey')
        user = self.initial.get('user') or (hasattr(self, 'user') and self.user)
        
        if journey and user:
            if journey.creator.user != user:
                raise ValidationError('You do not have permission to import to this journey.')
        
        return cleaned_data
    
    def get_detected_platform(self):
        """Helper to get detected platform"""
        return self.cleaned_data.get('detected_platform')
    
    def has_existing_activity(self):
        """Check if day already has content"""
        return hasattr(self, 'existing_activity')
    
    def get_existing_activity(self):
        """Get existing activity if any"""
        return getattr(self, 'existing_activity', None)

# ============================================================================
# SOCIAL CONNECTION FORMS
# ============================================================================

class SocialConnectForm(forms.Form):
    """Connect social media account"""
    
    platform = forms.ChoiceField(
        choices=SocialConnection.PLATFORMS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class SocialSettingsForm(forms.ModelForm):
    """Update social connection settings"""
    
    auto_import = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    import_hashtag = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '#MyJourney'
        })
    )
    
    class Meta:
        model = SocialConnection
        fields = ['auto_import', 'import_hashtag']
    
    def clean_import_hashtag(self):
        hashtag = self.cleaned_data.get('import_hashtag', '')
        if hashtag and not hashtag.startswith('#'):
            hashtag = '#' + hashtag
        return hashtag


# ============================================================================
# COMMENT FORMS
# ============================================================================

class CommentForm(forms.ModelForm):
    """Add a comment to an activity"""
    
    content = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Add a comment...',
            'rows': 2
        })
    )
    
    class Meta:
        model = ActivityComment
        fields = ['content']


# ============================================================================
# DONATION FORMS
# ============================================================================

class DonationForm(forms.ModelForm):
    """Make a donation to a journey"""
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '25.00',
            'step': '1.00',
            'min': 1
        })
    )
    
    donor_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your name (optional)'
        })
    )
    
    donor_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@email.com (for receipt)'
        })
    )
    
    message = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Leave a message of support...',
            'rows': 3
        })
    )
    
    anonymous = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    class Meta:
        model = Donation
        fields = ['amount', 'donor_name', 'donor_email', 'message']
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < 1:
            raise ValidationError('Minimum donation is $1.')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If anonymous, clear donor name
        if cleaned_data.get('anonymous'):
            cleaned_data['donor_name'] = 'Anonymous'
        
        return cleaned_data


# ============================================================================
# SEARCH FORMS
# ============================================================================
class JourneySearchForm(forms.Form):
    """Search and filter journeys"""
    
    SORT_CHOICES = [
        ('-created_at', 'Newest'),
        ('-view_count', 'Most Viewed'),
        ('title', 'Title A-Z'),
    ]
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search journeys...'
        })
    )
    
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + Journey.CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    journey_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Journey.JOURNEY_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    funding_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

# ============================================================================
# REPORT FORMS
# ============================================================================

class ReportForm(forms.ModelForm):
    """Report inappropriate content"""
    
    reason = forms.ChoiceField(
        choices=Report.REASON_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Please provide additional details...',
            'rows': 4
        })
    )
    
    class Meta:
        model = Report
        fields = ['reason', 'description']


# ============================================================================
# POST-JOURNEY PRODUCT FORMS
# ============================================================================

class PostJourneyProductForm(forms.ModelForm):
    """Create a post-journey product"""
    
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., Complete 30-Day Blueprint'
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'What does this product include?',
            'rows': 4
        })
    )
    
    price = forms.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '29.99',
            'step': '0.01',
            'min': 0.01
        })
    )
    
    product_type = forms.ChoiceField(
        choices=PostJourneyProduct.PRODUCT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-trigger': 'product-type-change'
        })
    )
    
    pdf_file = CloudinaryFileField(
        required=False,
        options={
            'folder': 'post_journey_pdfs',
            'resource_type': 'raw'
        },
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': '.pdf'
        })
    )
    
    video_file = CloudinaryFileField(
        required=False,
        options={
            'folder': 'post_journey_videos',
            'resource_type': 'video'
        },
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'video/*'
        })
    )
    
    coaching_calendar_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://calendly.com/your-link'
        })
    )
    
    coaching_duration = forms.IntegerField(
        min_value=15,
        initial=60,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'min': 15,
            'step': 15
        })
    )
    
    class Meta:
        model = PostJourneyProduct
        fields = [
            'title', 'description', 'price', 'product_type',
            'pdf_file', 'video_file', 'coaching_calendar_link', 'coaching_duration'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get('product_type')
        
        if product_type == 'blueprint' and not cleaned_data.get('pdf_file'):
            self.add_error('pdf_file', 'PDF file is required for blueprint products.')
        
        if product_type == 'behind_scenes' and not cleaned_data.get('video_file'):
            self.add_error('video_file', 'Video file is required for behind the scenes products.')
        
        if product_type == 'coaching' and not cleaned_data.get('coaching_calendar_link'):
            self.add_error('coaching_calendar_link', 'Calendar link is required for coaching products.')
        
        return cleaned_data



# ============================================================================
# CONTACT / SUPPORT FORMS
# ============================================================================

class ContactForm(forms.Form):
    """Contact form for support"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@email.com'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Subject'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'How can we help you?',
            'rows': 6
        })
    )


class NewsletterSignupForm(forms.Form):
    """Newsletter signup form"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@email.com'
        })
    )
    
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your name (optional)'
        })
    )