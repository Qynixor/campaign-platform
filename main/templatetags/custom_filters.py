# main/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    # If it's a list or other iterable, try to index it
    try:
        return dictionary[key]
    except (KeyError, IndexError, TypeError):
        return None

@register.filter
def get_attr(obj, attr):
    """Get an attribute from an object"""
    if obj is None:
        return None
    return getattr(obj, attr, None)

@register.filter
def truncatechars(value, arg):
    """Truncate a string to a certain number of characters"""
    if value is None:
        return ''
    try:
        length = int(arg)
    except ValueError:
        return value
    if len(value) <= length:
        return value
    return value[:length] + '...'

@register.filter
def filesizeformat(value):
    """Format a file size in bytes to human readable format"""
    if value is None:
        return '0 bytes'
    try:
        size = int(value)
    except (ValueError, TypeError):
        return '0 bytes'
    
    if size < 1024:
        return f"{size} bytes"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

@register.filter
def divisibleby(value, arg):
    """Check if a value is divisible by arg (for percentages)"""
    if value is None or arg is None:
        return 0
    try:
        return (float(value) / float(arg)) * 100
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def get_mood_emoji(mood):
    """Get emoji for mood"""
    mood_emojis = {
        'amazing': '🌟',
        'great': '💪',
        'good': '👍',
        'okay': '😐',
        'tired': '😴',
        'challenged': '💪',
        'struggling': '😞',
        'proud': '🏆',
        'grateful': '🙏',
        'neutral': '😶',
    }
    return mood_emojis.get(mood, '😊')

@register.filter
def get_activity_icon(activity_type):
    """Get icon for activity type"""
    icons = {
        'cardio': '🏃',
        'strength': '💪',
        'hiit': '🔥',
        'yoga': '🧘',
        'pilates': '🧘',
        'walking': '🚶',
        'running': '🏃',
        'cycling': '🚴',
        'swimming': '🏊',
        'sports': '⚽',
        'stretching': '🤸',
        'other': '🏋️',
    }
    return icons.get(activity_type, '🏋️')

@register.filter
def get_intensity_label(intensity):
    """Get label for intensity"""
    labels = {
        'low': '🟢 Low',
        'medium': '🟡 Medium',
        'high': '🔴 High',
    }
    return labels.get(intensity, intensity)

@register.simple_tag
def multiply(value, arg):
    """Multiply two numbers"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0