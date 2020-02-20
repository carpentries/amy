from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime


class RescheduleForm(forms.Form):
    scheduled_execution = forms.SplitDateTimeField(
        required=True, initial=None,
        label="New execution time",
        widget=AdminSplitDateTime(),
    )
