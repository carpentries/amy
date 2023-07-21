from django import forms
from markdownx.fields import MarkdownxFormField

from emails.models import EmailTemplate, ScheduledEmail
from workshops.forms import BootstrapHelper


class EmailTemplateCreateForm(forms.ModelForm):
    body = MarkdownxFormField(
        label=EmailTemplate._meta.get_field("body").verbose_name,
        help_text=EmailTemplate._meta.get_field("body").help_text,
        widget=forms.Textarea,
    )

    class Meta:
        model = EmailTemplate
        fields = [
            "name",
            "signal",
            "from_header",
            "reply_to_header",
            "cc_header",
            "bcc_header",
            "subject",
            "body",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        array_email_field_help_text = "Separate email addresses with a comma"
        self.fields["cc_header"].help_text = array_email_field_help_text
        self.fields["bcc_header"].help_text = array_email_field_help_text


EmailTemplateUpdateForm = EmailTemplateCreateForm


class ScheduledEmailUpdateForm(forms.ModelForm):
    body = MarkdownxFormField(
        label=ScheduledEmail._meta.get_field("body").verbose_name,
        help_text=ScheduledEmail._meta.get_field("body").help_text,
        widget=forms.Textarea,
    )

    class Meta:
        model = ScheduledEmail
        fields = [
            "to_header",
            "from_header",
            "reply_to_header",
            "cc_header",
            "bcc_header",
            "subject",
            "body",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        array_email_field_help_text = "Separate email addresses with a comma"
        self.fields["to_header"].help_text = array_email_field_help_text
        self.fields["cc_header"].help_text = array_email_field_help_text
        self.fields["bcc_header"].help_text = array_email_field_help_text


class ScheduledEmailRescheduleForm(forms.Form):
    scheduled_at = forms.SplitDateTimeField(
        label=ScheduledEmail._meta.get_field("scheduled_at").verbose_name,
        help_text="Time in UTC",
    )

    helper = BootstrapHelper(submit_label="Update")


class ScheduledEmailCancelForm(forms.Form):
    confirm = forms.CharField(required=False)
    decline = forms.CharField(required=False)
