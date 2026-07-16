from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator, EmailValidator
from django.core.exceptions import ValidationError
from cloudinary.forms import CloudinaryFileField
from .models import (
    Profile, Journey, Activity, Reflection, 
    Comment, JourneyFollow, Tag, Export, JourneyTag,
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
            'placeholder': 'Tell us about your fitness journey...',
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
# JOURNEY FORMS — Fitness & Wellness Focus
# ============================================================================

class JourneyForm(forms.ModelForm):
    """Create/Edit a fitness or wellness journey"""
    
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 30 Days of Fitness, My Wellness Journey',
            'autofocus': True
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'What\'s your fitness or wellness goal? What are you tracking?',
            'rows': 4
        })
    )
    
    category = forms.ChoiceField(
        choices=Journey.CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    fitness_goal = forms.ChoiceField(
        choices=Journey.FITNESS_GOALS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="What's your main fitness goal?"
    )
    
    wellness_focus = forms.ChoiceField(
        choices=Journey.WELLNESS_FOCUS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="What's your wellness focus?"
    )
    
    custom_goal = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Or tell us your custom goal...'
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
    
    template_style = forms.ChoiceField(
        choices=Journey.TEMPLATE_STYLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'template-style-radio'
        }),
        initial='fitness',
        required=False,  # ← ADD THIS
        label='Display Style',
        help_text='How your journey looks to visitors'
    )
    
    tags_input = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'fitness, wellness, strength, yoga'
        }),
        help_text="Separate tags with commas (max 10)"
    )
    
    class Meta:
        model = Journey
        fields = [
            'title', 'description', 'category', 'fitness_goal', 'wellness_focus', 'custom_goal',
            'cover_image', 'duration', 'current_day_override', 'start_date',
            'privacy_status', 'allow_comments', 'template_style'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ensure template_style always has a value
        if not self.initial.get('template_style'):
            self.initial['template_style'] = 'fitness'
        
        if self.instance and self.instance.pk:
            self.fields['current_day_override'].initial = self.instance.current_day_override
            self.fields['template_style'].initial = self.instance.template_style or 'fitness'
            
            tags = self.instance.journeytag_set.all()
            if tags.exists():
                self.fields['tags_input'].initial = ', '.join([tag.tag.name for tag in tags])
    
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
    
    def clean(self):
        cleaned_data = super().clean()
        fitness_goal = cleaned_data.get('fitness_goal')
        wellness_focus = cleaned_data.get('wellness_focus')
        category = cleaned_data.get('category')
        
        # Set default template_style if not provided
        if not cleaned_data.get('template_style'):
            cleaned_data['template_style'] = 'fitness'
        
        if category == 'fitness' and not fitness_goal and not cleaned_data.get('custom_goal'):
            self.add_error('fitness_goal', 'Please select a fitness goal or add a custom goal.')
        
        if category == 'wellness' and not wellness_focus and not cleaned_data.get('custom_goal'):
            self.add_error('wellness_focus', 'Please select a wellness focus or add a custom goal.')
        
        return cleaned_data
    
    def save(self, commit=True):
        journey = super().save(commit=False)
        journey.current_day_override = self.cleaned_data.get('current_day_override')
        journey.template_style = self.cleaned_data.get('template_style', 'fitness')
        
        if commit:
            journey.save()
            
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                journey.journeytag_set.all().delete()
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
# ACTIVITY FORMS — Daily Fitness/Wellness Entries
# ============================================================================

class ActivityForm(forms.ModelForm):
    """Create/Edit a daily fitness or wellness entry"""
    
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
            'placeholder': "What did you do today? Share your workout, nutrition, or wellness progress...",
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
    
    activity_type = forms.ChoiceField(
        choices=Activity.WORKOUT_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="What type of activity did you do?"
    )
    
    duration_minutes = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '30',
            'min': 1
        }),
        help_text="Duration in minutes"
    )
    
    intensity = forms.ChoiceField(
        choices=Activity.INTENSITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="How intense was it?"
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
            'placeholder': 'e.g., {"weight": 75, "distance": 5.2, "reps": 10}'
        }),
        help_text="JSON format: {'metric_name': value}"
    )
    
    location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Where did this happen? (e.g., Gym, Park, Home)'
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
            'title', 'content', 'summary', 'activity_type', 'duration_minutes', 'intensity',
            'media_file', 'media_caption', 'day_number_field', 'actual_date',
            'mood', 'progress_metrics', 'location', 'is_draft'
        ]
    
    def __init__(self, *args, **kwargs):
        self.journey = kwargs.pop('journey', None)
        self.day_number = kwargs.pop('day_number', None)
        super().__init__(*args, **kwargs)
        
        if self.day_number:
            self.fields['day_number_field'].initial = self.day_number
        
        if self.journey:
            if self.journey.category == 'fitness':
                self.fields['content'].widget.attrs['placeholder'] = f"What did you do for fitness on Day {self.day_number}? Share your workout, progress, and how you felt..."
            else:
                self.fields['content'].widget.attrs['placeholder'] = f"How was your wellness practice on Day {self.day_number}? Share your mindfulness, nutrition, or recovery..."
    
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
                if self.journey.is_day_locked(day_number):
                    raise ValidationError(f"Day {day_number} is not available yet.")
                
                existing = Activity.objects.filter(
                    journey=self.journey,
                    day_number_field=day_number
                )
                if self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)
                
                if existing.exists():
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
# REFLECTION FORMS (Replaces JournalEntry)
# ============================================================================

class ReflectionForm(forms.ModelForm):
    """Personal reflection form for fitness & wellness"""
    
    summary = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'What was this reflection about?'
        }),
        help_text="A short summary of what you're reflecting on"
    )
    
    reflection = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'How did you feel? What did you learn from today\'s experience?',
            'rows': 5
        })
    )
    
    reflection_type = forms.ChoiceField(
        choices=Reflection.REFLECTION_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    mood = forms.ChoiceField(
        choices=Reflection.MOOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    energy_level = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '1-10',
            'min': 1,
            'max': 10
        }),
        help_text="Rate your energy on a scale of 1-10"
    )
    
    sleep_hours = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=24,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '7.5',
            'step': '0.5',
            'min': 0,
            'max': 24
        }),
        help_text="How many hours of sleep did you get?"
    )
    
    related_journey = forms.ModelChoiceField(
        queryset=Journey.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Link this reflection to one of your journeys"
    )
    
    related_activity = forms.ModelChoiceField(
        queryset=Activity.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Link this reflection to a specific activity"
    )
    
    is_private = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        help_text="Private reflections stay between you and your journey"
    )
    
    class Meta:
        model = Reflection
        fields = [
            'summary', 'reflection', 'reflection_type', 'mood',
            'energy_level', 'sleep_hours', 'related_journey', 'related_activity',
            'is_private'
        ]
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['related_journey'].queryset = Journey.objects.filter(
                creator__user=user,
                is_active=True
            ).order_by('-created_at')
            
            if self.instance and self.instance.related_activity:
                self.fields['related_activity'].queryset = Activity.objects.filter(
                    journey__creator__user=user
                ).order_by('-created_at')
            else:
                self.fields['related_activity'].widget.attrs['disabled'] = True


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
    
    include_reflections = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    class Meta:
        model = Export
        fields = ['format', 'include_media', 'include_comments', 'include_reflections']


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
        ('-view_count', 'Most Viewed'),
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
    
    subject = forms.ChoiceField(
        choices=ContactMessage.SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'How can we help you with your fitness or wellness journey?',
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