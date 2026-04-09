from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary:
        return dictionary.get(key)
    return None

@register.filter
def get_range(value):
    """Return a range from 1 to value"""
    return range(1, int(value) + 1)