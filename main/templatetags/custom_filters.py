from django import template

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