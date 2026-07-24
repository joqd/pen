import os
from pathlib import Path

from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip(""").strip(""")
        os.environ.setdefault(key, value)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


load_env_file(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me')
DEBUG = env_bool('DJANGO_DEBUG', True)
# ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', ['127.0.0.1', 'localhost', 'testserver'])
ALLOWED_HOSTS = ['*']
# CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = [
    'http://*',
    'https://*',
]

SESSION_COOKIE_SECURE = False  # for dev
CSRF_COOKIE_SECURE = False  # for dev

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    # 3rd party
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'corsheaders',
    'django_filters',
    # my own
    'apps.accounts',
    'apps.catalog',
    'apps.orders',
    'apps.gallery',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'program.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'program.wsgi.application'

DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite')
if DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'program'),
            'USER': os.environ.get('DB_USER', 'program'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

TAILWIND_APP_NAME = 'apps.theme'

AUTH_USER_MODEL = 'accounts.User'

LANGUAGE_CODE = 'fa-ir'
LANGUAGES = [('fa', _('Persian'))]
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'Asia/Tehran')
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

SMS_IR_API_KEY = os.environ.get('SMS_IR_API_KEY')
SMS_IR_LINE_NUMBER = os.environ.get('SMS_IR_LINE_NUMBER')

JQUERY_URL = True

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

UNFOLD = {
    'SITE_TITLE': _('admin panel'),
    'SITE_HEADER': _('shop management'),
    'SITE_SYMBOL': 'storefront',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'STYLES': [
        lambda request: static('admin/css/custom.css'),
    ],
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': _('users and permissions'),
                'items': [
                    {
                        'title': _('users'),
                        'icon': 'person',
                        'link': reverse_lazy('admin:accounts_user_changelist'),
                    },
                    {
                        'title': _('addresses'),
                        'icon': 'location_on',
                        'link': reverse_lazy('admin:accounts_address_changelist'),
                    },
                ],
            },
            {
                'title': _('catalog'),
                'items': [
                    {
                        'title': _('products'),
                        'icon': 'inventory_2',
                        'link': reverse_lazy('admin:catalog_product_changelist'),
                    },
                    {
                        'title': _('collections'),
                        'icon': 'folder_special',
                        'link': reverse_lazy('admin:catalog_collection_changelist'),
                    },
                    {
                        'title': _('categories'),
                        'icon': 'category',
                        'link': reverse_lazy('admin:catalog_category_changelist'),
                    },
                    {
                        'title': _('tags'),
                        'icon': 'label',
                        'link': reverse_lazy('admin:catalog_tag_changelist'),
                    },
                ],
            },
            {
                'title': _('Cart and orders'),
                'items': [
                    {
                        'title': _('cart'),
                        'icon': 'shopping_cart',
                        'link': reverse_lazy('admin:orders_cart_changelist'),
                    },
                    {
                        'title': _('orders'),
                        'icon': 'receipt_long',
                        'link': reverse_lazy('admin:orders_order_changelist'),
                    },
                ],
            },
            {
                'title': _('Content'),
                'items': [
                    {
                        'title': _('gallery'),
                        'icon': 'photo_library',
                        'link': reverse_lazy('admin:gallery_customergallery_changelist'),
                    },
                ],
            },
        ],
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    'TITLE': 'Adagio Style Commerce API',
    'VERSION': '1.0.0',
    'DESCRIPTION': 'Backend API powering the **Adagio Style** online store.',
}
