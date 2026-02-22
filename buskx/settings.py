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
DEBUG = env.bool('DEBUG', default=False)

# 🔧 FIX: allow BOTH domains so redirects work cleanly
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'rallynex.com',
    'www.rallynex.com',
    'localhost',
    '127.0.0.1',

])

# =====================================================
# APPLICATIONS
# =====================================================
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

    'cloudinary',
    'cloudinary_storage',
]

CRONJOBS = [
    ('0 */24 * * *', 'campaigns.cron.send_pledge_reminders'),
]

# =====================================================
# MIDDLEWARE
# =====================================================
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
    'buskx.middlewares.WWWRedirectMiddleware',  # 🔧 MUST be 301
]

ROOT_URLCONF = 'buskx.urls'
WSGI_APPLICATION = 'buskx.wsgi.application'

# =====================================================
# TEMPLATES
# =====================================================
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

# =====================================================
# DATABASE
# =====================================================
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

# =====================================================
# CSRF
# =====================================================
CSRF_TRUSTED_ORIGINS = [
    'https://rallynex.com',
    'https://www.rallynex.com',

]

# =====================================================
# AUTH
# =====================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'accounts.validators.AnyPasswordValidator'},
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1

# 🔧 FIX: single canonical source of truth
SITE_URL = 'https://rallynex.com'
SITE_DOMAIN = 'rallynex.com'
SITE_NAME = "RallyNex"

# =====================================================
# ALLAUTH
# =====================================================
ACCOUNT_LOGIN_METHODS = {'username'}
ACCOUNT_SIGNUP_FIELDS = ['username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_EMAIL_CONFIRMATION_HMAC = False

LOGIN_REDIRECT_URL = '/rallynex-logo/'
LOGOUT_REDIRECT_URL = 'index'

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'accounts.adapter.CustomSocialAccountAdapter'

ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_BLACKLIST = ['admin', 'administrator', 'moderator', 'root']

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
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'

# =====================================================
# CLOUDINARY
# =====================================================
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

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
# PAYMENTS (UNCHANGED)
# =====================================================
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE = env('PAYPAL_MODE', default='sandbox')
PAYPAL_PLATFORM_ACCOUNT = env('PAYPAL_PLATFORM_ACCOUNT', default='')
PAYPAL_BRAND_NAME = 'RALLYNEX'
PAYPAL_ENABLE_PAYOUTS = env.bool('PAYPAL_ENABLE_PAYOUTS', default=False)

PAYPAL_API_BASE = (
    "https://api-m.sandbox.paypal.com"
    if PAYPAL_MODE == "sandbox"
    else "https://api-m.paypal.com"
)

FLUTTERWAVE_PUBLIC_KEY = os.environ.get('FLUTTERWAVE_PUBLIC_KEY')
FLUTTERWAVE_SECRET_KEY = os.environ.get('FLUTTERWAVE_SECRET_KEY')
FLUTTERWAVE_SECRET_HASH = os.environ.get('FLUTTERWAVE_SECRET_HASH')

# =====================================================
# MISC
# =====================================================

PRIVACY_POLICY_LINK = env('PRIVACY_POLICY_LINK', default='/privacy-policy/')
TERMS_OF_SERVICE_LINK = env('TERMS_OF_SERVICE_LINK', default='/terms-of-service/')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================
# LOGGING
# =====================================================
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

# settings.py
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
    'toolbar2': '''
        visualblocks visualchars |
        charmap hr pagebreak nonbreaking anchor | code |
    ''',
    'contextmenu': 'formats | link image',
    'menubar': True,
    'statusbar': True,
    'images_upload_url': '/upload_image/',  # Add this endpoint
}


