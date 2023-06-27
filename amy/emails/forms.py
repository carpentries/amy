from django import forms

from emails.models import ScheduledEmail


class ScheduledEmailEditForm(forms.ModelForm):
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
