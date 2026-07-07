from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator, EmailValidator
from django.core.exceptions import ValidationError
from cloudinary.forms import CloudinaryFileField
from .models import (
    Profile, Journey, Activity, JournalEntry, 
    Comment, JourneyFollow, Tag, Export,JourneyTag,
    ContactMessage, Subscriber
)
import re
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


# ============================================================================
# AUTHENTICATION FORMS
# ============================================================================

class SignUpForm(UserCreationForm):
    """User registration form — simple and clean"""
    
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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
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
    
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://yourwebsite.com'
        })
    )
    
    twitter = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@username'
        })
    )
    
    instagram = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '@username'
        })
    )
    
    class Meta:
        model = Profile
        fields = ['image', 'bio', 'location', 'website', 'twitter', 'instagram']
    
    def clean_twitter(self):
        username = self.cleaned_data.get('twitter', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username
    
    def clean_instagram(self):
        username = self.cleaned_data.get('instagram', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username


# ============================================================================
# JOURNEY FORMS — Documentation Focus
# ============================================================================

 # ============================================================================
# JOURNEY FORMS — Documentation Focus
# ============================================================================
class JourneyForm(forms.ModelForm):
    """Create/Edit a journey — documentation-first"""
    
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 30 Days of Writing',
            'autofocus': True
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'What is this journey about? What are you documenting?',
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
    
    current_day_override = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 14',
            'min': 1
        }),
        help_text="Already started? Enter your current day number."
    )
    
    start_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-input',
            'type': 'datetime-local'
        })
    )
    
    # Privacy — Private by default
    privacy_status = forms.ChoiceField(
        choices=Journey.PRIVACY_CHOICES,
        initial='private',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    allow_comments = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        help_text="Allow other users to comment on your journey"
    )
    
    # ==================== TEMPLATE STYLE ====================
    template_style = forms.ChoiceField(
        choices=Journey.TEMPLATE_STYLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'template-style-radio'
        }),
        initial='default',
        label='Display Style',
        help_text='How your journey looks to visitors'
    )
    
    tags_input = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'writing, personal, growth'
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
            'cover_image', 'duration', 'current_day_override', 'start_date',
            'privacy_status', 'allow_comments', 'template_style'  # ← ADDED template_style
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            self.fields['current_day_override'].initial = self.instance.current_day_override
            self.fields['template_style'].initial = self.instance.template_style or 'default'
            
            # FIX: Use journeytag_set instead of tags
            tags = self.instance.journeytag_set.all()
            if tags.exists():
                self.fields['tags_input'].initial = ', '.join([tag.tag.name for tag in tags])
            
            if self.instance.milestones:
                self.fields['milestones_input'].initial = '\n'.join(self.instance.milestones)
    
    def clean_current_day_override(self):
        override = self.cleaned_data.get('current_day_override')
        duration = self.cleaned_data.get('duration', 30)
        
        if override and override > duration:
            raise ValidationError(f"Current day can't exceed the duration ({duration} days).")
        
        return override
    
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
        current_day_override = cleaned_data.get('current_day_override')
        journey_type = cleaned_data.get('journey_type')
        
        if current_day_override and journey_type == 'milestone':
            self.add_error('current_day_override', 'Day override is only for daily journeys, not milestone journeys.')
        
        return cleaned_data
    
    def save(self, commit=True):
        journey = super().save(commit=False)
        journey.current_day_override = self.cleaned_data.get('current_day_override')
        journey.template_style = self.cleaned_data.get('template_style', 'default')
        
        if commit:
            journey.save()
            
            # Save milestones
            milestones_input = self.cleaned_data.get('milestones_input', '')
            if milestones_input:
                milestone_list = [m.strip() for m in milestones_input.split('\n') if m.strip()]
                journey.milestones = milestone_list
                journey.save(update_fields=['milestones'])
            
            # FIX: Use journeytag_set instead of tags
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                journey.journeytag_set.all().delete()  # Clear existing tags
                tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                for tag_name in tag_names[:10]:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    JourneyTag.objects.get_or_create(journey=journey, tag=tag)
        
        return journey


 
class JourneySettingsForm(forms.ModelForm):
    """Quick settings update for existing journey"""
    
    class Meta:
        model = Journey
        fields = ['privacy_status', 'allow_comments']
        widgets = {
            'privacy_status': forms.Select(attrs={'class': 'form-select'}),
            'allow_comments': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


# ============================================================================
# ACTIVITY FORMS — Daily Entries
# ============================================================================

class ActivityForm(forms.ModelForm):
    """Create/Edit a journey entry"""
    
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Optional title for this entry'
        })
    )
    
    content = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': "What happened today? Share your progress...",
            'rows': 4
        })
    )
    
    summary = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'A short summary of this entry',
            'rows': 2
        })
    )
    
    media_file = CloudinaryFileField(
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
    
    media_caption = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Caption for your media'
        })
    )
    
    day_number_field = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    actual_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        }),
        help_text="The actual date of this entry"
    )
    
    mood = forms.ChoiceField(
        choices=Activity.MOOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    progress_metrics = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., {"weight": 75, "pages": 10}'
        }),
        help_text="JSON format: {'metric_name': value}"
    )
    
    location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Where did this happen?'
        })
    )
    
    is_draft = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    class Meta:
        model = Activity
        fields = [
            'title', 'content', 'summary', 'media_file', 'media_caption',
            'day_number_field', 'actual_date', 'mood', 'progress_metrics',
            'location', 'is_draft'
        ]
    
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
            else:
                self.fields['content'].widget.attrs['placeholder'] = f"What happened on Day {self.day_number}? Share your progress..."
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        if not content.strip():
            raise ValidationError('Please write something about this day.')
        return content
    
    def clean_progress_metrics(self):
        metrics = self.cleaned_data.get('progress_metrics', '')
        if metrics:
            try:
                import json
                return json.loads(metrics)
            except json.JSONDecodeError:
                raise ValidationError('Please enter valid JSON format.')
        return {}
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.journey:
            day_number = cleaned_data.get('day_number_field') or self.day_number
            
            if day_number:
                # Check if day is locked (future day)
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
                        raise ValidationError(f"Milestone {day_number} already has content.")
                    else:
                        raise ValidationError(f"Day {day_number} already has content.")
        
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


# ============================================================================
# JOURNAL ENTRY FORMS — Free-Form Documentation
# ============================================================================

class JournalEntryForm(forms.ModelForm):
    """Free-form journal entry form"""
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Entry title'
        })
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Write your thoughts...',
            'rows': 8
        })
    )
    
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'writing, reflection, growth'
        }),
        help_text="Separate tags with commas"
    )
    
    is_private = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    mood = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'How are you feeling?'
        })
    )
    
    location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Where are you?'
        })
    )
    
    related_journey = forms.ModelChoiceField(
        queryset=Journey.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    class Meta:
        model = JournalEntry
        fields = [
            'title', 'content', 'tags', 'is_private',
            'mood', 'location', 'related_journey'
        ]
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['related_journey'].queryset = Journey.objects.filter(
                creator__user=user,
                is_active=True
            ).order_by('-created_at')
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        if tags:
            return [t.strip() for t in tags.split(',') if t.strip()]
        return []


# ============================================================================
# COMMENT FORMS
# ============================================================================

class CommentForm(forms.ModelForm):
    """Add a comment to a journey or activity"""
    
    content = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Add a comment...',
            'rows': 2
        })
    )
    
    class Meta:
        model = Comment
        fields = ['content']


# ============================================================================
# EXPORT FORMS
# ============================================================================

class ExportForm(forms.ModelForm):
    """Export journey documentation"""
    
    format = forms.ChoiceField(
        choices=Export.EXPORT_FORMATS,
        initial='pdf',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    include_media = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    include_comments = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    class Meta:
        model = Export
        fields = ['format', 'include_media', 'include_comments']


# ============================================================================
# FOLLOW FORM
# ============================================================================

class FollowForm(forms.ModelForm):
    """Follow a journey"""
    
    notify_on_new_entry = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    class Meta:
        model = JourneyFollow
        fields = ['notify_on_new_entry']


# ============================================================================
# SEARCH FORM
# ============================================================================

class JourneySearchForm(forms.Form):
    """Search and filter journeys"""
    
    SORT_CHOICES = [
        ('-created_at', 'Newest'),
        ('title', 'Title A-Z'),
        ('-updated_at', 'Recently Updated'),
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
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


# ============================================================================
# CONTACT FORMS
# ============================================================================

class ContactForm(forms.Form):
    """Contact form for support"""
    
    name = forms.CharField(
        max_length=200,
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


# ============================================================================
# REMOVED (Not Documentation-First)
# ============================================================================

"""
REMOVED:
- SocialConnection forms (too social)
- ImportedContent forms (too complex)
- SocialPostTemplate forms (too social)
- QuickAddTracker forms (replaced by simple ActivityForm)
- Report forms (moderation, not core)
- All donation/funding related fields
- Auto-import social settings
- Social share URL and auto-post settings
- The entire "Social-First" concept is removed
""" 