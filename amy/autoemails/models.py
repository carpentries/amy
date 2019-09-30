from collections import namedtuple
from typing import Optional, List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Template, Context

from workshops.models import ActiveMixin, CreatedUpdatedMixin


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
        max_length=255, unique=True,
        verbose_name="Template slug",
        help_text="It must be a unique name for this template.",
    )
    DJANGO_TEMPLATE_DOCS = ('https://docs.djangoproject.com/en/dev/topics/'
                            'templates/#the-django-template-language')
    subject = models.CharField(
        max_length=255, blank=True, null=False, default="",
        help_text="Enter text for email subject. If you need to use loops, "
                  "conditions, etc., use "
                  "<a href='{}'>Django templates language</a>."
                  .format(DJANGO_TEMPLATE_DOCS),
    )
    to_header = models.CharField(
        max_length=255, blank=True, null=False, default="",
        verbose_name="To",
        help_text="Default value for 'To' field. It may be overridden by the"
                  " email trigger. Use single address.",
    )
    from_header = models.CharField(
        max_length=255, blank=True, null=False,
        default=settings.DEFAULT_FROM_EMAIL,
        verbose_name="From",
        help_text="Value for 'From' field. It defaults to application settings"
                  " (currently '{}') and may be overridden by the email"
                  " trigger. Use single address."
                  .format(settings.DEFAULT_FROM_EMAIL),
    )
    cc_header = models.CharField(
        max_length=255, blank=True, null=False, default="",
        verbose_name="CC",
        help_text="Default value for 'CC' field. It may be overridden by the"
                  " email trigger. Use single address.",
    )
    bcc_header = models.CharField(
        max_length=255, blank=True, null=False, default="",
        verbose_name="BCC",
        help_text="Default value for 'BCC' field. It may be overridden by the"
                  " email trigger. Use single address.",
    )
    reply_to_header = models.CharField(
        max_length=255, blank=True, null=False, default="",
        verbose_name="Reply-To",
        help_text="Default value for 'Reply-To' field. It may be overridden by"
                  " the email trigger. Use single address.",
    )
    html_template = models.TextField(
        blank=True, null=False, default="",
        verbose_name="HTML body",
        help_text="Enter HTML for email body. If you need to use loops, "
                  "conditions, etc., use "
                  "<a href='{}'>Django templates language</a>."
                  .format(DJANGO_TEMPLATE_DOCS),
    )
    text_template = models.TextField(
        blank=True, null=False, default="",
        verbose_name="Plain text body",
        help_text="Enter plain text for email body. If you need to use loops, "
                  "conditions, etc., use "
                  "<a href='{}'>Django templates language</a>."
                  .format(DJANGO_TEMPLATE_DOCS),
    )
    EmailBody = namedtuple('EmailBody', ['text', 'html'])

    @staticmethod
    def get_template(content: str) -> Template:
        """Translate text into Django Template object."""
        return Template(content)

    @staticmethod
    def render_template(tpl: str, context: dict) -> str:
        """Render template with given context."""
        # turn context dictionary into a Context object
        ctx = Context(context)
        return EmailTemplate.get_template(tpl).render(ctx)

    def get_subject(self,
                    subject: str = "",
                    context: Optional[dict] = None) -> str:
        return subject or self.render_template(self.subject, context)

    def get_sender(self,
                   sender: str = "",
                   context: Optional[dict] = None) -> str:
        return sender or self.render_template(self.from_header, context)

    def get_recipients(self,
                       recipients: Optional[List[str]] = None,
                       context: Optional[dict] = None) -> list:
        return recipients or [self.render_template(self.to_header, context)]

    def get_cc_recipients(self,
                          cc_recipients: Optional[List[str]] = None,
                          context: Optional[dict] = None) -> list:
        return cc_recipients or [self.render_template(self.cc_header, context)]

    def get_bcc_recipients(self,
                           bcc_recipients: Optional[List[str]] = None,
                           context: Optional[dict] = None) -> list:
        return bcc_recipients or [self.render_template(self.bcc_header,
                                                       context)]

    def get_reply_to(self,
                     reply_to: str = "",
                     context: Optional[dict]=None) -> str:
        return reply_to or [self.render_template(self.reply_to_header, context)]

    def get_body(self,
                 text: str = "",
                 html: str = "",
                 context: Optional[dict] = None) -> EmailBody:
        """Get both text and HTML email bodies."""
        if text:
            text_body = self.render_template(text, context)
        else:
            text_body = self.render_template(self.text_template, context)

        if html:
            html_body = self.render_template(html, context)
        else:
            html_body = self.render_template(self.html_template, context)

        body = self.EmailBody(text=text_body, html=html_body)
        return body

    def build_email(self,
                    subject: str = "",
                    sender: str = "",
                    recipients: Optional[List[str]] = None,
                    cc_recipients: Optional[List[str]] = None,
                    bcc_recipients: Optional[List[str]] = None,
                    reply_to: str = "",
                    text: str = "",
                    html: str = "",
                    context: Optional[dict] = None) -> EmailMultiAlternatives:
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

        return msg

    def __str__(self):
        return f"Email Template '{self.slug}' ({self.subject})"
