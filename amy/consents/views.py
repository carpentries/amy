from consents.forms import ActiveTermConsentsForm
from consents.models import Consent
from django.contrib.auth.mixins import LoginRequiredMixin
from workshops.base_views import AMYCreateView, RedirectSupportMixin


class ConsentsUpdate(RedirectSupportMixin, AMYCreateView, LoginRequiredMixin):
    model = Consent
    form_class = ActiveTermConsentsForm

    def get_success_url(self):
        # Currently can only be called via redirect.
        # There is no direct view for Consents.
        next_url = self.request.GET["next"]
        return next_url

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        person = kwargs["data"]["consents-person"]
        kwargs.update({"prefix": "consents", "person": person})
        return kwargs

    def get_success_message(self, *args, **kwargs):
        return "Consents were successfully updated."
