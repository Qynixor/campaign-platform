from django.conf import settings

def cloudinary_config(request):
    """Make Cloudinary cloud name available in templates"""
    return {
        'CLOUDINARY_CLOUD_NAME': getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''),
    }