from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime
from markdownx.fields import MarkdownxFormField
from markdownx.widgets import AdminMarkdownxWidget

from workshops.forms import BootstrapHelper

from .models import EmailTemplate


class RescheduleForm(forms.Form):
    scheduled_execution = forms.SplitDateTimeField(
        required=True,
        initial=None,
        label="New execution time",
        widget=AdminSplitDateTime(),
    )


class TemplateForm(forms.Form):
    template = MarkdownxFormField(
        label="Markdown body",
        widget=AdminMarkdownxWidget,
        required=True,
    )


class GenericEmailScheduleForm(forms.ModelForm):
    body_template = MarkdownxFormField(
        label="Markdown body",
        widget=AdminMarkdownxWidget,
        required=True,
    )
    helper = BootstrapHelper(
        wider_labels=True,
        add_cancel_button=False,
        add_submit_button=False,
        form_tag=False,
    )

    class Meta:
        model = EmailTemplate
        fields = [
            "slug",
            "subject",
            "to_header",
            "from_header",
            "cc_header",
            "bcc_header",
            "reply_to_header",
            "body_template",
        ]
