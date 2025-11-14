from .settings import *

# Override settings for build environment
DEBUG = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dummy',
    'API_KEY': 'dummy', 
    'API_SECRET': 'dummy',
    'SECURE': True,
}