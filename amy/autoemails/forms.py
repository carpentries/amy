from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime


class RescheduleForm(forms.Form):
    scheduled_execution = forms.DateTimeField(
        required=True, initial=None,
        label="New execution time",
        widget=AdminSplitDateTime(),
    )
