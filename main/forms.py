from django import forms
from django.contrib.auth.models import User
from .models import Profile, Campaign, Comment, Activity, SupportCampaign, Chat, Message, Follow

from django.forms import inlineformset_factory

from .models import ActivityComment,CampaignProduct

from tinymce.widgets import TinyMCE
from .models import Report
from .models import NotInterested
from .models import Subscriber

from django.core.exceptions import ValidationError
from django import forms
from .models import UserVerification



# Custom validator to check for long words
def validate_no_long_words(value):
    for word in value.split():
        if len(word) > 20:  # Check if any word exceeds 20 characters
            raise ValidationError(f"Word '{word}' exceeds the allowed length of 20 characters.")

# ReportForm
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
        validate_no_long_words(reason)  # Validate the reason field
        return reason

    def clean_description(self):
        description = self.cleaned_data.get('description')
        validate_no_long_words(description)  # Validate the description field
        return description





from django import forms
from .models import CampaignProduct


from django import forms
from .models import CampaignProduct

class CampaignProductForm(forms.ModelForm):
    class Meta:
        model = CampaignProduct
        fields = ['name', 'description', 'image', 'price', 'stock_quantity', 'stock_status', 'is_active']






# ActivityCommentForm
class ActivityCommentForm(forms.ModelForm):
    class Meta:
        model = ActivityComment
        fields = ['content']

    def clean_content(self):
        content = self.cleaned_data.get('content')
        validate_no_long_words(content)  # Validate the content field
        return content




# main/forms.py
from django import forms
from .models import Activity
from .utils import validate_no_long_words

class ActivityForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        label="Add Media (optional)",
        help_text="Upload image, video or audio file (max 10MB)",
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*,video/*,audio/*',
            'class': 'file-input',
            'multiple': False
        })
    )
    
    class Meta:
        model = Activity
        fields = ['content', 'file']
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
            max_size = 10 * 1024 * 1024
            if file.size > max_size:
                raise forms.ValidationError(f'File size must be under {max_size/1024/1024}MB')
            
            allowed_types = ['image', 'video', 'audio']
            if not any(file.content_type.startswith(t) for t in allowed_types):
                raise forms.ValidationError('Only image, video, and audio files are allowed')
        return file






class ProfileForm(forms.ModelForm):
    paypal_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your PayPal email'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'image', 'bio', 'contact', 'location',
            'date_of_birth', 'gender', 'highest_level_of_education',
            'paypal_email'
        ]






# forms.py
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'file']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 1,
                'placeholder': 'Type a message...',
                'id': 'messageInput'
            }),
            'file': forms.FileInput(attrs={
                'id': 'fileInput',
                'style': 'display: none;',
                'accept': 'image/*,.pdf,.doc,.docx,.txt'
            })
        }

# CommentForm
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

    def clean_text(self):
        text = self.cleaned_data.get('text')
        validate_no_long_words(text)  # Validate the text field
        return text




class UserVerificationForm(forms.ModelForm):
    class Meta:
        model = UserVerification
        fields = ['document_type', 'document']  # Exclude the user field

        widgets = {
            'document_type': forms.Select(attrs={'class': 'custom-select'}),
            'document': forms.ClearableFileInput(attrs={'class': 'custom-file-input'}),
        }
    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            # You can add validation logic here, e.g., checking file type or size
            if document.size > 5 * 1024 * 1024:  # Example: limit file size to 5 MB
                raise forms.ValidationError("File size must be under 5 MB.")
        return document

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.user = user  # Set the user from the view
        if commit:
            instance.save()
        return instance



class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Enter your email',
                'required': True,
                'style': 'padding: 10px; width: 100%; box-sizing: border-box;'
            })
        }







class VerificationRequestForm(forms.Form):
    # You can include additional fields if needed
    message = forms.CharField(widget=forms.Textarea)

class VerificationReviewForm(forms.Form):
    # You can include additional fields if needed
    approval_status = forms.ChoiceField(choices=[(True, 'Approve'), (False, 'Deny')])
    review_comment = forms.CharField(widget=forms.Textarea, required=False)




class NotInterestedForm(forms.ModelForm):
    class Meta:
        model = NotInterested
        fields = ['campaign']











class ProfileSearchForm(forms.Form):
    search_query = forms.CharField(label='Search', max_length=100)

class CampaignSearchForm(forms.Form):
    search_query = forms.CharField(label='Search', max_length=100)


class SupportForm(forms.ModelForm):
    class Meta:
        model = SupportCampaign
        fields = []  # Remove the 'category' field from the list





class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {
            'username': 'Username:',
            'email': 'Email:'
        }





# Custom validator to check for long words
def validate_no_long_words(value):
    for word in value.split():
        if len(word) > 20:  # Check if any word exceeds 20 characters
            raise ValidationError(f"Word '{word}' exceeds the allowed length of 20 characters.")

from django.core.exceptions import ValidationError
from PIL import Image
import os
from .models import Campaign, Tag, CampaignTag

from django import forms
from .models import Campaign, Tag, CampaignTag
from django.core.exceptions import ValidationError
import os
from PIL import Image

# Your existing validation function
def validate_no_long_words(value, max_length=50):
    words = value.split()
    for word in words:
        if len(word) > max_length:
            raise ValidationError(f"Word '{word[:20]}...' is too long. Maximum word length is {max_length} characters.")






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
            'visibility', 'content', 'duration',
            'duration_unit', 'funding_goal'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'What\'s your campaign about?'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Tell people more about your campaign...',
                'rows': 5
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'duration': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'placeholder': 'e.g., 30'
            }),
            'duration_unit': forms.Select(attrs={
                'class': 'form-select',
                # Add empty option
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
        
        # Required fields (only title and content)
        self.fields['title'].required = True
        self.fields['content'].required = True
        self.fields['category'].required = True
        self.fields['visibility'].required = True
        
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
        
        # Set defaults for required fields
        if not self.instance.pk:  # Only for new campaigns
            self.fields['visibility'].initial = 'public'
            self.fields['category'].initial = 'Education for All'
        
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
        
        # If duration is empty string, set to None (optional)
        if duration == '':
            return None
            
        if duration is not None and duration <= 0:
            raise ValidationError("Duration must be a positive number.")
        
        return duration
    
    def clean_duration_unit(self):
        """Handle duration unit"""
        duration_unit = self.cleaned_data.get('duration_unit')
        duration = self.cleaned_data.get('duration')
        
        # If no duration is provided, duration_unit should be None
        if duration is None or duration == '':
            return None
        
        # If duration is provided but unit is empty, default to 'days'
        if duration and (duration_unit is None or duration_unit == ''):
            return 'days'
        
        return duration_unit
    
    def clean(self):
        """Custom validation for duration fields"""
        cleaned_data = super().clean()
        duration = cleaned_data.get('duration')
        duration_unit = cleaned_data.get('duration_unit')
        
        # If duration is provided but unit is not, show error
        if duration and not duration_unit:
            self.add_error('duration_unit', 'Please select a duration unit if you set a duration.')
        
        # If unit is provided but no duration, show error
        if duration_unit and not duration:
            self.add_error('duration', 'Please enter a duration if you select a unit.')
        
        return cleaned_data
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            validate_no_long_words(title)
        return title

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            validate_no_long_words(content)
        return content
    
    def clean_additional_images(self):
        """Clean additional images if you need validation"""
        return self.cleaned_data.get('additional_images')
    
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
                    tag, created = Tag.objects.get_or_create(name=tag_name.lower())
                    instance.tags.add(tag)
        
        return instance






class ChatForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(queryset=None, widget=forms.CheckboxSelectMultiple)
    
    class Meta:
        model = Chat
        fields = ('title', 'participants',)

    def __init__(self, user, *args, **kwargs):
        super(ChatForm, self).__init__(*args, **kwargs)
        
        # Get the current user's followers and followings
        followers = Follow.objects.filter(followed=user)
        followings = Follow.objects.filter(follower=user)
        
        # Create a list of followers and followings
        user_choices = [(follower.follower.pk, follower.follower.username) for follower in followers] + \
                       [(following.followed.pk, following.followed.username) for following in followings]
        
        # Set the queryset for the participants field
        self.fields['participants'].queryset = User.objects.filter(pk__in=[choice[0] for choice in user_choices])




class UpdateVisibilityForm(forms.ModelForm):
    followers_visibility = forms.ModelMultipleChoiceField(
        queryset=Profile.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select followers to view"
    )

    class Meta:
        model = Campaign
        fields = ['visibility', 'followers_visibility']

    def __init__(self, *args, **kwargs):
        followers = kwargs.pop('followers', None)
        super().__init__(*args, **kwargs)

        if followers:
            self.fields['followers_visibility'].queryset = followers




from django import forms
from .models import Pledge

class PledgeForm(forms.ModelForm):
    class Meta:
        model = Pledge
        fields = ['campaign', 'amount', 'contact']
        widgets = {
            'campaign': forms.HiddenInput(),  # We'll typically set this in the view
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
        
        # Set minimum amount validation
        self.fields['amount'].min_value = 1




# forms.py
from django import forms
from .models import Donation

# forms.py
class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount']  # remove 'destination'
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

