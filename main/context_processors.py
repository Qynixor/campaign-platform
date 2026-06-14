from django.conf import settings

def cloudinary_config(request):
    """Make Cloudinary cloud name available in templates"""
    return {
        'CLOUDINARY_CLOUD_NAME': getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''),
    }


# your_app/context_processors.py

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
    if request.user.is_authenticated:
        from .models import Notification
        count = Notification.objects.filter(user=request.user, viewed=False).count()
        return {'unread_count': count}
    return {'unread_count': 0}