from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from cloudinary.forms import CloudinaryFileField
from .models import (
    Profile, Journey, Activity, Reflection, 
    Comment, JourneyFollow, Tag, Export, JourneyTag,
    ContactMessage, Subscriber
)
import re
import json
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
# PROFILE FORMS — Builder Profile
# ============================================================================

class ProfileForm(forms.ModelForm):
    """Edit profile information for builders"""
    
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
            'placeholder': 'Tell us about your building journey... What are you working on?',
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
            'placeholder': 'https://yourproduct.com'
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
    
    linkedin = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'LinkedIn URL or username'
        })
    )
    
    github = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'GitHub username'
        })
    )
    
    class Meta:
        model = Profile
        fields = ['image', 'bio', 'location', 'website', 'twitter', 'linkedin', 'github']
    
    def clean_twitter(self):
        username = self.cleaned_data.get('twitter', '')
        if username and not username.startswith('@'):
            username = '@' + username
        return username
    
    def clean_linkedin(self):
        username = self.cleaned_data.get('linkedin', '')
        if username:
            if 'linkedin.com/in/' in username:
                username = username.split('linkedin.com/in/')[-1].split('/')[0]
            if not username.startswith('@'):
                username = '@' + username
        return username
    
    def clean_github(self):
        username = self.cleaned_data.get('github', '')
        if username:
            username = username.replace('@', '')
            if 'github.com/' in username:
                username = username.split('github.com/')[-1].split('/')[0]
        return username



# ============================================================================
# JOURNEY FORMS — Build in Public Focus
# ============================================================================

class JourneyForm(forms.ModelForm):
    """Create/Edit a build in public journey"""
    
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., Building SaaS Product X, My Startup Journey',
            'autofocus': True
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'What are you building? Why does it matter? Share your vision...',
            'rows': 4
        })
    )
    
    journey_type = forms.ChoiceField(
        choices=Journey.JOURNEY_TYPES,
        initial='build_in_public',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    category = forms.ChoiceField(
        choices=Journey.CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    product_stage = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., Idea, MVP, Beta, Launch, Growth'
        }),
        help_text="What stage is your product at?"
    )
    
    product_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://yourproduct.com'
        }),
        help_text="Link to your product"
    )
    
    github_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://github.com/your-repo'
        }),
        help_text="Link to your GitHub repository"
    )
    
    # ❌ REMOVED cover_image field completely
    
    duration = forms.IntegerField(
        min_value=1,
        max_value=365,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '30',
            'min': 1,
            'max': 365
        }),
        help_text="Number of days for this journey"
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
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        help_text="Allow other builders to comment on your journey"
    )
    
    allow_followers = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        help_text="Allow others to follow your journey"
    )
    
    template_style = forms.ChoiceField(
        choices=Journey.TEMPLATE_STYLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'template-style-radio'
        }),
        initial='build_in_public',
        label='Display Style',
        help_text='How your journey looks to visitors'
    )
    
    tags_input = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'saas, startup, product, marketing, fundraising'
        }),
        help_text="Separate tags with commas (max 10)"
    )
    
    class Meta:
        model = Journey
        fields = [
            'title', 'description', 'journey_type', 'category', 'product_stage',
            'product_url', 'github_url',  # ❌ Removed 'cover_image' from here
            'duration', 'current_day_override', 'start_date', 'privacy_status', 
            'allow_comments', 'allow_followers', 'template_style'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not self.initial.get('template_style'):
            self.initial['template_style'] = 'build_in_public'
        
        if self.instance and self.instance.pk:
            self.fields['current_day_override'].initial = self.instance.current_day_override
            self.fields['template_style'].initial = self.instance.template_style or 'build_in_public'
            
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
        
        if not cleaned_data.get('template_style'):
            cleaned_data['template_style'] = 'build_in_public'
        
        return cleaned_data
    
    def save(self, commit=True):
        journey = super().save(commit=False)
        journey.current_day_override = self.cleaned_data.get('current_day_override')
        journey.template_style = self.cleaned_data.get('template_style', 'build_in_public')
        
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
        fields = ['privacy_status', 'allow_comments', 'allow_followers']
        widgets = {
            'privacy_status': forms.Select(attrs={'class': 'form-select'}),
            'allow_comments': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'allow_followers': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

# ============================================================================
# ACTIVITY FORMS — Daily Build in Public Entries
# ============================================================================

class ActivityForm(forms.ModelForm):
    """Create/Edit a daily build in public entry"""
    
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Optional: What did you ship today?'
        })
    )
    
    content = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': "What did you build today? What did you learn? What challenges did you face?",
            'rows': 4
        })
    )
    
    summary = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'A short summary of today\'s progress',
            'rows': 2
        })
    )
    
    activity_type = forms.ChoiceField(
        choices=Activity.ACTIVITY_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="What type of activity was this?"
    )
    
    product_area = forms.ChoiceField(
        choices=Activity.PRODUCT_AREAS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Which area of your product does this relate to?"
    )
    
    hours_spent = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=24,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 3.5',
            'step': '0.5',
            'min': 0,
            'max': 24
        }),
        help_text="Hours spent working on this today"
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
            'placeholder': 'Caption for your media (screenshot, demo video, etc.)'
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
            'type': 'date'
        }),
        help_text="The actual date of this entry"
    )
    
    custom_metrics = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '{"users": 150, "revenue": 1000, "followers": 50}'
        }),
        help_text="Custom metrics like users, revenue, followers (JSON format)"
    )
    
    is_draft = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        help_text="Save as draft without publishing"
    )
    
    # ✅ Source URL field
    source_url = forms.URLField(
        required=False,
        widget=forms.HiddenInput(),  # Hidden because users don't need to see it
        initial=''
    )
    
    # ✅ View count field (required by database)
    view_count = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.HiddenInput()
    )
    
    # ✅ Unique viewers field (if exists in model)
    unique_viewers = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = Activity
        fields = [
            'title', 'content', 'summary', 'activity_type', 'product_area',
            'hours_spent', 'media_file', 'media_caption', 'day_number_field', 
            'actual_date', 'custom_metrics', 'is_draft', 'source_url', 
            'view_count', 'unique_viewers'
        ]
    
    def __init__(self, *args, **kwargs):
        self.journey = kwargs.pop('journey', None)
        self.day_number = kwargs.pop('day_number', None)
        super().__init__(*args, **kwargs)
        
        if self.day_number:
            self.fields['day_number_field'].initial = self.day_number
        
        if self.journey:
            self.fields['content'].widget.attrs['placeholder'] = (
                f"What did you build on Day {self.day_number} of {self.journey.title}? "
                f"Share your progress, learnings, and challenges..."
            )
        
        # ✅ Set initial values for hidden fields
        if self.instance and self.instance.pk:
            self.fields['view_count'].initial = self.instance.view_count if hasattr(self.instance, 'view_count') else 0
            self.fields['unique_viewers'].initial = self.instance.unique_viewers if hasattr(self.instance, 'unique_viewers') else 0
        else:
            self.fields['view_count'].initial = 0
            self.fields['unique_viewers'].initial = 0
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        if not content.strip():
            raise ValidationError('Please share what you built or learned today.')
        return content
    
    def clean_custom_metrics(self):
        metrics = self.cleaned_data.get('custom_metrics', '')
        if metrics:
            try:
                return json.loads(metrics)
            except json.JSONDecodeError:
                raise ValidationError('Please enter valid JSON format.')
        return {}
    
    def clean_source_url(self):
        source_url = self.cleaned_data.get('source_url', '')
        if source_url is None:
            return ''
        return source_url
    
    def clean_view_count(self):
        view_count = self.cleaned_data.get('view_count', 0)
        if view_count is None:
            return 0
        return view_count
    
    def clean_unique_viewers(self):
        unique_viewers = self.cleaned_data.get('unique_viewers', 0)
        if unique_viewers is None:
            return 0
        return unique_viewers
    
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
                    raise ValidationError(f"Day {day_number} already has an entry.")
        
        return cleaned_data
    
    def save(self, commit=True):
        activity = super().save(commit=False)
        
        if self.journey:
            activity.journey = self.journey
        
        if self.day_number and not activity.day_number_field:
            activity.day_number_field = self.day_number
        
        # ✅ Ensure source_url is never None
        if hasattr(activity, 'source_url'):
            if activity.source_url is None or activity.source_url == '':
                activity.source_url = ''
        
        # ✅ Force set view_count to 0 if None
        if hasattr(activity, 'view_count'):
            if activity.view_count is None:
                activity.view_count = 0
        
        # ✅ Force set unique_viewers to 0 if None
        if hasattr(activity, 'unique_viewers'):
            if activity.unique_viewers is None:
                activity.unique_viewers = 0
        
        # ✅ Set published_at if it exists and is None
        if hasattr(activity, 'published_at'):
            if activity.published_at is None:
                from django.utils import timezone
                activity.published_at = timezone.now()
        
        if commit:
            activity.save()
        
        return activity


# ============================================================================
# REFLECTION FORMS — Personal Reflections on Building
# ============================================================================

class ReflectionForm(forms.ModelForm):
    """Personal reflection form for builders"""
    
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
            'placeholder': 'What did you learn? What challenges did you overcome? What\'s next?',
            'rows': 5
        })
    )
    
    reflection_type = forms.ChoiceField(
        choices=Reflection.REFLECTION_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
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
            'summary', 'reflection', 'reflection_type', 
            'related_journey', 'related_activity', 'is_private'
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
            'placeholder': 'Share your thoughts or encouragement...',
            'rows': 2
        })
    )
    
    class Meta:
        model = Comment
        fields = ['content']


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
    
    notify_on_completion = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    class Meta:
        model = JourneyFollow
        fields = ['notify_on_new_entry', 'notify_on_completion']


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
# SEARCH FORM
# ============================================================================

class JourneySearchForm(forms.Form):
    """Search and filter journeys"""
    
    SORT_CHOICES = [
        ('-created_at', 'Newest'),
        ('-updated_at', 'Recently Updated'),
        ('-view_count', 'Most Viewed'),
        ('-follower_count', 'Most Followed'),
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
            'placeholder': 'How can we help you with your Build in Public journey?',
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
# MONETIZATION FORMS - FRONTEND USER FORMS
# ============================================================================

class SubscribeForm(forms.Form):
    """Form for users to subscribe to Rallynex Plus"""
    plan_id = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.RadioSelect,
        empty_label=None
    )
    
    def __init__(self, *args, **kwargs):
        from .models import SubscriptionPlan
        super().__init__(*args, **kwargs)
        self.fields['plan_id'].queryset = SubscriptionPlan.objects.filter(is_active=True)
        self.fields['plan_id'].label = "Select Plan"
        self.fields['plan_id'].help_text = "Choose your subscription plan"


class PurchaseProductForm(forms.Form):
    """Form for users to purchase one-time products"""
    product_id = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.RadioSelect,
        empty_label=None
    )
    
    journey_id = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select journey for export or report"
    )
    
    def __init__(self, user, *args, **kwargs):
        from .models import OneTimeProduct
        super().__init__(*args, **kwargs)
        
        self.fields['product_id'].queryset = OneTimeProduct.objects.filter(is_active=True)
        self.fields['product_id'].label = "Select Product"
        
        if user and user.is_authenticated:
            try:
                self.fields['journey_id'].queryset = user.profile.journeys.filter(is_active=True)
            except:
                pass
        
        # Show journey field only when needed
        product_id = self.data.get('product_id') if self.data else None
        if product_id:
            try:
                product = OneTimeProduct.objects.filter(id=product_id).first()
                if product and product.product_type in ['export', 'ai_report']:
                    self.fields['journey_id'].required = True
                else:
                    self.fields['journey_id'].widget = forms.HiddenInput()
                    self.fields['journey_id'].required = False
            except:
                pass


class ExportRequestForm(forms.ModelForm):
    """Form for requesting a journey export"""
    class Meta:
        from .models import PaidJourneyExport
        model = PaidJourneyExport
        fields = ['format', 'include_media', 'include_reflections', 'include_comments']
        widgets = {
            'format': forms.Select(attrs={'class': 'form-control'}),
            'include_media': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_reflections': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_comments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'include_media': 'Include Media Files',
            'include_reflections': 'Include Reflections',
            'include_comments': 'Include Comments',
        }


class ThemeCustomizationForm(forms.ModelForm):
    """Form for customizing a journey theme"""
    class Meta:
        from .models import PaidCustomTheme
        model = PaidCustomTheme
        fields = ['name', 'theme_type', 'primary_color', 'secondary_color', 
                  'background_color', 'text_color', 'layout_style', 'font_family']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'theme_type': forms.Select(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'background_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'text_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'layout_style': forms.Select(attrs={'class': 'form-control'}),
            'font_family': forms.Select(attrs={'class': 'form-control'}),
        }


class AICustomizationForm(forms.Form):
    """Form for AI report customization"""
    report_title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter report title'})
    )
    include_sections = forms.MultipleChoiceField(
        choices=[
            ('summary', 'Summary'),
            ('insights', 'Key Insights'),
            ('recommendations', 'Recommendations'),
            ('metrics', 'Detailed Metrics'),
            ('progress', 'Progress Analysis'),
        ],
        widget=forms.CheckboxSelectMultiple,
        initial=['summary', 'insights', 'recommendations']
    )
    report_style = forms.ChoiceField(
        choices=[
            ('detailed', 'Detailed'),
            ('concise', 'Concise'),
            ('visual', 'Visual Focus'),
        ],
        widget=forms.RadioSelect,
        initial='detailed'
    )