# main/forms.py

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from tinymce.widgets import TinyMCE

from .models import (
    Profile, Campaign, Comment, Activity, SupportCampaign,
    ActivityComment, CampaignProduct, Report, NotInterested,
    UserVerification, Pledge, Blog, Donation
)

# ============================================================================
# CUSTOM VALIDATORS
# ============================================================================

def validate_no_long_words(value):
    """Check if any word exceeds 20 characters"""
    for word in value.split():
        if len(word) > 20:
            raise ValidationError(f"Word '{word}' exceeds the allowed length of 20 characters.")

# main/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
import logging

logger = logging.getLogger(__name__)

class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'placeholder': 'your-email@example.com'
        })
    )
    
    paypal_email = forms.EmailField(
        required=True,
        label="PayPal Email",
        help_text="Required—we need your PayPal email to send you payouts.",
        widget=forms.EmailInput(attrs={
            'placeholder': 'your-email@paypal.com'
        })
    )
    
    terms_agreement = forms.BooleanField(
        required=True,
        error_messages={
            'required': 'You must agree to the terms and conditions to sign up.'
        }
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_paypal_email(self):
        paypal_email = self.cleaned_data.get('paypal_email')
        print(f"Cleaning paypal_email: {paypal_email}")
        if not paypal_email:
            raise forms.ValidationError("PayPal email is required to receive payouts.")
        return paypal_email
    
    def save(self, commit=True):
        print("DEBUG: Entering save method")
        # Save user
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        paypal_email = self.cleaned_data.get('paypal_email')
        print(f"DEBUG: PayPal email from form: {paypal_email}")
        
        if commit:
            user.save()
            print(f"DEBUG: User saved with username: {user.username}")
            
            # Create or update profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.paypal_email = paypal_email
            profile.save()
            print(f"DEBUG: Profile {'created' if created else 'updated'} with PayPal email: {profile.paypal_email}")
            
            # Double-check it saved
            profile.refresh_from_db()
            print(f"DEBUG: Verified profile PayPal email after save: {profile.paypal_email}")
        
        return user

# ============================================================================
# PROFILE FORMS
# ============================================================================

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'image', 'bio', 'contact', 'location',
            'date_of_birth', 'gender', 'highest_level_of_education',
            'paypal_email'
        ]
        widgets = {
            'paypal_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'your-email@paypal.com'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'contact': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your phone number'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'City, Country'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'highest_level_of_education': forms.Select(attrs={
                'class': 'form-select'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-file'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional
        for field in self.fields:
            self.fields[field].required = False


class ProfileSearchForm(forms.Form):
    search_query = forms.CharField(label='Search', max_length=100)


# ============================================================================
# USER FORMS
# ============================================================================

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {
            'username': 'Username:',
            'email': 'Email:'
        }


# ============================================================================
# CAMPAIGN FORMS
# ============================================================================

class CampaignForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Add tags separated by commas...'
        }),
        help_text="Separate tags with commas (e.g., education, children, school)"
    )
    
    additional_images = forms.FileField(
        required=False,
        label="Additional Images for Slideshow",
        help_text="Upload up to 4 additional images for your poster slideshow (optional)",
        widget=forms.FileInput(attrs={
            'accept': 'image/png, image/jpeg, image/gif, image/webp'
        })
    )
    
    class Meta:
        model = Campaign
        fields = [
            'title', 'category', 'poster', 'audio',
            'content', 'duration',
            'duration_unit', 'funding_goal'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., 90 Days Discipline (4 words max)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Tell people more about your campaign...',
                'rows': 5
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'duration': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'placeholder': 'e.g., 30'
            }),
            'duration_unit': forms.Select(attrs={
                'class': 'form-select',
            }),
            'funding_goal': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'poster': forms.FileInput(attrs={
                'accept': 'image/png, image/jpeg, image/gif, image/webp',
                'class': 'file-upload-input'
            }),
            'audio': forms.FileInput(attrs={
                'accept': 'audio/*',
                'class': 'file-upload-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Required fields
        self.fields['title'].required = True
        self.fields['content'].required = True
        self.fields['category'].required = True
        
        # Optional fields
        self.fields['poster'].required = False
        self.fields['audio'].required = False
        self.fields['duration'].required = False
        self.fields['duration_unit'].required = False
        self.fields['funding_goal'].required = False
        self.fields['tags_input'].required = False
        self.fields['additional_images'].required = False
        
        # Add empty choice to duration_unit dropdown
        self.fields['duration_unit'].widget.choices = [
            ('', 'Select unit (optional)'),
            ('days', 'Days'),
            ('minutes', 'Minutes'),
        ]
        
        # Set defaults for required fields for new campaigns
        if not self.instance.pk:
            self.fields['category'].initial = 'Personal Empowerment'
        
        # Pre-populate with existing tags if editing
        if self.instance and self.instance.pk:
            existing_tags = ', '.join([tag.name for tag in self.instance.tags.all()])
            self.fields['tags_input'].initial = existing_tags
    
    def clean_funding_goal(self):
        """Ensure funding_goal has a value, default to 0.00"""
        funding_goal = self.cleaned_data.get('funding_goal')
        if funding_goal is None or funding_goal == '':
            return 0.00
        return funding_goal
    
    def clean_duration(self):
        """Validate duration is positive if provided"""
        duration = self.cleaned_data.get('duration')
        
        # If duration is empty string, set to None
        if duration == '':
            return None
            
        if duration is not None and duration <= 0:
            raise ValidationError("Duration must be a positive number.")
        
        return duration
    
    def clean(self):
        """Custom validation for duration fields"""
        cleaned_data = super().clean()
        duration = cleaned_data.get('duration')
        duration_unit = cleaned_data.get('duration_unit')
        
        # If this is an existing campaign
        if self.instance and self.instance.pk:
            # If duration is being changed but unit not provided, use existing unit
            if duration and not duration_unit:
                cleaned_data['duration_unit'] = self.instance.duration_unit
            # If unit is being changed but duration not provided, use existing duration
            elif duration_unit and not duration:
                cleaned_data['duration'] = self.instance.duration
        else:
            # New campaign validation
            if duration and not duration_unit:
                self.add_error('duration_unit', 'Please select a duration unit if you set a duration.')
            if duration_unit and not duration:
                self.add_error('duration', 'Please enter a duration if you select a unit.')
        
        return cleaned_data
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        
        if title:
            word_count = len(title.split())
            
            # 4 words max
            if word_count > 4:
                raise forms.ValidationError(
                    f"Title must be 4 words or less. You used {word_count} words."
                )
            
        return title
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # Handle tags if provided
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                # Clear existing tags
                instance.tags.clear()
                
                # Add new tags
                tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
                for tag_name in tag_names:
                    from .models import Tag
                    tag, created = Tag.objects.get_or_create(name=tag_name.lower())
                    instance.tags.add(tag)
        
        return instance


class CampaignSearchForm(forms.Form):
    search_query = forms.CharField(label='Search', max_length=100)


# ============================================================================
# ACTIVITY FORMS
# ============================================================================

class ActivityForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        label="Add Media (optional)",
        help_text="Upload image, video or audio file (max 100MB for videos, 10MB for images)",
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*,video/*,audio/*',
            'class': 'file-input',
            'multiple': False
        })
    )
    
    screenshot_count = forms.ChoiceField(
        choices=[(3, '3 photos'), (5, '5 photos'), (7, '7 photos'), (10, '10 photos')],
        initial=5,
        required=False,
        widget=forms.Select(attrs={
            'class': 'screenshot-count-select',
            'style': 'display: none;'
        })
    )
    
    class Meta:
        model = Activity
        fields = ['content', 'file', 'screenshot_count']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share an update, ask for help, celebrate progress...',
                'class': 'activity-content'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['content'].required = False
            self.fields['content'].initial = ''
    
    def _get_file_name(self, file):
        """Safely get filename from any file type (regular file or Cloudinary)"""
        try:
            if hasattr(file, 'name'):
                return file.name.lower()
            elif hasattr(file, 'public_id'):
                return file.public_id.lower()
            elif hasattr(file, 'url'):
                url_parts = str(file.url).split('/')
                return url_parts[-1].lower() if url_parts else ""
            else:
                return str(file).lower()
        except (AttributeError, TypeError):
            return ""
    
    def _get_content_type(self, file):
        """Safely get content type from any file type"""
        try:
            if hasattr(file, 'content_type'):
                return file.content_type
            elif hasattr(file, 'file') and hasattr(file.file, 'content_type'):
                return file.file.content_type
            elif hasattr(file, 'resource_type'):
                return file.resource_type
            return ""
        except (AttributeError, TypeError):
            return ""
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        file = cleaned_data.get('file')
        
        if not content and not file:
            raise forms.ValidationError(
                "Please provide either content or a media file for the activity."
            )
        return cleaned_data

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            validate_no_long_words(content)
        return content

    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            file_name = self._get_file_name(file)
            content_type = self._get_content_type(file)
            
            is_video = False
            is_image = False
            
            if content_type:
                is_video = content_type.startswith('video/') or content_type == 'video'
                is_image = content_type.startswith('image/') or content_type == 'image'
            
            if not (is_video or is_image):
                video_exts = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v', '.mpg', '.mpeg']
                image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
                
                is_video = any(file_name.endswith(ext) for ext in video_exts)
                is_image = any(file_name.endswith(ext) for ext in image_exts)
            
            max_size = 500 * 1024 * 1024
            size_limit_mb = 500
            
            if is_image:
                max_size = 20 * 1024 * 1024
                size_limit_mb = 20
            elif is_video:
                max_size = 500 * 1024 * 1024
                size_limit_mb = 500
            
            if hasattr(file, 'size') and file.size:
                if file.size > max_size:
                    file_type = "Video" if is_video else "Image" if is_image else "File"
                    raise forms.ValidationError(
                        f'{file_type} size must be under {size_limit_mb}MB. '
                        f'Current size: {file.size / (1024*1024):.1f}MB'
                    )
            
            if not (is_video or is_image) and content_type and not content_type.startswith('audio/'):
                audio_exts = ['.mp3', '.wav', '.ogg', '.m4a']
                is_audio = any(file_name.endswith(ext) for ext in audio_exts) or content_type.startswith('audio/')
                if not is_audio:
                    raise forms.ValidationError('Only image, video, and audio files are allowed')
            
            self.cleaned_data['_is_video'] = is_video
            self.cleaned_data['_is_image'] = is_image
        
        return file


class ActivityCommentForm(forms.ModelForm):
    class Meta:
        model = ActivityComment
        fields = ['content']

    def clean_content(self):
        content = self.cleaned_data.get('content')
        validate_no_long_words(content)
        return content


# ============================================================================
# COMMENT FORMS
# ============================================================================

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

    def clean_text(self):
        text = self.cleaned_data.get('text')
        validate_no_long_words(text)
        return text


# ============================================================================
# SUPPORT FORMS
# ============================================================================

class SupportForm(forms.ModelForm):
    class Meta:
        model = SupportCampaign
        fields = []


# ============================================================================
# PRODUCT FORMS
# ============================================================================

class CampaignProductForm(forms.ModelForm):
    class Meta:
        model = CampaignProduct
        fields = ['name', 'description', 'image', 'price', 'stock_quantity', 'stock_status', 'is_active']


# ============================================================================
# REPORT FORMS
# ============================================================================

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        validate_no_long_words(reason)
        return reason

    def clean_description(self):
        description = self.cleaned_data.get('description')
        validate_no_long_words(description)
        return description


# ============================================================================
# NOT INTERESTED FORMS
# ============================================================================

class NotInterestedForm(forms.ModelForm):
    class Meta:
        model = NotInterested
        fields = ['campaign']


# ============================================================================
# VERIFICATION FORMS
# ============================================================================

class UserVerificationForm(forms.ModelForm):
    class Meta:
        model = UserVerification
        fields = ['document_type', 'document']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'custom-select'}),
            'document': forms.ClearableFileInput(attrs={'class': 'custom-file-input'}),
        }
    
    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            if document.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5 MB.")
        return document

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.user = user
        if commit:
            instance.save()
        return instance


class VerificationRequestForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea)


class VerificationReviewForm(forms.Form):
    approval_status = forms.ChoiceField(choices=[(True, 'Approve'), (False, 'Deny')])
    review_comment = forms.CharField(widget=forms.Textarea, required=False)


# ============================================================================
# PLEDGE FORMS
# ============================================================================

class PledgeForm(forms.ModelForm):
    class Meta:
        model = Pledge
        fields = ['campaign', 'amount', 'contact']
        widgets = {
            'campaign': forms.HiddenInput(),
            'amount': forms.NumberInput(attrs={
                'min': '1',
                'step': '0.01',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        campaign = kwargs.pop('campaign', None)
        super().__init__(*args, **kwargs)
        
        if campaign:
            self.initial['campaign'] = campaign
            self.fields['campaign'].widget = forms.HiddenInput()
        
        self.fields['amount'].min_value = 1


# ============================================================================
# DONATION FORMS
# ============================================================================

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter donation amount',
                'step': '0.01',
                'min': '1'
            }),
        }
        labels = {
            'amount': 'Donation Amount',
        }


# ============================================================================
# BLOG FORMS
# ============================================================================

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = '__all__'
        widgets = {
            'content': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'excerpt': forms.Textarea(attrs={'rows': 4}),
            'meta_description': forms.Textarea(attrs={'rows': 3}),
        }