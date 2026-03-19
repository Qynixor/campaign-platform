# main/templatetags/custom_filters.py
import re
from django import template
from django.db.models import Sum
from django.utils import timezone

register = template.Library()

# ============================================================================
# CLOUDINARY IMAGE OPTIMIZATION FILTERS
# ============================================================================

@register.filter
def cloudinary_optimize(url, size="400,250"):
    """
    Generic Cloudinary optimization for campaign images
    Usage: {{ campaign.poster.url|cloudinary_optimize:"400,250" }}
    """
    if not url:
        return url
    
    try:
        url_str = str(url)
        
        # Only process if it's a Cloudinary URL
        if 'cloudinary' not in url_str:
            return url_str
        
        # Parse size
        if isinstance(size, str) and ',' in size:
            width, height = size.split(',')
            width = width.strip()
            height = height.strip()
        else:
            width = height = str(size)
        
        # Check if URL already has transformations
        if '/upload/' in url_str:
            parts = url_str.split('/upload/')
            # Add transformations
            transformations = f'w_{width},h_{height},c_fill,q_auto:best,f_auto'
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
        
    except Exception:
        # If anything fails, return original URL
        return url


@register.filter
def cloudinary_cover(url, dimensions="1200,400"):
    """
    Optimize cover/banner images
    Usage: {{ campaign.poster.url|cloudinary_cover:"1200,400" }}
    """
    if not url:
        return url
    
    try:
        url_str = str(url)
        
        if 'cloudinary' not in url_str:
            return url_str
        
        # Parse dimensions
        if isinstance(dimensions, str) and ',' in dimensions:
            width, height = dimensions.split(',')
            width = width.strip()
            height = height.strip()
        else:
            width = height = dimensions
        
        if '/upload/' in url_str:
            parts = url_str.split('/upload/')
            transformations = f'w_{width},h_{height},c_fill,q_auto:best,f_auto'
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
        
    except Exception:
        return url


@register.filter
def cloudinary_optimize_avatar(url, size=140):
    """Optimize avatar images"""
    if not url:
        return url
    
    try:
        url_str = str(url)
        
        if 'cloudinary' not in url_str:
            return url_str
        
        if '/upload/' in url_str:
            parts = url_str.split('/upload/')
            transformations = f'w_{size},h_{size},c_fill,g_face,r_max,q_auto:best,f_auto'
            return f"{parts[0]}/upload/{transformations}/{parts[1]}"
        
        return url_str
    except Exception:
        return url


# ============================================================================
# K-FORMAT FILTER
# ============================================================================

@register.filter
def k_format(value):
    """Convert numbers to K format (1000 -> 1K, 1500 -> 1.5K)"""
    try:
        value = float(value)
        if value >= 1000000:
            result = f"{value/1000000:.1f}M"
            return result.replace('.0M', 'M')
        elif value >= 1000:
            result = f"{value/1000:.1f}K"
            return result.replace('.0K', 'K')
        elif value.is_integer():
            return str(int(value))
        else:
            return f"{value:.1f}"
    except (ValueError, TypeError):
        return "0"


# ============================================================================
# MATH FILTERS - For premium stats calculations
# ============================================================================

@register.filter
def divide(value, arg):
    """
    Divide the value by the argument
    Usage: {{ value|divide:arg }}
    Example: {{ total|divide:count }}
    """
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """
    Multiply the value by the argument
    Usage: {{ value|multiply:arg }}
    Example: {{ rate|multiply:100 }}
    """
    try:
        value = float(value)
        arg = float(arg)
        return value * arg
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """
    Subtract argument from value
    Usage: {{ value|subtract:arg }}
    Example: {{ total|subtract:goal }}
    """
    try:
        value = float(value)
        arg = float(arg)
        return value - arg
    except (ValueError, TypeError):
        return 0


@register.filter
def add_filter(value, arg):
    """
    Add argument to value
    Usage: {{ value|add_filter:arg }}
    Example: {{ count|add_filter:5 }}
    """
    try:
        value = float(value)
        arg = float(arg)
        return value + arg
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calculate percentage
    Usage: {{ value|percentage:total }}
    Example: {{ donations|percentage:goal }}
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 0
        return (value / total) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def floatformat(value, decimals=0):
    """
    Format float with specified decimals
    Usage: {{ value|floatformat:2 }}
    """
    try:
        value = float(value)
        format_string = f"{{:.{decimals}f}}"
        return format_string.format(value)
    except (ValueError, TypeError):
        return "0" if decimals == 0 else "0." + "0" * decimals


# ============================================================================
# STRING FORMATTING FILTERS
# ============================================================================

@register.filter
def truncatechars(text, length):
    """Truncate text to a certain number of characters"""
    try:
        text = str(text)
        if len(text) > length:
            return text[:length] + '...'
        return text
    except (TypeError, ValueError):
        return text


@register.filter
def default_if_none(value, default):
    """Return default if value is None"""
    return default if value is None else value


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None


# ============================================================================
# DATE FILTERS
# ============================================================================

@register.filter
def days_since(date):
    """Calculate days since a given date"""
    try:
        if not date:
            return 0
        delta = timezone.now() - date
        return delta.days
    except (TypeError, AttributeError):
        return 0


@register.filter
def days_until(date):
    """Calculate days until a given date"""
    try:
        if not date:
            return 0
        delta = date - timezone.now()
        return max(0, delta.days)
    except (TypeError, AttributeError):
        return 0


# ============================================================================
# LIST/QUERY FILTERS
# ============================================================================

@register.filter
def sum_attribute(queryset, attribute):
    """Sum a specific attribute across a queryset"""
    try:
        return queryset.aggregate(total=Sum(attribute))['total'] or 0
    except (AttributeError, TypeError):
        return 0


@register.filter
def filter_by(queryset, **kwargs):
    """Filter queryset by kwargs"""
    try:
        return queryset.filter(**kwargs)
    except (AttributeError, TypeError):
        return queryset


# ============================================================================
# BOOLEAN FILTERS
# ============================================================================

@register.filter
def is_true(value):
    """Check if value is truthy"""
    return bool(value)


@register.filter
def is_false(value):
    """Check if value is falsy"""
    return not bool(value)