from django.conf import settings

def cloudinary_config(request):
    """Make Cloudinary cloud name available in templates"""
    return {
        'CLOUDINARY_CLOUD_NAME': getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''),
    }


def theme_context(request):
    """
    Provides theme to ALL templates automatically.
    No need to modify each template individually.
    """
    theme = request.COOKIES.get('theme', 'light')
    return {
        'current_theme': theme,
        'is_dark_mode': theme == 'dark',
    }


def notification_count(request):
    """Get unread notification count for the current user"""
    if request.user.is_authenticated:
        from .models import Notification
        # FIXED: viewed → is_read (matches the renamed field in Notification model)
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_count': count}
    return {'unread_count': 0}