from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime
from markdownx.fields import MarkdownxFormField
from markdownx.widgets import AdminMarkdownxWidget


class RescheduleForm(forms.Form):
    scheduled_execution = forms.SplitDateTimeField(
        required=True, initial=None,
        label="New execution time",
        widget=AdminSplitDateTime(),
    )


class TemplateForm(forms.Form):
    template = MarkdownxFormField(
        label="Markdown body",
        widget=AdminMarkdownxWidget,
        required=True,
    )
