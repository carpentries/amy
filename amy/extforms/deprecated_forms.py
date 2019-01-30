from captcha.fields import ReCaptchaField

from extrequests.deprecated_forms import (
    SWCEventRequestNoCaptchaForm,
    DCEventRequestNoCaptchaForm,
    DCSelfOrganizedEventRequestFormNoCaptcha,
    EventSubmitFormNoCaptcha,
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
