from captcha.fields import ReCaptchaField
from django import forms

from extrequests.deprecated_forms import (
    SWCEventRequestNoCaptchaForm,
    DCEventRequestNoCaptchaForm,
    DCSelfOrganizedEventRequestFormNoCaptcha,
    EventSubmitFormNoCaptcha,
    ProfileUpdateRequestFormNoCaptcha,
)
from workshops.models import (
    InvoiceRequest,
)
from workshops.forms import (
    BootstrapHelper,
    PrivacyConsentMixin,
)


class SWCEventRequestForm(SWCEventRequestNoCaptchaForm):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False,
                             duplicate_buttons_on_top=False)

    class Meta(SWCEventRequestNoCaptchaForm.Meta):
        exclude = ('state', 'event') \
                  + SWCEventRequestNoCaptchaForm.Meta.exclude


class DCEventRequestForm(DCEventRequestNoCaptchaForm):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False,
                             duplicate_buttons_on_top=False)

    class Meta(DCEventRequestNoCaptchaForm.Meta):
        exclude = ('state', 'event') \
                  + DCEventRequestNoCaptchaForm.Meta.exclude


class DCSelfOrganizedEventRequestForm(
        DCSelfOrganizedEventRequestFormNoCaptcha, PrivacyConsentMixin):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)

    class Meta(DCSelfOrganizedEventRequestFormNoCaptcha.Meta):
        exclude = ('state', 'event') \
                  + DCSelfOrganizedEventRequestFormNoCaptcha.Meta.exclude


class EventSubmitForm(EventSubmitFormNoCaptcha, PrivacyConsentMixin):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True)

    class Meta(EventSubmitFormNoCaptcha.Meta):
        exclude = ('state', 'event') + EventSubmitFormNoCaptcha.Meta.exclude


class ProfileUpdateRequestForm(ProfileUpdateRequestFormNoCaptcha):
    captcha = ReCaptchaField()

    helper = BootstrapHelper(wider_labels=True, add_cancel_button=False)


class InvoiceRequestForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = InvoiceRequest
        fields = (
            'organization', 'reason', 'reason_other', 'date', 'event',
            'event_location', 'item_id', 'postal_number', 'contact_name',
            'contact_email', 'contact_phone', 'full_address', 'amount',
            'currency', 'currency_other', 'breakdown', 'vendor_form_required',
            'vendor_form_link', 'form_W9', 'receipts_sent',
            'shared_receipts_link', 'notes',
        )
        widgets = {
            'reason': forms.RadioSelect,
            'currency': forms.RadioSelect,
            'vendor_form_required': forms.RadioSelect,
            'receipts_sent': forms.RadioSelect,
        }


class InvoiceRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = InvoiceRequest
        fields = (
            'status', 'sent_date', 'paid_date', 'notes'
        )
