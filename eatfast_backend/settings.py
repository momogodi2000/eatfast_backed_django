"""
Django settings for eatfast_backend project.
Updated to use SQLite for local development and PostgreSQL for production.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# CORE SETTINGS
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Site Configuration
SITE_URL = config('SITE_URL', default='http://localhost:3000')

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_redis',
    'django_filters',
]

LOCAL_APPS = [
    'backend',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Custom User Model
AUTH_USER_MODEL = 'backend.User'

# ==============================================================================
# MIDDLEWARE CONFIGURATION
# ==============================================================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eatfast_backend.urls'

# ==============================================================================
# TEMPLATES CONFIGURATION
# ==============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
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

WSGI_APPLICATION = 'eatfast_backend.wsgi.application'

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

# Check if we're in production (Render) or development
IS_PRODUCTION = config('DATABASE_URL', default=None) is not None

if IS_PRODUCTION:
    # Production: Use PostgreSQL on Render
    print("🚀 Using PostgreSQL for production")
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL')
        )
    }
    
    # Database connection pooling for production
    DATABASES['default'].update({
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    })
else:
    # Development: Use SQLite for local development
    print("💻 Using SQLite for local development")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Commented out: Original PostgreSQL configuration for reference
# DATABASES = {
#     'default': dj_database_url.config(
#         default=config(
#             'DATABASE_URL', 
#             default=f'postgresql://{config("DB_USER", default="")}:'
#                    f'{config("DB_PASSWORD", default="")}@'
#                    f'{config("DB_HOST", default="localhost")}:'
#                    f'{config("DB_PORT", default="5432")}/'
#                    f'{config("DB_NAME", default="eatfast_db")}'
#         )
#     )
# }

# ==============================================================================
# CACHE CONFIGURATION
# ==============================================================================

if IS_PRODUCTION:
    # Production: Try to use Redis if available
    try:
        redis_url = config('REDIS_URL', default=None)
        if redis_url:
            CACHES = {
                'default': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': redis_url,
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    }
                }
            }
        else:
            # Fallback to dummy cache
            CACHES = {
                'default': {
                    'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
                }
            }
    except:
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        }
else:
    # Development: Use local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'eatfast-cache',
        }
    }

# ==============================================================================
# SESSION CONFIGURATION
# ==============================================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours

# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC & MEDIA FILES CONFIGURATION
# ==============================================================================

# Static Files Configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Create static directory if it doesn't exist
STATICFILES_DIRS = []
static_dir = os.path.join(BASE_DIR, 'static')
if os.path.exists(static_dir):
    STATICFILES_DIRS = [static_dir]

# Media Files Configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# File Type Validation
ALLOWED_UPLOAD_EXTENSIONS = [
    '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'
]

# ==============================================================================
# DJANGO REST FRAMEWORK CONFIGURATION
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'VERSION_PARAM': 'version',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# ==============================================================================
# CORS CONFIGURATION
# ==============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', 
    default='http://localhost:5173,http://localhost:3000'
).split(',')

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'content-disposition',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ==============================================================================
# EMAIL CONFIGURATION
# ==============================================================================

if IS_PRODUCTION:
    # Production email settings
    EMAIL_BACKEND = config(
        'EMAIL_BACKEND', 
        default='django.core.mail.backends.smtp.EmailBackend'
    )
    EMAIL_HOST = config('EMAIL_HOST', default='')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
else:
    # Development: Console email backend (prints emails to console)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email Configuration for Contact & Partner
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@eatfast.cm')
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@eatfast.cm')),
]

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

if IS_PRODUCTION:
    # Production security settings
    # HTTPS Security
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_PRELOAD = True
    
    # Cookie Security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    
    # Additional Security
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REDIRECT_EXEMPT = []
    
    # Render.com specific settings
    ALLOWED_HOSTS.append('.render.com')
else:
    # Development: Relaxed security settings
    ALLOWED_HOSTS = ['*']

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

# Create logs directory
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'backend': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ==============================================================================
# RATE LIMITING SETTINGS
# ==============================================================================

RATE_LIMIT_CONTACT_FORM = 5  # Max 5 submissions per hour per IP
RATE_LIMIT_PARTNER_APPLICATION = 3  # Max 3 applications per day per IP

# ==============================================================================
# MISCELLANEOUS SETTINGS
# ==============================================================================

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom Settings for Your App
EATFAST_SETTINGS = {
    'MAX_RESTAURANTS_PER_USER': 5,
    'MAX_MENU_ITEMS_PER_RESTAURANT': 100,
    'ORDER_TIMEOUT_MINUTES': 30,
    'DELIVERY_RADIUS_KM': 10,
}

# ==============================================================================
# ENVIRONMENT SPECIFIC SETTINGS
# ==============================================================================

# Development specific settings
if DEBUG and not IS_PRODUCTION:
    # Enable Django Debug Toolbar if installed (only in development)
    try:
        import debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
        print("🔧 Debug Toolbar enabled for development")
    except ImportError:
        pass

# Production specific settings
if IS_PRODUCTION:
    # Additional production middleware
    MIDDLEWARE.insert(1, 'django.middleware.cache.UpdateCacheMiddleware')
    MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')
    
    # Cache settings for production
    CACHE_MIDDLEWARE_ALIAS = 'default'
    CACHE_MIDDLEWARE_SECONDS = 600
    CACHE_MIDDLEWARE_KEY_PREFIX = 'eatfast'
    
    print("🚀 Production settings loaded")
else:
    print("💻 Development settings loaded")

# ==============================================================================
# DATABASE INFORMATION
# ==============================================================================

# Print database info for debugging
if DEBUG:
    db_engine = DATABASES['default']['ENGINE']
    if 'sqlite' in db_engine:
        print(f"📁 Database: SQLite at {DATABASES['default']['NAME']}")
    elif 'postgresql' in db_engine:
        print(f"🐘 Database: PostgreSQL at {DATABASES['default'].get('HOST', 'Render')}")
    else:
        print(f"🗄️ Database: {db_engine}")