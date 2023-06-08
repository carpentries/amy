import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.template import TemplateSyntaxError, engines
from django.template.backends.base import BaseEngine

from workshops.mixins import ActiveMixin, CreatedMixin, CreatedUpdatedMixin

DJANGO_TEMPLATE_DOCS = (
    "https://docs.djangoproject.com/en/dev/topics/"
    "templates/#the-django-template-language"
)

MAX_LENGTH = 255


class EmailTemplate(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """Markdown template used for generating HTML email contents."""

    # ID needed separately as we're using UUIDs for PKs in this module
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=MAX_LENGTH, blank=False, null=False, unique=True)

    # This will tie the template with specific signal (trigger). Once the signal is
    # emitted, the connected template will be queued based on the signal details.
    # TODO: this can become an enum later on, to limit the choices for the user.
    signal = models.SlugField(
        max_length=MAX_LENGTH,
        blank=False,
        null=False,
        unique=True,
        help_text="Trigger that will queue this email template",
    )

    subject = models.CharField(
        max_length=MAX_LENGTH,
        blank=False,
        null=False,
        verbose_name="Email subject",
        help_text="Enter text for email subject. If you need to use loops, "
        "conditions, etc., use "
        f"<a href='{DJANGO_TEMPLATE_DOCS}'>Django templates language</a>.",
    )
    from_header = models.EmailField(blank=False)
    reply_to_header = models.EmailField(
        blank=True,
        default="",
        help_text="If empty, the default reply-to address will be 'from_header'.",
    )
    cc_header = ArrayField(models.EmailField(blank=False))
    bcc_header = ArrayField(models.EmailField(max_length=MAX_LENGTH, blank=False))
    body = models.TextField(
        blank=False,
        null=False,
        verbose_name="Email body (markdown)",
        help_text="Enter Markdown for email body. If you need to use loops, "
        "conditions, etc., use "
        f"<a href='{DJANGO_TEMPLATE_DOCS}'>Django templates language</a>.",
    )

    @staticmethod
    def get_engine(name: str | None = None) -> BaseEngine:
        return engines[name or settings.EMAIL_TEMPLATE_ENGINE_BACKEND]

    @staticmethod
    def validate_template(
        engine: BaseEngine, template: str, context: dict | None = None
    ) -> bool:
        try:
            tpl = engine.from_string(template)
            tpl.render(context or dict())
        except TemplateSyntaxError as exp:
            raise ValidationError(f"Invalid syntax: {exp}") from exp
        return True

    def clean(self) -> None:
        errors = dict()
        fields = ("subject", "body")
        for field in fields:
            try:
                self.validate_template(self.get_engine(), getattr(self, field))
            except ValidationError as exp:
                errors[field] = exp

        if errors:
            raise ValidationError(errors)


class ScheduledEmailStatus(models.TextChoices):
    SCHEDULED = "scheduled"
    LOCKED = "locked"
    RUNNING = "running"
    SUCCEEDED = "succeded"
    FAILED = "failed"


class ScheduledEmail(CreatedUpdatedMixin, models.Model):
    """Email to be sent at specific timestamp."""

    # ID needed separately as we're using UUIDs for PKs in this module
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    state = models.CharField(
        max_length=30,
        blank=False,
        null=False,
        choices=ScheduledEmailStatus.choices,
        default=ScheduledEmailStatus.SCHEDULED,
    )

    scheduled_at = models.DateTimeField(
        blank=False,
        null=False,
        editable=False,
        verbose_name="Timestamp of scheduled run",
    )

    to_header = ArrayField(models.EmailField(blank=False), verbose_name="To (header)")
    from_header = models.EmailField(blank=False, verbose_name="From (header)")
    reply_to_header = models.EmailField(
        blank=True, default="", verbose_name="Reply-To (header)"
    )
    cc_header = ArrayField(models.EmailField(blank=False), verbose_name="CC (header)")
    bcc_header = ArrayField(models.EmailField(blank=False), verbose_name="BCC (header)")
    subject = models.CharField(
        max_length=MAX_LENGTH,
        blank=False,
        null=False,
        verbose_name="Subject (rendered from template)",
    )
    body = models.TextField(
        blank=False,
        null=False,
        verbose_name="Email body (rendered from template)",
    )

    template = models.ForeignKey(
        EmailTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Linked template",
    )

    class Meta:
        indexes = [models.Index(fields=["state", "scheduled_at"])]


class ScheduledEmailLog(CreatedMixin, models.Model):
    """Log entry for scheduled email. Contains details of a particular situation, for
    example attempting to send email and its outcome, e.g. failure."""

    # ID needed separately as we're using UUIDs for PKs in this module
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    details = models.CharField(
        max_length=MAX_LENGTH,
        blank=False,
        null=False,
        editable=False,
    )
    state_before = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        choices=ScheduledEmailStatus.choices,
        editable=False,
    )
    state_after = models.CharField(
        max_length=30,
        blank=False,
        null=False,
        choices=ScheduledEmailStatus.choices,
        editable=False,
    )

    scheduled_email = models.ForeignKey(ScheduledEmail, on_delete=models.CASCADE)
