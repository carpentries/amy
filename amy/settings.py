"""
Django settings for amy project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import json

from django.conf import global_settings

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


TEMPLATE_DEBUG = True

ALLOWED_HOSTS = [
    'software-carpentry.org',
    'software-carpentry.org.'
]


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'workshops',
    # this should be after 'workshops' because templates in
    # 'templates/registration/' clash
    'django.contrib.admin',
    'crispy_forms',
)

CRISPY_TEMPLATE_PACK = 'bootstrap3'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

# WARNING: in Django 1.8 processors get moved from ``django.core`` to
#          ``django.template``.
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    "django.core.context_processors.request",
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
    }
}

# Authentication

AUTH_USER_MODEL = 'workshops.Person'

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

# Warn viewers of invalid template strings
TEMPLATE_STRING_IF_INVALID = 'XXX-unset-variable-XXX'

# if "next" (or "?next") variable is not set when logging in, redirect to
# workshops
LOGIN_REDIRECT_URL = '/workshops/'

# here's where @login_required redirects to:
LOGIN_URL = '/account/login/'
