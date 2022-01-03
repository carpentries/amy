from collections import namedtuple
from typing import List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Template, TemplateSyntaxError, engines
from django.urls import reverse
import markdown

from workshops.mixins import (
    ActiveMixin,
    CreatedUpdatedArchivedMixin,
    CreatedUpdatedMixin,
)
from workshops.models import Person

EmailBody = namedtuple("EmailBody", ["text", "html"])


class EmailTemplate(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """
    Single template for any action desired. This class/instance stores:
    * email headers (like "from", "to", "cc", "bcc", "subject")
    * plain text body
    * HTML body

    A representation of this class' instance is cached in Redis (or other task
    queue backend), and then sent out by the Scheduler (see
    https://github.com/rq/rq-scheduler for details).
    """

    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Template slug",
        help_text="It must be a unique name for this template.",
    )
    DJANGO_TEMPLATE_DOCS = (
        "https://docs.djangoproject.com/en/dev/topics/"
        "templates/#the-django-template-language"
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        default="",
        help_text="Enter text for email subject. If you need to use loops, "
        "conditions, etc., use "
        "<a href='{}'>Django templates language</a>.".format(DJANGO_TEMPLATE_DOCS),
    )
    to_header = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        default="",
        verbose_name="To",
        help_text="Default value for 'To' field. It may be overridden by the"
        " email trigger. Use single address.",
    )
    from_header = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        default=settings.DEFAULT_FROM_EMAIL,
        verbose_name="From",
        help_text="Value for 'From' field. It defaults to application settings"
        " (currently '{}') and may be overridden by the email"
        " trigger. Use single address.".format(settings.DEFAULT_FROM_EMAIL),
    )
    cc_header = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        default="",
        verbose_name="CC",
        help_text="Default value for 'CC' field. It may be overridden by the"
        " email trigger. Use single address.",
    )
    bcc_header = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        default="",
        verbose_name="BCC",
        help_text="Default value for 'BCC' field. It may be overridden by the"
        " email trigger. Use single address.",
    )
    reply_to_header = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        default="",
        verbose_name="Reply-To",
        help_text="Default value for 'Reply-To' field. It may be overridden by"
        " the email trigger. Use single address.",
    )
    body_template = models.TextField(
        blank=True,
        null=False,
        default="",
        verbose_name="Markdown body",
        help_text="Enter Markdown for email body. If you need to use loops, "
        "conditions, etc., use "
        "<a href='{}'>Django templates language</a>.".format(DJANGO_TEMPLATE_DOCS),
    )

    @staticmethod
    def get_template(content: str, default_engine: str = "db_backend") -> Template:
        """Translate text into Django Template object.

        default_engine: name of the template backend used for rendering
        For more see:
        https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-TEMPLATES-NAME
        """
        return engines[default_engine].from_string(content)

    @staticmethod
    def render_template(
        tpl: str, context: dict, default_engine: str = "db_backend"
    ) -> str:
        """Render template with given context."""
        return EmailTemplate.get_template(tpl, default_engine=default_engine).render(
            context
        )

    def get_subject(self, subject: str = "", context: Optional[dict] = None) -> str:
        context = context or {}
        return subject or self.render_template(self.subject, context)

    def get_sender(self, sender: str = "", context: Optional[dict] = None) -> str:
        context = context or {}
        return sender or self.render_template(self.from_header, context)

    def get_recipients(
        self, recipients: Optional[List[str]] = None, context: Optional[dict] = None
    ) -> list:
        context = context or {}
        return recipients or list(
            # remove empty entries from the list
            filter(bool, [self.render_template(self.to_header, context)])
        )

    def get_cc_recipients(
        self, cc_recipients: Optional[List[str]] = None, context: Optional[dict] = None
    ) -> list:
        context = context or {}
        return cc_recipients or list(
            # remove empty entries from the list
            filter(bool, [self.render_template(self.cc_header, context)])
        )

    def get_bcc_recipients(
        self, bcc_recipients: Optional[List[str]] = None, context: Optional[dict] = None
    ) -> list:
        context = context or {}
        return bcc_recipients or list(
            # remove empty entries from the list
            filter(bool, [self.render_template(self.bcc_header, context)])
        )

    def get_reply_to(
        self, reply_to: Optional[List[str]] = None, context: Optional[dict] = None
    ) -> List[str]:
        context = context or {}
        return reply_to or [self.render_template(self.reply_to_header, context)] or [""]

    def get_body(
        self, text: str = "", html: str = "", context: Optional[dict] = None
    ) -> EmailBody:
        """Get both text and HTML email bodies.

        If not provided through method parameters, the text and HTML versions
        are generated using Markdown->HTML converter.

        Text: is just pure Markdown version.
        HTML: is converted from Markdown."""
        context = context or {}
        # when either text or HTML parameters aren't provided
        if not text or not html:
            base_template = self.render_template(self.body_template, context)

        if text:
            text_body = self.render_template(text, context)
        else:
            text_body = base_template

        if html:
            html_body = self.render_template(html, context)
        else:
            html_body = markdown.markdown(base_template)

        body = EmailBody(text=text_body, html=html_body)
        return body

    def build_email(
        self,
        subject: str = "",
        sender: str = "",
        recipients: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
        text: str = "",
        html: str = "",
        context: Optional[dict] = None,
        merge_data: Optional[dict] = None,
    ) -> EmailMultiAlternatives:
        """Build a Django email representation (see
        https://docs.djangoproject.com/en/2.2/topics/email/#sending-alternative-content-types
        for details).

        A resulting EmailMultiAlternatives instance contains all headers/fields
        used in database record (like subject, plain text contents, HTML
        alternatives content), allows for adding attachments, and finally
        provides `send()` method."""

        body = self.get_body(text, html, context)

        msg = EmailMultiAlternatives(
            subject=self.get_subject(subject, context),
            from_email=self.get_sender(sender, context),
            to=self.get_recipients(recipients, context),
            cc=self.get_cc_recipients(cc_recipients, context),
            bcc=self.get_bcc_recipients(bcc_recipients, context),
            reply_to=self.get_reply_to(reply_to, context),
            body=body.text,
        )
        msg.attach_alternative(body.html, "text/html")

        # https://anymail.readthedocs.io/en/stable/sending/templates/#batch-sending-with-merge-data
        # https://anymail.readthedocs.io/en/stable/sending/templates/#anymail.message.AnymailMessage.merge_data
        # When set the recipients in the "to" field each get an individual message
        msg.merge_data = merge_data
        if merge_data is not None:
            assert len(msg.to) <= settings.BULK_EMAIL_LIMIT

        return msg

    def __str__(self):
        return f"Email Template '{self.slug}' ({self.subject:.50}...)"

    def get_absolute_url(self):
        return reverse("admin:autoemails_emailtemplate_change", args=[self.pk])

    def clean(self):
        errors = dict()

        fields = [
            "subject",
            "to_header",
            "from_header",
            "cc_header",
            "bcc_header",
            "reply_to_header",
            "body_template",
        ]

        for field in fields:
            # check field for template syntax errors
            try:
                tpl = EmailTemplate.get_template(getattr(self, field))
                out = tpl.render(dict())
            except TemplateSyntaxError:
                errors[field] = "Invalid Django Template syntax."
            else:
                # check for missing open/close tags
                if "{{" in out or "}}" in out or "{%" in out or "%}" in out:
                    errors[field] = (
                        'Missing opening or closing tags: "{%", "%}",' ' "{{", or "}}".'
                    )

        if errors:
            raise ValidationError(errors)


class Trigger(ActiveMixin, CreatedUpdatedMixin, models.Model):
    """
    A representation of action and related email template. User can select what
    action triggers the email template. Time of the email being sent is
    programmed-in, and it's not possible to change it in the trigger instance.
    """

    ACTION_CHOICES = (
        ("new-instructor", "Instructor is added to the workshop"),
        ("new-supporting-instructor", "Supporting Instructor is added to the workshop"),
        (
            "week-after-workshop-completion",
            "7 days past the end date of an active workshop",
        ),
        (
            "self-organised-request-form",
            "A new event is created from Self-Organised Request Form",
        ),
        (
            "instructors-host-introduction",
            "Introduction of instrutors and host (centr. org. workshop)",
        ),
        ("ask-for-website", "Website URL is missing"),
        ("recruit-helpers", "Recruit helpers"),
        ("workshop-request-response1", "Response to Workshop Request 1"),
        ("workshop-request-response2", "Response to Workshop Request 2"),
        ("workshop-request-response3", "Response to Workshop Request 3"),
        (
            "consent-required",
            "There is a new or updated term added that the users should consent to",
        ),
        (
            "profile-update",
            "Reminder to for the user to update the information in their profile.",
        ),
        (
            "profile-archival-warning-inactivity",
            "Warning for the user to login before their profile will be archived"
            " due to inactivity.",
        ),
        (
            "profile-archival-warning-consents",
            "Warning for the user to login before their profile will be archived"
            " due to new consents they have not yet agreed to.",
        ),
    )
    action = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        choices=ACTION_CHOICES,
        verbose_name="Action",
        help_text="",
    )
    template = models.OneToOneField(
        EmailTemplate,
        on_delete=models.PROTECT,
        limit_choices_to={"active": True},
        verbose_name="Template",
        help_text="Select desired template. Only active templates are "
        "available. Each template can only be used once.",
    )

    def __str__(self):
        return '<Trigger for "{}" (template "{}")>'.format(
            self.action, self.template.slug
        )

    def get_absolute_url(self):
        return reverse("admin:autoemails_trigger_change", args=[self.pk])


class RQJob(CreatedUpdatedMixin, models.Model):
    """Simple class for storing Redis Queue job's ID."""

    job_id = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        verbose_name="RQ Job ID",
    )

    trigger = models.ForeignKey(
        Trigger,
        blank=False,
        null=False,
        on_delete=models.PROTECT,
        verbose_name="Trigger",
    )

    scheduled_execution = models.DateTimeField(
        blank=True,
        null=True,
        default=None,
        verbose_name="Scheduled execution time",
        help_text="Set automatically when scheduling an email.",
    )

    status = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        default="",
        verbose_name="Job status",
        help_text="This field is cached from Redis.",
    )

    mail_status = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        default="",
        verbose_name="Mail status",
        help_text="This field is updated from Mailgun.",
    )

    event_slug = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        default="",
        verbose_name="Event slug",
        help_text="Related event's slug.",
    )

    recipients = models.TextField(
        blank=True,
        null=False,
        default="",
        verbose_name="Mail recipients",
    )
    interval = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Interval in seconds",
    )
    result_ttl = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Result TTL",
    )
    action_name = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        default="",
        verbose_name="Action Class",
        help_text="Action class that will be executed.",
    )

    def __str__(self):
        return "<RQJob [{}]>".format(self.job_id)

    def get_absolute_url(self):
        return reverse("admin:autoemails_rqjob_preview", args=[self.pk])

    class Meta:
        verbose_name = "RQ Job"
        verbose_name_plural = "RQ Jobs"

        # add index on job_id for faster retrieval
        indexes = [models.Index(fields=["job_id"])]


class EmailReminder(CreatedUpdatedArchivedMixin, models.Model):
    remind_again_date = models.DateTimeField()
    person = models.ForeignKey(
        Person,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
    )
    trigger = models.ForeignKey(
        Trigger,
        blank=False,
        null=False,
        on_delete=models.PROTECT,
    )
    number_times_sent = models.IntegerField(blank=False, null=False, default=0)
