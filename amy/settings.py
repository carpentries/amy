"""
Django settings for AMY project.
"""

import json
import os
import sys

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# SECURITY WARNING: don't run with DEBUG turned on in production!
DEBUG = json.loads(os.environ.get('AMY_DEBUG', 'true'))

##################### S E C R E T  K E Y #####################

# don't run with default SECRET_KEY on production
DEFAULT_SECRET_KEY = '3l$35+@a%g!(^y^98oi%ei+%+yvtl3y0k^_7-fmx2oj09-ac5@'
SECRET_KEY = os.environ.get('AMY_SECRET_KEY', DEFAULT_SECRET_KEY)
if not DEBUG and SECRET_KEY == DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured('You must specify non-default value for '
                               'SECRET_KEY when running with Debug=FALSE.')

##################### P Y D A T A #####################

# settings for PyData application
ENABLE_PYDATA = json.loads(os.environ.get('AMY_ENABLE_PYDATA', 'false'))

if ENABLE_PYDATA:
    PYDATA_USERNAME_SECRET = os.environ.get('AMY_PYDATA_USERNAME')
    PYDATA_PASSWORD_SECRET = os.environ.get('AMY_PYDATA_PASSWORD')

##################### R E C A P T C H A #####################

# be sure to put these values in your envvars, even for development
RECAPTCHA_PUBLIC_KEY = os.environ.get('AMY_RECAPTCHA_PUBLIC_KEY', None)
RECAPTCHA_PRIVATE_KEY = os.environ.get('AMY_RECAPTCHA_PRIVATE_KEY', None)
RECAPTCHA_USE_SSL = True
NOCAPTCHA = True  # nicer input

if DEBUG:
    # 'PASSED' in the form will always pass the RECAPTCHA test
    os.environ['RECAPTCHA_TESTING'] = 'True'
    # values below are from
    # https://developers.google.com/recaptcha/docs/faq#id-like-to-run-automated-tests-with-recaptcha-v2-what-should-i-do
    if not RECAPTCHA_PUBLIC_KEY:
        RECAPTCHA_PUBLIC_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
    if not RECAPTCHA_PRIVATE_KEY:
        RECAPTCHA_PRIVATE_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'
else:
    # ensure the keys are present on production
    if not RECAPTCHA_PUBLIC_KEY or not RECAPTCHA_PRIVATE_KEY:
        raise ImproperlyConfigured('Both ReCaptcha keys (public and private) '
                                   'must be present.')

##################### E M A I L S #####################

# error email recipients
ADMINS = (
    ('Sysadmins ML', 'sysadmin@lists.software-carpentry.org'),
)
# sender for error emails
SERVER_EMAIL = os.environ.get('AMY_SERVER_EMAIL', 'root@localhost')

# addresses to receive "New workshop request" or "New profile update request"
# notifications
REQUEST_NOTIFICATIONS_RECIPIENTS = (
    'admin-all@carpentries.org',
)
# default sender for non-error messages
DEFAULT_FROM_EMAIL = os.environ.get('AMY_DEFAULT_FROM_EMAIL',
                                    'webmaster@localhost')

# django-anymail configuration for Mailgun
ANYMAIL = {
    'MAILGUN_API_KEY': os.environ.get('AMY_MAILGUN_API_KEY', None),
    'MAILGUN_SENDER_DOMAIN': os.environ.get('AMY_MAILGUN_SENDER_DOMAIN', None),
}

if not DEBUG and (not ANYMAIL['MAILGUN_API_KEY'] or
                  not ANYMAIL['MAILGUN_SENDER_DOMAIN']):
    raise ImproperlyConfigured('Mailgun settings are required when running '
                               'with Debug=False.')

EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
if DEBUG:
    # outgoing mails will be stored in `django.core.mail.outbox`
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

##################### S I T E,  H O S T S #####################

SITE_URL = 'https://amy.software-carpentry.org'
if DEBUG:
    SITE_URL = 'http://127.0.0.1:8000'

ALLOWED_HOSTS = [
    'amy.software-carpentry.org',
]
if DEBUG:
    ALLOWED_HOSTS.append('127.0.0.1')

##################### T E M P L A T E S #####################

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
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
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],

            # Warn viewers of invalid template strings
            'string_if_invalid': 'XXX-unset-variable-XXX',
        }
    }
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

##################### I N S T A L L E D  A P P S #####################

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # pydata will be removed if ENABLE_PYDATA is not True
    'pydata',
    'workshops.apps.WorkshopsConfig',
    # dal (django-autocomplete-light) replaces django-selectable:
    'dal',
    'dal_select2',
    # this should be after 'workshops' because templates in
    # 'templates/registration/' clash
    'django.contrib.admin',
    'crispy_forms',
    'django_countries',
    'django_filters',
    'reversion',
    'reversion_compare',
    'rest_framework',
    'api',
    'extforms',
    'captcha',
    'compressor',
    'social_django',
    'debug_toolbar',
    'django_extensions',
    'anymail',
]
if not ENABLE_PYDATA:
    INSTALLED_APPS.remove('pydata')

##################### M I D D L E W A R E #####################

MIDDLEWARE = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'workshops.github_auth.GithubAuthMiddleware',
    'workshops.action_required.PrivacyPolicy',
)

##################### D A T A B A S E #####################

if DEBUG:
    DB_FILENAME = os.environ.get('AMY_DB_FILENAME', 'db.sqlite3')
else:
    try:
        DB_FILENAME = os.environ['AMY_DB_FILENAME']
    except KeyError as ex:
        raise ImproperlyConfigured(
            'You must specify AMY_DB_FILENAME environment variable '
            'when DEBUG is False.') from ex

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, DB_FILENAME),
        'TEST': {},
    }
}
if '--keepdb' in sys.argv:
    # By default, Django uses in-memory sqlite3 database, which is much
    # faster than sqlite3 database in a file. However, we may want to keep
    # database between test launches, so that we avoid the overhead of
    # applying migrations on each test launch.
    DATABASES['default']['TEST']['NAME'] = 'test_db.sqlite3'

##################### A U T H,  S O C I A L #####################

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
    'social_core.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['github']
SOCIAL_AUTH_GITHUB_KEY = os.environ.get('AMY_SOCIAL_AUTH_GITHUB_KEY', '').strip()
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('AMY_SOCIAL_AUTH_GITHUB_SECRET', '').strip()
if not DEBUG and not (SOCIAL_AUTH_GITHUB_KEY and SOCIAL_AUTH_GITHUB_SECRET):
    print('Logging using github account will *not* work, '
          'because you didn\'t set SOCIAL_AUTH_GITHUB_KEY and/or '
          'SOCIAL_AUTH_GITHUB_SECRET environment variables.',
          file=sys.stderr)


SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',

    # If we can't find Person associated with given github account, abort.
    'workshops.github_auth.abort_if_no_user_found',

    # The default pipeline includes 'social.pipeline.user.create_user' here,
    # but we don't want to register a new Person when somebody logs in
    # using GitHub account that is not associated with any Person.

    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
)

SOCIAL_AUTH_USER_MODEL = 'workshops.Person'

# Github API token (optional). Setting this token reduces limits and quotes
# on Github API.

GITHUB_API_TOKEN = os.environ.get('AMY_GITHUB_API_TOKEN', None)

################### I N T E R N A T I O N A L I Z A T I O N ###################

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'EST'

USE_I18N = True

USE_L10N = True

USE_TZ = True


##################### S T A T I C  F I L E S #####################

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'node_modules'),
)
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

##################### M I S C E L L A N E O U S #####################

ROOT_URLCONF = 'amy.urls'

WSGI_APPLICATION = 'amy.wsgi.application'

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.INFO: 'alert-info',
    message_constants.SUCCESS: 'alert-success',
    message_constants.WARNING: 'alert-warning',
    message_constants.ERROR: 'alert-danger',
}

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
        'user': '2000/hour'
    },

    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
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
