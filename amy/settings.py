"""
Django settings for amy project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import json
import os
import sys

from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/


# SECURITY WARNING: don't run with DEBUG turned on in production!
DEBUG = json.loads(os.environ.get('AMY_DEBUG', 'true'))
# For deployment in production:
# AMY_DEBUG=false AMY_SECRET_KEY="..." ./manage.py runserver ...

if DEBUG:
    SECRET_KEY = '3l$35+@a%g!(^y^98oi%ei+%+yvtl3y0k^_7-fmx2oj09-ac5@'
else:
    SECRET_KEY = None
SECRET_KEY = os.environ.get('AMY_SECRET_KEY', SECRET_KEY)

# settings for PyData application
ENABLE_PYDATA = json.loads(os.environ.get('AMY_ENABLE_PYDATA', 'false'))

if ENABLE_PYDATA:
    PYDATA_USERNAME_SECRET = os.environ.get('AMY_PYDATA_USERNAME')
    PYDATA_PASSWORD_SECRET = os.environ.get('AMY_PYDATA_PASSWORD')

# be sure to put these values in your envvars, even for development
RECAPTCHA_PUBLIC_KEY = os.environ.get('AMY_RECAPTCHA_PUBLIC_KEY', None)
RECAPTCHA_PRIVATE_KEY = os.environ.get('AMY_RECAPTCHA_PRIVATE_KEY', None)
RECAPTCHA_USE_SSL = True
NOCAPTCHA = True  # nicer input

if DEBUG:
    # 'PASSED' in the form will always pass the RECAPTCHA test
    NOCAPTCHA = False  # uglier input, but possible to manually enter 'PASSED'
    os.environ['RECAPTCHA_TESTING'] = 'True'
else:
    # ensure the keys are present on production
    assert RECAPTCHA_PUBLIC_KEY, 'RECAPTCHA site key not present'
    assert RECAPTCHA_PRIVATE_KEY, 'RECAPTCHA secure key not present'

# email settings
ADMINS = (
    ('Sysadmins ML', 'sysadmin@lists.software-carpentry.org'),
)
# "From:" for error messages sent out to ADMINS
SERVER_EMAIL = os.environ.get('AMY_SERVER_EMAIL', 'root@localhost')

# addresses to receive "New workshop request" or "New profile update request"
# notifications
REQUEST_NOTIFICATIONS_RECIPIENTS = (
    'admin-all@lists.software-carpentry.org',
)
EMAIL_HOST = os.environ.get('AMY_EMAIL_HOST', 'localhost')
EMAIL_HOST_USER = os.environ.get('AMY_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('AMY_EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = int(os.environ.get('AMY_EMAIL_PORT', 25))
EMAIL_TIMEOUT = 10  # timeout for blocking email operations, in seconds
EMAIL_USE_TLS = json.loads(os.environ.get('AMY_EMAIL_USE_TLS', 'false'))
EMAIL_USE_SSL = json.loads(os.environ.get('AMY_EMAIL_USE_SSL', 'false'))

# "From:" for NOT error messages (ie. sent to whoever we want)
DEFAULT_FROM_EMAIL = os.environ.get('AMY_DEFAULT_FROM_EMAIL',
                                    'webmaster@localhost')

if DEBUG:
    # outgoing mails will be stored in `django.core.mail.outbox`
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

SITE_URL = 'https://amy.software-carpentry.org'
if DEBUG:
    SITE_URL = 'http://127.0.0.1:8000'

# New template settings (for Django >= 1.8)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                'app_namespace.Loader',
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'debug': DEBUG,
            'context_processors': [
                # default processors + request processor
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                # AMY version
                'workshops.context_processors.version',
                # GitHub auth
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
            ],

            # Warn viewers of invalid template strings
            'string_if_invalid': 'XXX-unset-variable-XXX',
        }
    }
]

ALLOWED_HOSTS = [
    'amy.software-carpentry.org',
]
if DEBUG:
    ALLOWED_HOSTS.append('127.0.0.1')

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
if ENABLE_PYDATA:
    INSTALLED_APPS += [
        'pydata',
    ]
INSTALLED_APPS += [
    'workshops',
    # this should be after 'workshops' because templates in
    # 'templates/registration/' clash
    'django.contrib.admin',
    'crispy_forms',
    'selectable',
    'django_countries',
    'django_filters',
    'reversion',
    'rest_framework',
    'api',
    'extforms',
    'captcha',
    'compressor',
    'social.apps.django_app.default',
    'debug_toolbar',
]

CRISPY_TEMPLATE_PACK = 'bootstrap3'

MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'workshops.github_auth.GithubAuthMiddleware',
)

ROOT_URLCONF = 'amy.urls'

WSGI_APPLICATION = 'amy.wsgi.application'

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.INFO: 'alert-info',
    message_constants.SUCCESS: 'alert-success',
    message_constants.WARNING: 'alert-warning',
    message_constants.ERROR: 'alert-danger',
}


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'TEST': {},
    }
}
if '--keepdb' in sys.argv:
    # By default, Django uses in-memory sqlite3 database, which is much
    # faster than sqlite3 database in a file. However, we may want to keep
    # database between test launches, so that we avoid the overhead of
    # applying migrations on each test launch.
    DATABASES['default']['TEST']['NAME'] = 'test_db.sqlite3'

# Authentication
AUTH_USER_MODEL = 'workshops.Person'
VALIDATION = 'django.contrib.auth.password_validation.'
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': VALIDATION + 'UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'personal', 'middle', 'family',
                                'email')
        }
    },
    {
        'NAME': VALIDATION + 'MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': VALIDATION + 'CommonPasswordValidator',
    },
    {
        'NAME': VALIDATION + 'NumericPasswordValidator',
    },
]

# GitHub Auth
AUTHENTICATION_BACKENDS = (
    'social.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['github']
SOCIAL_AUTH_GITHUB_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_KEY', '').strip()
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_SECRET', '').strip()
if not DEBUG and not (SOCIAL_AUTH_GITHUB_KEY and SOCIAL_AUTH_GITHUB_SECRET):
    print('Logging using github account will *not* work, '
          'because you didn\'t set SOCIAL_AUTH_GITHUB_KEY and/or '
          'SOCIAL_AUTH_GITHUB_SECRET environment variables.',
          file=sys.stderr)


SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',

    # If we can't find Person associated with given github account, abort.
    'workshops.github_auth.abort_if_no_user_found',

    # The default pipeline includes 'social.pipeline.user.create_user' here,
    # but we don't want to register a new Person when somebody logs in
    # using GitHub account that is not associated with any Person.

    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
)

SOCIAL_AUTH_USER_MODEL = 'workshops.Person'

# Github API token (optional). Setting this token reduces limits and quotes
# on Github API.

GITHUB_API_TOKEN = os.environ.get('GITHUB_API_TOKEN', None)

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'EST'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'bower_components'),
)
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

# if "next" (or "?next") variable is not set when logging in, redirect to
# workshops
LOGIN_REDIRECT_URL = '/workshops/'

# here's where @login_required redirects to:
LOGIN_URL = '/account/login/'

# explicitely add European Union as a country
COUNTRIES_OVERRIDE = {
    'EU': _('European Union'),
    'US': _('United States'),
    'W3': _('Online'),
}

# settings for REST API
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework_yaml.parsers.YAMLParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_yaml.renderers.YAMLRenderer',
    ),

    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '50/hour',
        'user': '200/hour'
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # merge with default configuration
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # disable "Invalid HTTP_HOST" notifications
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
    },
}

# weaker hasher brings test speedup according to Django docs:
# https://docs.djangoproject.com/en/1.9/topics/testing/overview/#speeding-up-the-tests
if DEBUG and 'test' in sys.argv:
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )

# Debug Toolbar
DEBUG_TOOLBAR_PATCH_SETTINGS = False
INTERNAL_IPS = ['127.0.0.1', '::1']
