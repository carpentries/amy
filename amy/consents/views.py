from consents.forms import ActiveTermConsentsForm
from consents.models import Consent
from consents.util import person_has_consented_to_required_terms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import HiddenInput
from django.http.response import Http404
from django.shortcuts import redirect, render
from rest_framework.reverse import reverse
from workshops.base_views import AMYCreateView, RedirectSupportMixin
from workshops.util import login_required


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


@login_required
def action_required_terms(request):
    person = request.user

    # disable the view for users who already agreed
    if person_has_consented_to_required_terms(person):
        raise Http404("This view is disabled.")

    kwargs = {
        "initial": {"person": person},
        "widgets": {"person": HiddenInput()},
    }
    if request.method == "POST":
        form = ActiveTermConsentsForm(request.POST, person=person, **kwargs)
        if form.is_valid():
            form.save()
            messages.success(request, "Agreement successfully saved.")

            if "next" in request.GET:
                return redirect(request.GET["next"])
            else:
                return redirect(reverse("dispatch"))
        else:
            messages.error(request, "Fix errors below.")
    if request.method == "GET":
        form = ActiveTermConsentsForm(person=person, **kwargs)

    context = {
        "title": "Action required: terms agreement",
        "form": form,
    }
    return render(request, "consents/action_required_terms.html", context)
