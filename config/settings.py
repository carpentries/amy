"""
Django settings for AMY project.
"""

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
import environ

ROOT_DIR = environ.Path(__file__) - 2  # (amy/config/settings.py - 2 = amy/)
BASE_DIR = ROOT_DIR()
APPS_DIR = ROOT_DIR.path("amy")

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("AMY_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path(".env")))

CONTINUOUS_INTEGRATION = env.bool("CI", default=False)

# GENERAL
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("AMY_DEBUG", True)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# Secret key must be kept secret
DEFAULT_SECRET_KEY = "3l$35+@a%g!(^y^98oi%ei+%+yvtl3y0k^_7-fmx2oj09-ac5@"
SECRET_KEY = env.str("AMY_SECRET_KEY", default=DEFAULT_SECRET_KEY)
if not DEBUG and SECRET_KEY == DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured(
        "You must specify non-default value for "
        "SECRET_KEY when running with Debug=FALSE."
    )

# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = env.int("AMY_SITE_ID", default=2)
ALLOWED_HOSTS = env.list("AMY_ALLOWED_HOSTS", default=["amy.carpentries.org"])
if DEBUG:
    ALLOWED_HOSTS.append("127.0.0.1")

# DATABASES
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://amy:amypostgresql@localhost/amy"
    ),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
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
RECAPTCHA_PUBLIC_KEY = env.str(
    "AMY_RECAPTCHA_PUBLIC_KEY",
    default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
)
RECAPTCHA_PRIVATE_KEY = env.str(
    "AMY_RECAPTCHA_PRIVATE_KEY",
    default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
)
RECAPTCHA_USE_SSL = True
NOCAPTCHA = True
if DEBUG:
    SILENCED_SYSTEM_CHECKS = ["captcha.recaptcha_test_key_error"]

# APPS
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
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
    "django_select2",
    "django_countries",
    "django_filters",
    "reversion",
    "reversion_compare",
    "rest_framework",
    "captcha",
    "social_django",
    "debug_toolbar",
    "django_extensions",
    "anymail",
    "django_comments",  # this used to be in django.contrib
    "markdownx",
    "django_rq",
    "djangoformsetjs",
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
    "amy.autoemails.apps.AutoemailsConfig",
    "amy.consents.apps.ConsentsConfig",
    "amy.communityroles.apps.CommunityRolesConfig",
    "amy.recruitment.apps.RecruitmentConfig",
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
SOCIAL_AUTH_GITHUB_KEY = env.str("AMY_SOCIAL_AUTH_GITHUB_KEY", default="")
SOCIAL_AUTH_GITHUB_SECRET = env.str("AMY_SOCIAL_AUTH_GITHUB_SECRET", default="")
if not DEBUG and not (SOCIAL_AUTH_GITHUB_KEY and SOCIAL_AUTH_GITHUB_SECRET):
    raise ImproperlyConfigured(
        "Logging using github account will *not* work, "
        "because you didn't set AMY_SOCIAL_AUTH_GITHUB_KEY and/or "
        "AMY_SOCIAL_AUTH_GITHUB_SECRET environment variables."
    )
# Github API token (optional). Setting this token reduces limits and quotes
# on Github API.
GITHUB_API_TOKEN = env("AMY_GITHUB_API_TOKEN", default=None)
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
        "OPTIONS": {
            "user_attributes": ("username", "personal", "middle", "family", "email")
        },
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
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("AMY_REDIS_URL", "redis://localhost:6379/") + "0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "select2": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("AMY_REDIS_URL", "redis://localhost:6379/") + "1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

# MIDDLEWARE
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
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
    "workshops.github_auth.GithubAuthMiddleware",
    "consents.middleware.TermsMiddleware",
]

# STATIC
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR("staticfiles"))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR.path("static")),
    str(ROOT_DIR.path("node_modules/@fortawesome/fontawesome-free/")),
    str(ROOT_DIR.path("node_modules/@github/time-elements/dist")),
    str(ROOT_DIR.path("node_modules/bootstrap/dist/css")),
    str(ROOT_DIR.path("node_modules/bootstrap/dist/js")),
    str(ROOT_DIR.path("node_modules/bootstrap-datepicker/dist/css")),
    str(ROOT_DIR.path("node_modules/bootstrap-datepicker/dist/js")),
    str(ROOT_DIR.path("node_modules/bootstrap-datepicker/dist/locales")),
    str(ROOT_DIR.path("node_modules/popper.js/dist/umd")),
    str(ROOT_DIR.path("node_modules/datatables.net/js")),
    str(ROOT_DIR.path("node_modules/datatables.net-bs4/css")),
    str(ROOT_DIR.path("node_modules/datatables.net-bs4/js")),
    str(ROOT_DIR.path("node_modules/select2/dist/css")),
    str(ROOT_DIR.path("node_modules/select2/dist/js")),
    str(ROOT_DIR.path("node_modules/@ttskch/select2-bootstrap4-theme/dist")),
    str(ROOT_DIR.path("node_modules/jquery/dist")),
    str(ROOT_DIR.path("node_modules/jquery-stickytabs")),
    str(ROOT_DIR.path("node_modules/js-cookie/dist")),
    str(ROOT_DIR.path("node_modules/urijs/src")),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# MEDIA
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(ROOT_DIR("mediafiles"))
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
            str(APPS_DIR.path("templates")),
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
                # GitHub auth
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
            # Warn viewers of invalid template strings
            "string_if_invalid": "XXX-unset-variable-XXX",
        },
    },
    # backend used for reading templates from the database
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
]
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap4"

# FIXTURES
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# EMAIL
# -----------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
if DEBUG and not env.bool("AMY_LIVE_EMAIL", default=False):
    # outgoing mails will be stored in `django.core.mail.outbox`
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# sender for error emails
SERVER_EMAIL = env("AMY_SERVER_EMAIL", default="root@localhost")

# default sender for non-error messages
DEFAULT_FROM_EMAIL = env("AMY_DEFAULT_FROM_EMAIL", default="webmaster@localhost")

# django-anymail configuration for Mailgun
ANYMAIL = {
    "MAILGUN_API_KEY": env("AMY_MAILGUN_API_KEY", default=None),
    "MAILGUN_SENDER_DOMAIN": env("AMY_MAILGUN_SENDER_DOMAIN", default=None),
    # This should be in format `long_random:another_long_random`, as it's used
    # for HTTP Basic Auth when Mailgun logs in to tell us about email tracking
    # event.
    # "WEBHOOK_SECRET": env("AMY_MAILGUN_WEBHOOK_SECRET", default=None),
    "SEND_DEFAULTS": {
        "tags": ["amy"],
    },
}
if not DEBUG and (
    not ANYMAIL["MAILGUN_API_KEY"] or not ANYMAIL["MAILGUN_SENDER_DOMAIN"]
):
    raise ImproperlyConfigured(
        "Mailgun settings are required when running " "with DEBUG=False."
    )


# NOTIFICATIONS
# -----------------------------------------------------------------------------
ADMIN_NOTIFICATION_CRITERIA_DEFAULT = "workshops@carpentries.org"

# Number of emails that can be sent at one time using
# The Email provider's (Mailgun) bulk email functionality
BULK_EMAIL_LIMIT = 1000

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = env("AMY_ADMIN_URL", default="admin/")
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
            "format": "{asctime}::{levelname}::{message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}::{message}",
            "style": "{",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "email_backend": EMAIL_BACKEND,
            "include_html": True,
        },
        "log_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": env.path(
                "AMY_SERVER_LOGFILE", default=ROOT_DIR("logs", "amy.log")
            ),
        },
        "debug_log_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": env.path(
                "AMY_DEBUG_LOGFILE", default=ROOT_DIR("logs", "amy_debug.log")
            ),
        },
        "worker_log_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": env.path(
                "AMY_WORKER_LOGFILE", default=ROOT_DIR("logs", "worker_debug.log")
            ),
        },
    },
    "loggers": {
        # disable "Invalid HTTP_HOST" notifications
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
        "amy": {
            "handlers": ["null"],
            "level": "WARNING",
        },
        "amy.signals": {
            "handlers": ["debug_log_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "amy.server_logs": {
            "handlers": ["log_file"],
            "level": "ERROR",
            "propagate": True,
        },
        "rq.worker": {
            "handlers": ["worker_log_file"],
            "level": "DEBUG",
        },
    },
}

# Debug Toolbar
# -----------------------------------------------------------------------------
DEBUG_TOOLBAR_PATCH_SETTINGS = False
INTERNAL_IPS = ["127.0.0.1", "::1"]

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

# Django-RQ (Redis Queueing) settings
# -----------------------------------------------------------------------------
# https://github.com/rq/django-rq
RQ_QUEUES = {
    "default": {
        "URL": env.str("AMY_REDIS_URL", "redis://localhost:6379/") + "2",
        "DEFAULT_TIMEOUT": 360,
    },
    "testing": {
        "URL": env.str("AMY_REDIS_URL", "redis://localhost:6379/") + "15",
        "DEFAULT_TIMEOUT": 360,
    },
}
# Add link to admin
RQ_SHOW_ADMIN_LINK = False
# If you need custom exception handlers
# RQ_EXCEPTION_HANDLERS = ['path.to.my.handler']

RQ = {
    "JOB_CLASS": "autoemails.job.Job",
    "DEFAULT_RESULT_TTL": 31536000,  # 1 year in seconds for keeping job results
}


# Autoemails application settings
# -----------------------------------------------------------------------------
# These settings describe internal `autoemails` application behavior.
AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS = env.str(
    "AMY_AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS",
    default=None,  # On test server: 'amy-tests@carpentries.org'
)

# Reports
# -----------------------------------------------------------------------------
# Settings for workshop-reports integration
REPORTS_SALT_FRONT = env.str("AMY_REPORTS_SALT_FRONT", default="")
REPORTS_SALT_BACK = env.str("AMY_REPORTS_SALT_BACK", default="")
if not DEBUG and not (REPORTS_SALT_FRONT and REPORTS_SALT_BACK):
    raise ImproperlyConfigured(
        "Report salts are required. See REPORT_SALT_FRONT and REPORT_SALT_BACK"
        " in settings."
    )

REPORTS_LINK = env.str(
    "AMY_REPORTS_LINK",
    default="https://workshop-reports.carpentries.org/?key={hash}&slug={slug}",
)

# Instructor Recruitment Process
# -----------------------------------------------------------------------------
# Settings for Instructor Recruitment project
INSTRUCTOR_RECRUITMENT_ENABLED = env.bool(
    "AMY_INSTRUCTOR_RECRUITMENT_ENABLED", default=False
)
