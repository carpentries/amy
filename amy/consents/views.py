from django.http.response import Http404
from consents.models import Consent
from consents.util import person_has_consented_to_required_terms
from workshops.base_views import RedirectSupportMixin
from consents.forms import ConsentsForm
from workshops.base_views import AMYCreateView, AMYDeleteView, AMYDetailView
from workshops.util import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render
from rest_framework.reverse import reverse


class ConsentDetails(AMYDetailView):
    queryset = Consent.objects.all()
    context_object_name = "task"
    pk_url_kwarg = "task_id"
    # template_name = "workshops/task.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Task {0}".format(self.object)
        return context


class ConsentCreate(RedirectSupportMixin, AMYCreateView):
    model = Consent
    form_class = ConsentsForm
    queryset = Consent.objects.select_related("term", "term_option")
    pk_url_kwarg = "consent_id"

    # success_url = "consents/edit"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context["initial"] = {"
        return context

    def get_success_message(self, *args, **kwargs):
        return "Consents were successfully updated."


class ConsentDelete(AMYDeleteView):
    pass


@login_required
def action_required_terms(request):
    person = request.user

    # disable the view for users who already agreed
    if person_has_consented_to_required_terms(person):
        raise Http404("This view is disabled.")

    form = ConsentsForm(person=person)

    if request.method == "POST":
        form = ConsentsForm(request.POST, instance=person)

        if form.is_valid() and form.instance == person:
            person = form.save()
            messages.success(request, "Agreement successfully saved.")

            if "next" in request.GET:
                return redirect(request.GET["next"])
            else:
                return redirect(reverse("dispatch"))
        else:
            messages.error(request, "Fix errors below.")

    context = {
        "title": "Action required: terms agreement",
        "form": form,
    }
    return render(request, "consents/action_required_terms.html", context)
