import os
from pathlib import Path
from dotenv import load_dotenv
import environ

# Load environment variables
env = environ.Env()

# Load .env file
env_file = Path(__file__).resolve().parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# BASE_DIR configuration
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = env('SECRET_KEY', default='unsafe-secret-key-for-development-only')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'www.rallynex.com',
    'localhost', 
    '127.0.0.1',
    'rallynex1.onrender.com', 
    'campaign-platform-kmv9.onrender.com',
])

# Application definitions
INSTALLED_APPS = [
    'tinymce',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
   
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'storages',
    'accounts',
    'crispy_forms',
    'main.apps.MainConfig',
    'django.contrib.sitemaps',
    'django_extensions',
    'django.contrib.humanize',
    'django_summernote',
    'django_quill',
    'django_crontab',
    'background_task',
]

CRONJOBS = [
    ('0 */24 * * *', 'campaigns.cron.send_pledge_reminders'),
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'buskx.middlewares.LegalLinksMiddleware',
]

ROOT_URLCONF = 'buskx.urls'

# Templates configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'accounts/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI application
WSGI_APPLICATION = 'buskx.wsgi.application'

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='temp_db_for_build'),
        'USER': env('DB_USER', default='temp_user'),
        'PASSWORD': env('DB_PASSWORD', default='temp_password'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

CSRF_TRUSTED_ORIGINS = [
    'https://www.rallynex.com',
    'https://rallynex.com',
    'https://rallynex1.onrender.com',
    'https://campaign-platform-kmv9.onrender.com', 
]

# Authentication and password validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'accounts.validators.AnyPasswordValidator',
    },
]

# Localization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================
# Cloudinary Configurations - SIMPLIFIED
# ==============================

# Cloudinary settings with defaults
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'dummy_cloud_name'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', 'dummy_api_key'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', 'dummy_api_secret'),
    'SECURE': True,
}

# ALWAYS use Cloudinary for media files in production
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = f'https://res.cloudinary.com/{CLOUDINARY_STORAGE["CLOUD_NAME"]}/media/'

# Static files - use WhiteNoise for production
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

if not DEBUG:
    # Production: Use WhiteNoise for static files
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    # Development: Use local storage for static files
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# =========================
# Email settings WITH DEFAULTS
# =========================

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)

# Add empty string defaults to prevent None values
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='rallynex1@gmail.com')


# =========================
# Authentication backends
# =========================
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1

# =========================
# Google OAuth (Allauth Social) WITH DEFAULTS
# =========================
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': env('SOCIALACCOUNT_GOOGLE_CLIENT_ID', default=''),
            'secret': env('SOCIALACCOUNT_GOOGLE_SECRET', default=''),
            'key': ''
        }
    }
}

# =========================
# Allauth modern settings
# =========================


# =========================
# Allauth modern settings
# =========================

# Use the new ACCOUNT_LOGIN_METHODS instead of deprecated settings
ACCOUNT_LOGIN_METHODS = {'username'}  # For username-only login
# OR for both username and email:
# ACCOUNT_LOGIN_METHODS = {'username', 'email'}

# Signup fields - include email if verification is mandatory
ACCOUNT_SIGNUP_FIELDS = ['username*', 'email*', 'password1*', 'password2*']

# Email verification options: 'mandatory', 'optional', or 'none'
# If you set to 'mandatory', you MUST include 'email*' in SIGNUP_FIELDS
ACCOUNT_EMAIL_VERIFICATION = env('ACCOUNT_EMAIL_VERIFICATION', default='none')

# Redirects
LOGIN_REDIRECT_URL = '/rallynex-logo/'
LOGOUT_REDIRECT_URL = 'index'

# Social account settings
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True

# Custom adapter (optional)
SOCIALACCOUNT_ADAPTER = 'accounts.adapter.CustomSocialAccountAdapter'

# Username settings (optional)
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_BLACKLIST = ['admin', 'administrator', 'moderator', 'root']  # Optional




# TinyMCE configuration
TINYMCE_DEFAULT_CONFIG = {
    'height': 360,
    'width': 800,
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 20,
    'selector': 'textarea',
    'plugins': '''
        textcolor save link image media preview codesample contextmenu
        table code lists fullscreen insertdatetime nonbreaking
        contextmenu directionality searchreplace wordcount visualblocks
        visualchars code fullscreen autolink lists charmap print
        hr anchor pagebreak
        ''',
    'toolbar': '''
        undo redo | styleselect | bold italic | alignleft aligncenter
        alignright alignjustify | bullist numlist outdent indent | link image | codesample
        ''',
    'menubar': True,
    'statusbar': True,
    'contextmenu': True,
}

# File upload size limit
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# Legal links settings WITH DEFAULTS
PRIVACY_POLICY_LINK = env('PRIVACY_POLICY_LINK', default='/privacy-policy/')
TERMS_OF_SERVICE_LINK = env('TERMS_OF_SERVICE_LINK', default='/terms-of-service/')

# Default auto field setting
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

 # Detect environment and set accordingly
import os
if 'RENDER' in os.environ:
    SITE_URL = 'https://campaign-platform-kmv9.onrender.com'
    SITE_DOMAIN = 'campaign-platform-kmv9.onrender.com'
else:
    SITE_URL = 'https://www.rallynex.com'
    SITE_DOMAIN = 'www.rallynex.com'



# PayPal settings WITH DEFAULTS
PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE = env('PAYPAL_MODE', default='sandbox')
PAYPAL_PLATFORM_ACCOUNT = env('PAYPAL_PLATFORM_ACCOUNT', default='')
PAYPAL_BRAND_NAME = 'RALLYNEX'
PAYPAL_ENABLE_PAYOUTS = env.bool('PAYPAL_ENABLE_PAYOUTS', default=False)
PAYPAL_API_BASE = (
    "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox"
    else "https://api-m.paypal.com"
)

# RECOMMENDED Branding Settings (customized for Rallynex)
PAYPAL_PAYMENT_DESCRIPTOR = "RALLYNEX*DONATION"  # Will appear on bank statements (22 char max)

# Flutterwave settings WITH DEFAULTS
FLUTTERWAVE_PUBLIC_KEY = os.environ.get('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_SECRET_KEY = os.environ.get('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_ENCRYPTION_KEY = os.environ.get('FLUTTERWAVE_ENCRYPTION_KEY', '')
FLUTTERWAVE_PLATFORM_SUBACCOUNT = os.getenv("FLUTTERWAVE_PLATFORM_SUBACCOUNT", "")
FLUTTERWAVE_REDIRECT_URL = "http://127.0.0.1:8000/donations/flutterwave/callback/" 

PLATFORM_SUBACCOUNT_ID = env("FLUTTERWAVE_PLATFORM_SUBACCOUNT_ID", default="")

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'django_errors.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'main': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}