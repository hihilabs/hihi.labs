import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://hihilabs.xyz',
    'https://www.hihilabs.xyz',
    'https://hihilabs.communityplaylist.com',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'apps.claude_ai',
    'apps.projects',
    'apps.sound',
    'apps.servers',
    'apps.tax',
    'apps.billing',
    'apps.core',
    'apps.subscriptions',
    'apps.messaging',
    'apps.modules',
    'apps.workers',
    'apps.ops',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.subscriptions.middleware.SubscriptionMiddleware',
]

ROOT_URLCONF = 'hihilabs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hihilabs.context_processors.site_globals',
                'apps.subscriptions.context_processors.subscription_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'hihilabs.wsgi.application'

_DATA_DIR = Path(os.environ.get('DATA_DIR', BASE_DIR))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _DATA_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/ai/'

DEPLOY_WEBHOOK_SECRET = os.environ.get('DEPLOY_WEBHOOK_SECRET', '')
DEPLOY_WEBHOOK_URL    = os.environ.get('DEPLOY_WEBHOOK_URL', 'http://localhost:8000/ops/deploy/')
SSH_PRIVATE_KEY_B64   = os.environ.get('SSH_PRIVATE_KEY_B64', '')

# AI
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Chat model tiers
CLAUDE_CHAT_MODEL = 'claude-sonnet-4-6'               # chat + self-editing
CLAUDE_SMART_MODEL = 'claude-sonnet-4-6'              # templates, complex tasks
WHISPER_MODEL = 'whisper-1'

# Branding
SITE_NAME = os.environ.get('SITE_NAME', 'HiHi Labs')
SITE_OWNER = os.environ.get('SITE_OWNER', 'Andrew')

DISCORD_WEBHOOK_OPS = os.environ.get('DISCORD_WEBHOOK_OPS', '')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
        },
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
}

# PWA Push Notifications
VAPID_PRIVATE_KEY_B64 = os.getenv("VAPID_PRIVATE_KEY_B64", "")
VAPID_PUBLIC_KEY_B64  = os.getenv("VAPID_PUBLIC_KEY_B64", "")
VAPID_CLAIM_EMAIL     = os.getenv("VAPID_CLAIM_EMAIL", "webmaster@hihilabs.xyz")

# Payments
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PHANTOM_WALLET_ADDRESS = os.getenv("PHANTOM_WALLET_ADDRESS", "")
HELIUM_WALLET_ADDRESS  = os.getenv("HELIUM_WALLET_ADDRESS", "")
