# blog_filters.py
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def contains(value, arg):
    """Check if value contains arg (case-insensitive)."""
    if not value or not arg:
        return False
    return arg.lower() in value.lower()

@register.filter
def safe_lower(value):
    """Safely convert to lowercase."""
    if value:
        return value.lower()
    return ''

@register.filter
def has_faq(value):
    """Check if content has FAQ-related content."""
    if not value:
        return False
    content_lower = value.lower()
    faq_keywords = ['faq', 'question', 'frequently asked', 'q&a', 'q and a']
    return any(keyword in content_lower for keyword in faq_keywords)