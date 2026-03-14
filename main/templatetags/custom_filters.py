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