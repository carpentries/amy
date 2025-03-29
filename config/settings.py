"""
Django settings for AMY project.
"""

from pathlib import Path
from typing import cast

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
import environ  # type: ignore
import jinja2

ROOT_DIR = Path(__file__).parent.parent  # amy/
APPS_DIR = ROOT_DIR / "amy"

# set default values
env = environ.Env(
    CI=(bool, False),
    AMY_DEBUG=(bool, True),
    AMY_SITE_ID=(int, 2),
    AMY_ALLOWED_HOSTS=(list, ["amy.carpentries.org"]),
    AMY_CSRF_TRUSTED_ORIGINS=(list, []),
    AMY_DATABASE_HOST=(str, "localhost"),
    AMY_DATABASE_PORT=(int, 5432),
    AMY_DATABASE_NAME=(str, "amy"),
    AMY_DATABASE_USER=(str, "amy"),
    AMY_DATABASE_PASSWORD=(str, "amypostgresql"),
    AMY_RECAPTCHA_PUBLIC_KEY=(str, "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"),
    AMY_RECAPTCHA_PRIVATE_KEY=(str, "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"),
    AMY_SOCIAL_AUTH_GITHUB_KEY=(str, ""),
    AMY_SOCIAL_AUTH_GITHUB_SECRET=(str, ""),
    AMY_GITHUB_API_TOKEN=(str, "fakeToken"),
    AMY_STATIC_HOST=(str, ""),
    AMY_LIVE_EMAIL=(bool, False),
    AMY_SERVER_EMAIL=(str, "root@localhost"),
    AMY_DEFAULT_FROM_EMAIL=(str, "webmaster@localhost"),
    AMY_MAILGUN_API_KEY=(str, ""),
    AMY_MAILGUN_SENDER_DOMAIN=(str, ""),
    AMY_ADMIN_URL=(str, "admin/"),
    AMY_AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS=(str, ""),
    AMY_REPORTS_SALT_FRONT=(str, ""),
    AMY_REPORTS_SALT_BACK=(str, ""),
    AMY_REPORTS_LINK=(
        str,
        "https://workshop-reports.carpentries.org/?key={hash}&slug={slug}",
    ),
    AMY_SITE_BANNER=(str, "local"),  # should be "local", "testing", or "production"
    AMY_EMAIL_ATTACHMENTS_S3_BUCKET_NAME=(str, "carpentries-amy-email-attachments-staging"),
)

# OS environment variables take precedence over variables from .env
env.read_env(str(ROOT_DIR / ".env"))

CONTINUOUS_INTEGRATION = env("CI")

# GENERAL
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env("AMY_DEBUG")
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-FORMAT_MODULE_PATH
FORMAT_MODULE_PATH = "amy.formats"
# Secret key must be kept secret
DEFAULT_SECRET_KEY = "3l$35+@a%g!(^y^98oi%ei+%+yvtl3y0k^_7-fmx2oj09-ac5@"
SECRET_KEY = env.str("AMY_SECRET_KEY", default=DEFAULT_SECRET_KEY)
if not DEBUG and SECRET_KEY == DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured("You must specify non-default value for SECRET_KEY when running with Debug=FALSE.")

# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = env("AMY_SITE_ID")

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env("AMY_ALLOWED_HOSTS")
if DEBUG:
    ALLOWED_HOSTS.append("127.0.0.1")
    ALLOWED_HOSTS.append("localhost")

# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = env("AMY_CSRF_TRUSTED_ORIGINS")

# DATABASES
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("AMY_DATABASE_NAME"),
        "USER": env("AMY_DATABASE_USER"),
        "PASSWORD": env("AMY_DATABASE_PASSWORD"),
        "HOST": env("AMY_DATABASE_HOST"),
        "PORT": env("AMY_DATABASE_PORT"),
        "ATOMIC_REQUESTS": True,
    }
}

# Default primary key field type
# https://docs.djangoproject.com/en/dev/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# URLS
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# ReCaptcha
# -----------------------------------------------------------------------------
RECAPTCHA_PUBLIC_KEY = env("AMY_RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = env("AMY_RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_USE_SSL = True
NOCAPTCHA = True
if DEBUG:
    SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]

# APPS
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Handy template tags
    "django.contrib.humanize",
    # for TemplatesSetting form template renderer
    # https://docs.djangoproject.com/en/dev/ref/forms/renderers/
    "django.forms",
    "django.contrib.postgres",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap4",
    "django_select2",
    "django_countries",
    "django_filters",
    "reversion",
    "reversion_compare",
    "rest_framework",
    "knox",
    "django_recaptcha",
    "social_django",
    "debug_toolbar",
    "django_extensions",
    "anymail",
    "django_comments",  # this used to be in django.contrib
    "markdownx",
    "djangoformsetjs",
    "django_better_admin_arrayfield",
    "flags",
]
LOCAL_APPS = [
    "amy.workshops.apps.WorkshopsConfig",
    "amy.api.apps.ApiConfig",
    "amy.dashboard.apps.DashboardConfig",
    "amy.extforms.apps.ExtformsConfig",
    "amy.extrequests.apps.ExtrequestsConfig",
    "amy.fiscal.apps.FiscalConfig",
    "amy.reports.apps.ReportsConfig",
    "amy.trainings.apps.TrainingsConfig",
    "amy.extcomments.apps.ExtcommentsConfig",
    "amy.autoemails.apps.AutoemailsConfig",  # TODO: eventually remove
    "amy.consents.apps.ConsentsConfig",
    "amy.communityroles.apps.CommunityRolesConfig",
    "amy.recruitment.apps.RecruitmentConfig",
    "amy.emails.apps.EmailsConfig",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# AUTHENTICATION
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "social_core.backends.github.GithubOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ["github"]
SOCIAL_AUTH_GITHUB_KEY = env("AMY_SOCIAL_AUTH_GITHUB_KEY")
SOCIAL_AUTH_GITHUB_SECRET = env("AMY_SOCIAL_AUTH_GITHUB_SECRET")
if not DEBUG and not (SOCIAL_AUTH_GITHUB_KEY and SOCIAL_AUTH_GITHUB_SECRET):
    raise ImproperlyConfigured(
        "Logging using github account will *not* work, "
        "because you didn't set AMY_SOCIAL_AUTH_GITHUB_KEY and/or "
        "AMY_SOCIAL_AUTH_GITHUB_SECRET environment variables."
    )
# Github API token (optional). Setting this token reduces limits and quotes
# on Github API.
GITHUB_API_TOKEN = env("AMY_GITHUB_API_TOKEN")
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    # If we can't find Person associated with given github account, abort.
    "workshops.github_auth.abort_if_no_user_found",
    # The default pipeline includes 'social.pipeline.user.create_user' here,
    # but we don't want to register a new Person when somebody logs in
    # using GitHub account that is not associated with any Person.
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "workshops.Person"
SOCIAL_AUTH_USER_MODEL = "workshops.Person"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "dispatch"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "login"

# PASSWORDS
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
VALIDATION = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": f"{VALIDATION}.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("username", "personal", "middle", "family", "email")},
    },
    {
        "NAME": f"{VALIDATION}.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": f"{VALIDATION}.CommonPasswordValidator",
    },
    {
        "NAME": f"{VALIDATION}.NumericPasswordValidator",
    },
]

# CACHE
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.2/topics/cache/#database-caching
CACHES = {
    "default": env.cache_url(
        "AMY_CACHE_DEFAULT",
        cast(environ.NoValue, "dbcache://default_cache_table"),
    ),
    "select2": env.cache_url(
        "AMY_CACHE_SELECT2",
        cast(environ.NoValue, "dbcache://select2_cache_table"),
    ),
}

# MIDDLEWARE
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "workshops.middleware.version_check.VersionCheckMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "reversion.middleware.RevisionMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "workshops.middleware.github_auth.GithubAuthMiddleware",
    "consents.middleware.TermsMiddleware",
    "workshops.middleware.feature_flags.SaveSessionFeatureFlagMiddleware",
]

# STATIC
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
STATIC_HOST = env("AMY_STATIC_HOST")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = f"{STATIC_HOST}/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR / "static"),
    str(ROOT_DIR / "node_modules" / "@fortawesome" / "fontawesome-free"),
    str(ROOT_DIR / "node_modules" / "@github" / "time-elements" / "dist"),
    str(ROOT_DIR / "node_modules" / "bootstrap" / "dist" / "css"),
    str(ROOT_DIR / "node_modules" / "bootstrap" / "dist" / "js"),
    str(ROOT_DIR / "node_modules" / "bootstrap-datepicker" / "dist" / "css"),
    str(ROOT_DIR / "node_modules" / "bootstrap-datepicker" / "dist" / "js"),
    str(ROOT_DIR / "node_modules" / "bootstrap-datepicker" / "dist" / "locales"),
    str(ROOT_DIR / "node_modules" / "popper.js" / "dist" / "umd"),
    str(ROOT_DIR / "node_modules" / "datatables.net" / "js"),
    str(ROOT_DIR / "node_modules" / "datatables.net-bs4" / "css"),
    str(ROOT_DIR / "node_modules" / "datatables.net-bs4" / "js"),
    str(ROOT_DIR / "node_modules" / "select2" / "dist" / "css"),
    str(ROOT_DIR / "node_modules" / "select2" / "dist" / "js"),
    str(ROOT_DIR / "node_modules" / "@ttskch" / "select2-bootstrap4-theme" / "dist"),
    str(ROOT_DIR / "node_modules" / "jquery" / "dist"),
    str(ROOT_DIR / "node_modules" / "jquery-stickytabs"),
    str(ROOT_DIR / "node_modules" / "js-cookie" / "dist"),
    str(ROOT_DIR / "node_modules" / "urijs" / "src"),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_AUTOREFRESH = DEBUG or CONTINUOUS_INTEGRATION  # faster tests

# MEDIA
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(ROOT_DIR / "mediafiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# FORM RENDERER
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.1/ref/settings/#form-renderer
# and
# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# TEMPLATES
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [
            str(APPS_DIR / "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            "debug": DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                # AMY version
                "workshops.context_processors.version",
                "workshops.context_processors.site_banner",
                "workshops.context_processors.feature_flags_enabled",
                # Consent enums
                "consents.context_processors.terms",
                # GitHub auth
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
            # Warn viewers of invalid template strings
            "string_if_invalid": "XXX-unset-variable-XXX",
        },
    },
    # `autoemails` app backend used for reading templates from the database
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "NAME": "db_backend",
        # not-allowed to fetch from disk
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "debug": False,
            "loaders": [],
            "context_processors": [
                "django.template.context_processors.i18n",
                "django.template.context_processors.tz",
            ],
            # Warn about invalid template variables
            "string_if_invalid": "XXX-unset-variable-XXX",
        },
    },
    # `emails` app backend used for reading templates from the database
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "NAME": "email_jinja2_backend",
        # not-allowed to fetch from disk
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "undefined": jinja2.Undefined,
        },
    },
]
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# EMAIL
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
if DEBUG and not env("AMY_LIVE_EMAIL"):
    # outgoing mails will be stored in `django.core.mail.outbox`
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# sender for error emails
SERVER_EMAIL = env("AMY_SERVER_EMAIL")

# default sender for non-error messages
DEFAULT_FROM_EMAIL = env("AMY_DEFAULT_FROM_EMAIL")

# django-anymail configuration for Mailgun
ANYMAIL = {
    "MAILGUN_API_KEY": env("AMY_MAILGUN_API_KEY"),
    "MAILGUN_SENDER_DOMAIN": env("AMY_MAILGUN_SENDER_DOMAIN"),
    # This should be in format `long_random:another_long_random`, as it's used
    # for HTTP Basic Auth when Mailgun logs in to tell us about email tracking
    # event.
    # "WEBHOOK_SECRET": env("AMY_MAILGUN_WEBHOOK_SECRET", default=None),
    "SEND_DEFAULTS": {
        "tags": ["amy"],
    },
}
if not DEBUG and (not ANYMAIL["MAILGUN_API_KEY"] or not ANYMAIL["MAILGUN_SENDER_DOMAIN"]):
    raise ImproperlyConfigured("Mailgun settings are required when running with DEBUG=False.")


# NOTIFICATIONS
# -----------------------------------------------------------------------------
ADMIN_NOTIFICATION_CRITERIA_DEFAULT = "workshops@carpentries.org"

# Number of emails that can be sent at one time using
# The Email provider's (Mailgun) bulk email functionality
BULK_EMAIL_LIMIT = 1000

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = env("AMY_ADMIN_URL")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("Sysadmins ML", "sysadmin@carpentries.org"),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# messages
# -----------------------------------------------------------------------------
from django.contrib.messages import constants as message_constants  # noqa

MESSAGE_TAGS = {
    message_constants.DEBUG: "debug",
    message_constants.INFO: "info alert-info",
    message_constants.SUCCESS: "success alert-success",
    message_constants.WARNING: "warning alert-warning",
    message_constants.ERROR: "error alert-danger",
}
ONLY_FOR_ADMINS_TAG = "only-for-admins"

# django-countries
# -----------------------------------------------------------------------------
# explicitely add European Union as a country
COUNTRIES_OVERRIDE = {
    "EU": _("European Union"),
    "US": _("United States"),
    "W3": _("Online"),
}

# rest-framework
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "50/hour", "user": "2000/hour"},
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
}

# logging
# -----------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # merge with default configuration
    "formatters": {
        "verbose": {
            "format": ("[{asctime}][{levelname}][{pathname}:{funcName}:{lineno}] {message}"),
            "style": "{",
        },
        "simple": {
            "format": "[{asctime}][{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "email_backend": EMAIL_BACKEND,
            "include_html": True,
        },
    },
    "loggers": {
        # disable "Invalid HTTP_HOST" notifications
        "django.request": {
            "level": "ERROR",
        },
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
        "amy": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

# Debug Toolbar
# -----------------------------------------------------------------------------
INTERNAL_IPS = ["127.0.0.1", "::1"]
DEBUG_TOOLBAR_CONFIG = {"SHOW_COLLAPSED": True}
DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.history.HistoryPanel",
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",
    "flags.panels.FlagsPanel",
    "flags.panels.FlagChecksPanel",
]

# Django-contrib-comments
# -----------------------------------------------------------------------------
# https://django-contrib-comments.readthedocs.io/en/latest/settings.html
COMMENTS_APP = "extcomments"

# Django-Select2 settings
# -----------------------------------------------------------------------------
# https://django-select2.readthedocs.io/en/latest/django_select2.html
SELECT2_JS = ""  # don't load JS on it's own - we're loading it in `base.html`
SELECT2_CSS = ""  # the same for CSS
SELECT2_I18N = "select2/js/i18n"
SELECT2_CACHE_BACKEND = "select2"


# Test runner
# -----------------------------------------------------------------------------
# A custom test runner tailored for our needs.
# https://docs.djangoproject.com/en/4.1/topics/testing/advanced/#defining-a-test-runner
TEST_RUNNER = "workshops.tests.runner.SilenceLogsRunner"

# Autoemails application settings
# -----------------------------------------------------------------------------
# These settings describe internal `autoemails` application behavior.
# On test server: 'amy-tests@carpentries.org'
AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS = env("AMY_AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS")

# Email module
# -----------------------------------------------------------------------------
# This module is the next version of Autoemails.
EMAIL_TEMPLATE_ENGINE_BACKEND = "email_jinja2_backend"
EMAIL_MAX_FAILED_ATTEMPTS = 10  # value controls the circuit breaker for failed attempts
EMAIL_ATTACHMENTS_BUCKET_NAME = env("AMY_EMAIL_ATTACHMENTS_S3_BUCKET_NAME")

# Reports
# -----------------------------------------------------------------------------
# Settings for workshop-reports integration
REPORTS_SALT_FRONT = env("AMY_REPORTS_SALT_FRONT")
REPORTS_SALT_BACK = env("AMY_REPORTS_SALT_BACK")
if not DEBUG and not (REPORTS_SALT_FRONT and REPORTS_SALT_BACK):
    raise ImproperlyConfigured("Report salts are required. See REPORT_SALT_FRONT and REPORT_SALT_BACK" " in settings.")

REPORTS_LINK = env("AMY_REPORTS_LINK")

# Site banner style
# -----------------------------------------------------------------------------
# This should show a special banner on all sites so that users are aware of
# local/dev/test stage they are using.
SITE_BANNER_STYLE = env("AMY_SITE_BANNER")
if SITE_BANNER_STYLE not in ("local", "testing", "production"):
    raise ImproperlyConfigured("SITE_BANNER_STYLE accepts only one of 'local', 'testing', 'production'.")

PROD_ENVIRONMENT = bool(SITE_BANNER_STYLE == "production")

# Feature Flags
# -----------------------------------------------------------------------------
# These flags are used to enable/disable features in AMY.
# See https://cfpb.github.io/django-flags/ for more details.

# ------------
# The system for enabling or disabling feature flags by users themselves should only be
# used if the feature flag can be enabled by a single parameter condition set to `=true`
# Disabling the feature flag should be done by setting the URL parameter to `=false`.
# There should also be included a session condition. For example:
#
#  FLAGS = {
#      "SOME_MODULE": [
#          {"condition": "anonymous", "value": False, "required": True},
#          {"condition": "parameter", "value": "enable_some_module=true"},  # CHANGE ME
#          {"condition": "session", "value": "enable_some_module"},  # CHANGE ME
#      ],
#  }
# ------------
FLAGS = {
    # Enable instructor recruitment views.
    "INSTRUCTOR_RECRUITMENT": [
        {"condition": "boolean", "value": True},
    ],
    # ------------
    # Enable the new email module.
    "EMAIL_MODULE": [
        {"condition": "boolean", "value": True},
    ],
    # Always enabled.
    "ENFORCE_MEMBER_CODES": [
        {"condition": "boolean", "value": True},
    ],
}

# Instructor Certificates
# -----------------------------------------------------------------------------
CERTIFICATE_SIGNATURE = "SherAaron Hurt (Director of Workshops and Instruction)"
