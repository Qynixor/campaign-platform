# main/templatetags/custom_filters.py
import re
from django import template
from django.db.models import Sum
from django.forms import BoundField
from django.template.defaultfilters import stringfilter
from django.utils.timesince import timesince
from django.utils import timezone

register = template.Library()

# ============================================================================
# FORM FIELD FILTERS
# ============================================================================

@register.filter(name='add_class')
def add_class(field, css_class):
    """Add a CSS class to a form field"""
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={"class": css_class})
    elif isinstance(field, str):
        # Handle string fields (like rendered radio buttons)
        return field
    else:
        # Fallback for other field types
        return field


# ============================================================================
# NUMBER FORMATTING FILTERS
# ============================================================================

@register.filter
def format_count(value):
    """
    Format numbers for display (e.g., 1000 becomes 1K, 1000000 becomes 1M)
    """
    try:
        value = int(value)
        if value >= 1000000:
            # Remove .0 if it's a whole number
            result = f'{value/1000000:.1f}M'
            return result.replace('.0M', 'M')
        elif value >= 1000:
            result = f'{value/1000:.1f}K'
            return result.replace('.0K', 'K')
        else:
            return str(value)
    except (ValueError, TypeError):
        return "0"


@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


# ============================================================================
# K-FORMAT FILTER (YOUR MAIN FILTER)
# ============================================================================

@register.filter
def k_format(value):
    """
    Convert numbers to K format (1000 -> 1K, 1500 -> 1.5K)
    Usage: {{ value|k_format }}
    """
    try:
        value = float(value)
        if value >= 1000000:
            return f"{value/1000000:.1f}M".replace('.0M', 'M')
        elif value >= 1000:
            return f"{value/1000:.1f}K".replace('.0K', 'K')
        elif value.is_integer():
            return str(int(value))
        else:
            return f"{value:.1f}"
    except (ValueError, TypeError):
        return "0"


# ============================================================================
# DICTIONARY/OBJECT FILTERS
# ============================================================================

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None


# ============================================================================
# STRING FORMATTING FILTERS
# ============================================================================

@register.filter
def regex_replace(value, pattern):
    """Replace regex pattern with empty string"""
    try:
        return re.sub(pattern, '', value)
    except (TypeError, re.error):
        return value


@register.filter
def digits_only(value):
    """Remove all non-digit characters (for phone numbers)"""
    if not value:
        return ""
    try:
        return re.sub(r'[^0-9]', '', str(value))
    except (TypeError, re.error):
        return value


@register.filter
def truncatechars(text, length):
    """
    Truncate text to a certain number of characters
    Usage: {{ text|truncatechars:50 }}
    """
    try:
        if len(text) > length:
            return text[:length] + '...'
        return text
    except (TypeError, ValueError):
        return text


# ============================================================================
# TIME FORMATTING FILTERS
# ============================================================================

@register.filter
def timesince_short(date):
    """
    Show timesince in a shorter format
    Usage: {{ date|timesince_short }}
    """
    try:
        if not date:
            return ''
        
        delta = timezone.now() - date
        
        if delta.days > 365:
            years = delta.days // 365
            return f"{years}y"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months}mo"
        elif delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}m"
        else:
            return "now"
    except (AttributeError, TypeError):
        return ""


# ============================================================================
# PLEDGE/PAYMENT FILTERS
# ============================================================================

@register.filter
def fulfilled_count(pledges):
    """Count fulfilled pledges"""
    try:
        return pledges.filter(is_fulfilled=True).count()
    except AttributeError:
        return 0


@register.filter
def pending_count(pledges):
    """Count pending pledges"""
    try:
        return pledges.filter(is_fulfilled=False).count()
    except AttributeError:
        return 0


@register.filter
def sum_pledges(pledges):
    """Sum of all pledge amounts"""
    try:
        return pledges.aggregate(total=Sum('amount'))['total'] or 0
    except (AttributeError, KeyError):
        return 0


# ============================================================================
# TRIBE/COMMUNITY FILTERS
# ============================================================================

@register.filter
def has_joined_tribe(campaign, user_profile):
    """Check if a user has joined the campaign's sound tribe"""
    if not user_profile:
        return False
    try:
        return campaign.has_user_joined_tribe(user_profile)
    except AttributeError:
        return False


@register.filter
def user_in_tribe(campaign, user):
    """Check if user is in campaign's tribe"""
    if not user or not user.is_authenticated:
        return False
    try:
        return campaign.has_user_joined_tribe(user.profile)
    except AttributeError:
        return False


# ============================================================================
# CLOUDINARY IMAGE OPTIMIZATION FILTERS
# ============================================================================

@register.filter
def cloudinary_optimize(url, size=140):
    """
    Add Cloudinary transformations to optimize profile picture
    and remove white dots/noise artifacts
    
    Usage: {{ profile.image.url|cloudinary_optimize:140 }}
           {{ profile.image.url|cloudinary_optimize:"300,200" }}
    """
    if not url or 'cloudinary' not in str(url):
        return url
    
    try:
        url_str = str(url)
        
        # Parse size if it's in format "width,height"
        if isinstance(size, str) and ',' in size:
            width, height = size.split(',')
            width = width.strip()
            height = height.strip()
        else:
            width = height = str(size)
        
        # Insert transformations before the version
        # Cloudinary URL pattern: .../upload/v1234567/image.jpg
        parts = url_str.split('/upload/')
        
        if len(parts) == 2:
            # Add transformations:
            # w_{width},h_{height} - resize to dimensions
            # c_fill - crop to fill exactly
            # g_face - focus on faces
            # q_auto:best - automatic quality
            # f_auto - automatic format (WebP if supported)
            # e_sharpen - slight sharpening to reduce soft edges
            transformations = f'w_{width},h_{height},c_fill,g_face,q_auto:best,f_auto,e_sharpen:100'
            
            # Insert transformations
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
        
    except Exception as e:
        # If anything fails, return original URL
        print(f"Cloudinary optimization error: {e}")
        return url


@register.filter
def cloudinary_optimize_avatar(url, size=140):
    """
    Specialized version for circular avatars with extra edge smoothing
    to eliminate white dots/noise around the edges
    
    Usage: {{ profile.image.url|cloudinary_optimize_avatar:140 }}
    """
    if not url or 'cloudinary' not in str(url):
        return url
    
    try:
        url_str = str(url)
        parts = url_str.split('/upload/')
        
        if len(parts) == 2:
            # For circular avatars, add radius and edge smoothing
            # r_max - maximum rounding for perfect circle
            # e_sharpen:150 - extra sharpening to hide artifacts
            # e_ripple:0 - smooth edge anti-aliasing
            # e_contrast:5 - slight contrast to clean edges
            transformations = f'w_{size},h_{size},c_fill,g_face,r_max,q_auto:best,f_auto,e_sharpen:150,e_contrast:5'
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
        
    except Exception as e:
        print(f"Cloudinary avatar optimization error: {e}")
        return url


@register.filter
def cloudinary_remove_artifacts(url):
    """
    Special filter just to remove white dots/noise artifacts
    Use this if you're still seeing artifacts after regular optimization
    
    Usage: {{ profile.image.url|cloudinary_remove_artifacts }}
    """
    if not url or 'cloudinary' not in str(url):
        return url
    
    try:
        url_str = str(url)
        parts = url_str.split('/upload/')
        
        if len(parts) == 2:
            # e_artifact:remove - Cloudinary's specific artifact removal
            # e_contrast:10 - slight contrast to clean edges
            # e_sharpen:100 - sharpen to hide artifacts
            transformations = f'q_auto:best,f_auto,e_artifact:remove,e_contrast:10,e_sharpen:100,e_vibrance:10'
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
        
    except Exception as e:
        print(f"Cloudinary artifact removal error: {e}")
        return url


@register.filter
def cloudinary_cover(url, dimensions="1200,400"):
    """
    Optimize cover/banner images
    
    Usage: {{ user_profile.image.url|cloudinary_cover:"1200,400" }}
    """
    if not url or 'cloudinary' not in str(url):
        return url
    
    try:
        url_str = str(url)
        
        # Parse dimensions
        if ',' in dimensions:
            width, height = dimensions.split(',')
            width = width.strip()
            height = height.strip()
        else:
            width = height = dimensions
        
        parts = url_str.split('/upload/')
        
        if len(parts) == 2:
            # For cover images: crop to fill, moderate sharpening
            transformations = f'w_{width},h_{height},c_fill,q_auto:best,f_auto,e_sharpen:50'
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
        
    except Exception as e:
        print(f"Cloudinary cover optimization error: {e}")
        return url