import os
from pathlib import Path
from dotenv import load_dotenv
import environ
import dj_database_url

import cloudinary
import cloudinary.uploader
import cloudinary.api

# =====================================================
# ENV SETUP
# =====================================================
load_dotenv()
env = environ.Env()

env_file = Path(__file__).resolve().parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================
# SECURITY
# =====================================================
SECRET_KEY = env('SECRET_KEY', default='unsafe-secret-key-for-development-only')
DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'localhost',
    '127.0.0.1',
    'rallynex.com',
    'www.rallynex.com',
])

# =====================================================
# APPLICATIONS
# =====================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.sitemaps',

    # Third party
    'tinymce',
    'cloudinary',
    'cloudinary_storage',
    'crispy_forms',
    'django_extensions',
    'background_task',

    # Main app
    'main.apps.MainConfig',
]

# =====================================================
# MIDDLEWARE
# =====================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'main.middleware.NonWWWRedirectMiddleware', 
]

ROOT_URLCONF = 'buskx.urls'
WSGI_APPLICATION = 'buskx.wsgi.application'

# =====================================================
# TEMPLATES
# =====================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'main/templates'),
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.cloudinary_config',  # Add this for Cloudinary config in templates
                'main.context_processors.theme_context',
            ],
        },
    },
]


# =====================================================
# DATABASE - NEONDB PRODUCTION READY (FIXED)
# =====================================================
import ssl
import sys

DATABASE_URL = os.getenv('DATABASE_URL')

# Check if running collectstatic - use dummy database
if 'collectstatic' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
elif DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # Add ALL options at once (don't overwrite)
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',           # Required for NeonDB
        'connect_timeout': 30,          # Increased timeout
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    }
else:
    # Fallback - will error clearly if DATABASE_URL is missing
    raise ValueError("DATABASE_URL environment variable is not set")


# =====================================================
# CSRF
# =====================================================
CSRF_TRUSTED_ORIGINS = [
    'https://www.rallynex.com',
    'https://rallynex.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# =====================================================
# AUTH
# =====================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
]

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

SITE_ID = 1
SITE_URL = 'http://localhost:8000'
SITE_DOMAIN = 'localhost'
SITE_NAME = "RallyNex"

# =====================================================
# LOGIN/LOGOUT
# =====================================================
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'landing'
LOGIN_REDIRECT_URL = '/onboarding/'

# =====================================================
# LOCALIZATION
# =====================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True



# =====================================================
# STATIC & MEDIA
# =====================================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# =====================================================
# CLOUDINARY - PRODUCTION READY
# =====================================================
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
    
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
    
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# =====================================================
# PAYMENTS
# =====================================================
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE = env('PAYPAL_MODE', default='sandbox')
PAYPAL_BRAND_NAME = 'RALLYNEX'

# =====================================================
# TINYMCE
# =====================================================
TINYMCE_DEFAULT_CONFIG = {
    'height': 500,
    'width': '100%',
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 20,
    'selector': 'textarea',
    'theme': 'silver',
    'plugins': '''
        textcolor save link image media preview codesample contextmenu
        table code lists fullscreen insertdatetime nonbreaking
        directionality searchreplace wordcount visualblocks
        visualchars code fullscreen autolink lists charmap print hr
        anchor pagebreak
    ''',
    'toolbar1': '''
        fullscreen preview bold italic underline | fontselect,
        fontsizeselect | forecolor backcolor | alignleft alignright |
        aligncenter alignjustify | indent outdent | bullist numlist table |
        | link image media | codesample |
    ''',
    'contextmenu': 'formats | link image',
    'menubar': True,
    'statusbar': True,
}

# =====================================================
# MISC
# =====================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================
# LOGGING
# =====================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'main': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# Force non-www domain (rallynex.com instead of www.rallynex.com)
PREPEND_WWW = False

# Canonical URL settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'