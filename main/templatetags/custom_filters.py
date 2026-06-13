from django import template
import re

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using key"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def get_range(value):
    """Return a range from 1 to value"""
    return range(1, value + 1)


@register.filter
def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    if not url:
        return ''
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})',
        r'shorts\/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ''


@register.filter
def truncatechars(value, arg):
    """Truncate a string to a certain number of characters"""
    if not value:
        return ''
    try:
        limit = int(arg)
    except ValueError:
        return value
    if len(value) <= limit:
        return value
    return value[:limit] + '...'