import csv
import io
import logging
from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, ProtectedError, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from requests.exceptions import HTTPError, RequestException

from consents.models import Term, TermOption, TrainingRequestConsent
from consents.util import reconsent_for_term_option_type
from emails.actions.new_self_organised_workshop import new_self_organised_workshop_check
from emails.actions.post_workshop_7days import (
    post_workshop_7days_strategy,
    run_post_workshop_7days_strategy,
)
from emails.signals import new_self_organised_workshop_signal
from extrequests.base_views import AMYCreateAndFetchObjectView, WRFInitial
from extrequests.filters import (
    SelfOrganisedSubmissionFilter,
    TrainingRequestFilter,
    WorkshopInquiryFilter,
    WorkshopRequestFilter,
)
from extrequests.forms import (
    BulkChangeTrainingRequestForm,
    BulkMatchTrainingRequestForm,
    MatchTrainingRequestForm,
    SelfOrganisedSubmissionAdminForm,
    TrainingRequestsMergeForm,
    TrainingRequestsSelectionForm,
    TrainingRequestUpdateForm,
    WorkshopInquiryRequestAdminForm,
    WorkshopRequestAdminForm,
)
from extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from extrequests.utils import (
    accept_training_request_and_match_to_event,
    get_membership_from_training_request_or_raise_error,
    get_membership_or_none_from_code,
    get_membership_warnings_after_match,
)
from workshops.base_views import (
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
    AssignView,
    AuthenticatedHttpRequest,
    ChangeRequestStateView,
    RedirectSupportMixin,
    StateFilterMixin,
)
from workshops.exceptions import InternalError, WrongWorkshopURL
from workshops.forms import (
    AdminLookupForm,
    BootstrapHelper,
    BulkUploadCSVForm,
    EventCreateForm,
)
from workshops.models import (
    Event,
    Language,
    Membership,
    Organization,
    Person,
    Role,
    Task,
    TrainingRequest,
    WorkshopRequest,
)
from workshops.utils.access import OnlyForAdminsMixin, admin_required
from workshops.utils.merge import merge_objects
from workshops.utils.metadata import fetch_workshop_metadata, parse_workshop_metadata
from workshops.utils.trainingrequest_upload import (
    clean_upload_trainingrequest_manual_score,
    update_manual_score,
    upload_trainingrequest_manual_score_csv,
)
from workshops.utils.urls import safe_next_or_default_url
from workshops.utils.usernames import create_username
from workshops.utils.views import failed_to_delete

logger = logging.getLogger("amy")


# ------------------------------------------------------------
# WorkshopRequest related views
# ------------------------------------------------------------


class AllWorkshopRequests(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = "requests"
    template_name = "requests/all_workshoprequests.html"
    filter_class = WorkshopRequestFilter
    queryset = WorkshopRequest.objects.select_related("assigned_to", "institution").prefetch_related(
        "requested_workshop_types"
    )
    title = "Workshop requests"


class WorkshopRequestDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = WorkshopRequest.objects.all()
    context_object_name = "object"
    template_name = "requests/workshoprequest.html"
    pk_url_kwarg = "request_id"
    object: WorkshopRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Workshop request #{}".format(self.get_object().pk)

        member_code = cast(WorkshopRequest, self.get_object()).member_code
        context["membership"] = get_membership_or_none_from_code(member_code)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(initial={"person": self.object.assigned_to})

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse("workshoprequest_assign", args=[self.object.pk]),
            add_cancel_button=False,
        )

        context["person_lookup_form"] = person_lookup_form

        return context


class WorkshopRequestChange(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "workshops.change_workshoprequest"
    model = WorkshopRequest
    pk_url_kwarg = "request_id"
    form_class = WorkshopRequestAdminForm
    template_name = "generic_form_with_comments.html"


class WorkshopRequestSetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = "workshops.change_workshoprequest"
    model = WorkshopRequest
    pk_url_kwarg = "request_id"
    state_url_kwarg = "state"
    permanent = False


class WorkshopRequestAcceptEvent(OnlyForAdminsMixin, PermissionRequiredMixin, WRFInitial, AMYCreateAndFetchObjectView):
    permission_required = ["workshops.change_workshoprequest", "workshops.add_event"]
    model = Event
    form_class = EventCreateForm
    template_name = "requests/workshoprequest_accept_event.html"

    queryset_other = WorkshopRequest.objects.filter(state="p")
    context_other_object_name = "object"
    pk_url_kwarg = "request_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["title"] = "Accept and create a new event"

        member_code = cast(WorkshopRequest, self.get_other_object()).member_code
        context["membership"] = get_membership_or_none_from_code(member_code)

        return context

    def get_success_url(self):
        return reverse("event_details", args=[self.object.slug])

    def form_valid(self, form):
        self.object = form.save()

        event = self.object
        workshop_request = cast(WorkshopRequest, self.other_object)

        person = workshop_request.host()
        if person:
            Task.objects.create(event=event, person=person, role=Role.objects.get(name="host"))

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(event),
            self.request,
            event,
        )

        workshop_request.state = "a"
        workshop_request.event = event
        workshop_request.save()
        return super().form_valid(form)


class WorkshopRequestAssign(OnlyForAdminsMixin, AssignView):
    permission_required = "workshops.change_workshoprequest"
    model = WorkshopRequest
    pk_url_kwarg = "request_id"
    person_url_kwarg = "person_id"


# ------------------------------------------------------------
# WorkshopInquiryRequest related views
# ------------------------------------------------------------


class AllWorkshopInquiries(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = "inquiries"
    template_name = "requests/all_workshopinquiries.html"
    filter_class = WorkshopInquiryFilter
    queryset = WorkshopInquiryRequest.objects.select_related("assigned_to", "institution").prefetch_related(
        "requested_workshop_types"
    )
    title = "Workshop inquiries"


class WorkshopInquiryDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = WorkshopInquiryRequest.objects.all()
    context_object_name = "object"
    template_name = "requests/workshopinquiry.html"
    pk_url_kwarg = "inquiry_id"
    object: WorkshopInquiryRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Workshop inquiry #{}".format(self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(initial={"person": self.object.assigned_to})

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse("workshopinquiry_assign", args=[self.object.pk]),
            add_cancel_button=False,
        )

        context["person_lookup_form"] = person_lookup_form
        return context


class WorkshopInquiryChange(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "extrequests.change_workshopinquiryrequest"
    model = WorkshopInquiryRequest
    pk_url_kwarg = "inquiry_id"
    form_class = WorkshopInquiryRequestAdminForm
    template_name = "generic_form_with_comments.html"


class WorkshopInquirySetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = "extrequests.change_workshopinquiryrequest"
    model = WorkshopInquiryRequest
    pk_url_kwarg = "inquiry_id"
    state_url_kwarg = "state"
    permanent = False


class WorkshopInquiryAcceptEvent(OnlyForAdminsMixin, PermissionRequiredMixin, WRFInitial, AMYCreateAndFetchObjectView):
    permission_required = [
        "extrequests.change_workshopinquiryrequest",
        "workshops.add_event",
    ]
    model = Event
    form_class = EventCreateForm
    template_name = "requests/workshopinquiry_accept_event.html"

    queryset_other = WorkshopInquiryRequest.objects.filter(state="p")
    context_other_object_name = "object"
    pk_url_kwarg = "inquiry_id"

    def get_context_data(self, **kwargs):
        kwargs["title"] = "Accept and create a new event"
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("event_details", args=[self.object.slug])

    def form_valid(self, form):
        self.object = form.save()

        event = self.object
        inquiry = cast(WorkshopInquiryRequest, self.other_object)

        person = inquiry.host()
        if person:
            Task.objects.create(event=event, person=person, role=Role.objects.get(name="host"))

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(event),
            self.request,
            event,
        )

        inquiry.state = "a"
        inquiry.event = event
        inquiry.save()
        return super().form_valid(form)


class WorkshopInquiryAssign(OnlyForAdminsMixin, AssignView):
    permission_required = "extrequests.change_workshopinquiryrequest"
    model = WorkshopInquiryRequest
    pk_url_kwarg = "inquiry_id"
    person_url_kwarg = "person_id"


# ------------------------------------------------------------
# SelfOrganisedSubmission related views
# ------------------------------------------------------------


class AllSelfOrganisedSubmissions(OnlyForAdminsMixin, StateFilterMixin, AMYListView):
    context_object_name = "submissions"
    template_name = "requests/all_selforganisedsubmissions.html"
    filter_class = SelfOrganisedSubmissionFilter
    queryset = SelfOrganisedSubmission.objects.select_related("assigned_to", "institution").prefetch_related(
        "workshop_types"
    )
    title = "Self-Organised submissions"


class SelfOrganisedSubmissionDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = SelfOrganisedSubmission.objects.all()
    context_object_name = "object"
    template_name = "requests/selforganisedsubmission.html"
    pk_url_kwarg = "submission_id"
    object: SelfOrganisedSubmission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Self-Organised submission #{}".format(self.get_object().pk)

        person_lookup_form = AdminLookupForm()
        if self.object.assigned_to:
            person_lookup_form = AdminLookupForm(initial={"person": self.object.assigned_to})

        person_lookup_form.helper = BootstrapHelper(
            form_action=reverse("selforganisedsubmission_assign", args=[self.object.pk]),
            add_cancel_button=False,
        )

        context["person_lookup_form"] = person_lookup_form
        return context


class SelfOrganisedSubmissionChange(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "extrequests.change_selforganisedsubmission"
    model = SelfOrganisedSubmission
    pk_url_kwarg = "submission_id"
    form_class = SelfOrganisedSubmissionAdminForm
    template_name = "generic_form_with_comments.html"


class SelfOrganisedSubmissionSetState(OnlyForAdminsMixin, ChangeRequestStateView):
    permission_required = "extrequests.change_selforganisedsubmission"
    model = SelfOrganisedSubmission
    pk_url_kwarg = "submission_id"
    state_url_kwarg = "state"
    permanent = False


class SelfOrganisedSubmissionAcceptEvent(
    OnlyForAdminsMixin, PermissionRequiredMixin, WRFInitial, AMYCreateAndFetchObjectView
):
    permission_required = [
        "extrequests.change_selforganisedsubmission",
        "workshops.add_event",
    ]
    model = Event
    form_class = EventCreateForm
    template_name = "requests/selforganisedsubmission_accept_event.html"

    queryset_other = SelfOrganisedSubmission.objects.filter(state="p")
    context_other_object_name = "object"
    pk_url_kwarg = "submission_id"
    other_object: SelfOrganisedSubmission

    def get_form_kwargs(self):
        """Extend form kwargs with `initial` values.

        The initial values are read from SelfOrganisedSubmission request
        object, and from corresponding workshop page (if it's possible)."""
        kwargs = super().get_form_kwargs()

        # no matter what, don't show "lessons" field; previously they were shown
        # when mix&match was selected
        kwargs["show_lessons"] = False

        url = self.other_object.workshop_url.strip()
        data = {
            "url": url,
            "host": self.other_object.host_organization() or self.other_object.institution,
            "administrator": Organization.objects.get(domain="self-organized"),
        }

        try:
            metadata = fetch_workshop_metadata(url)
            parsed_data = parse_workshop_metadata(metadata)
        except (AttributeError, HTTPError, RequestException, WrongWorkshopURL):
            # ignore errors, but show warning instead
            messages.warning(
                self.request,
                "Cannot automatically fill the form " "from provided workshop URL.",
            )
        else:
            # keep working only if no exception occurred
            try:
                lang = parsed_data["language"].lower()
                parsed_data["language"] = Language.objects.get(subtag=lang)
            except (KeyError, ValueError, Language.DoesNotExist):
                # ignore non-existing
                messages.warning(self.request, "Cannot automatically fill language.")
                # it's easier to remove bad value than to leave
                # 500 Server Error when the form is rendered
                if "language" in parsed_data:
                    del parsed_data["language"]

            data.update(parsed_data)

            if "instructors" in data or "helpers" in data:
                instructors = data.get("instructors") or ["none"]
                helpers = data.get("helpers") or ["none"]
                data["comment"] = f"Instructors: {','.join(instructors)}\n\n" f"Helpers: {','.join(helpers)}"

        initial = super().get_initial()
        initial.update(data)
        kwargs["initial"] = initial
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs["title"] = "Accept and create a new event"
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("event_details", args=[self.object.slug])

    def form_valid(self, form):
        self.object = form.save()

        event = self.object
        submission = cast(SelfOrganisedSubmission, self.other_object)

        person = submission.host()
        if person:
            Task.objects.create(event=event, person=person, role=Role.objects.get(name="host"))

        submission.state = "a"
        submission.event = event
        submission.save()

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(event),
            self.request,
            event,
        )

        if new_self_organised_workshop_check(event):
            new_self_organised_workshop_signal.send(
                sender=event,
                request=self.request,
                event=event,
                self_organised_submission=submission,
            )

        return super().form_valid(form)


class SelfOrganisedSubmissionAssign(OnlyForAdminsMixin, AssignView):
    permission_required = "extrequests.change_selforganisedsubmission"
    model = SelfOrganisedSubmission
    pk_url_kwarg = "submission_id"
    person_url_kwarg = "person_id"


# ------------------------------------------------------------
# TrainingRequest related views
# ------------------------------------------------------------


@admin_required
def all_trainingrequests(request):
    filter_ = TrainingRequestFilter(
        request.GET,
        queryset=TrainingRequest.objects.all().prefetch_related(
            Prefetch(
                "person__task_set",
                to_attr="training_tasks",
                queryset=Task.objects.filter(role__name="learner", event__tags__name="TTT").select_related("event"),
            ),
        ),
    )

    form = BulkChangeTrainingRequestForm()
    match_form = BulkMatchTrainingRequestForm()

    if request.method == "POST" and "match" in request.POST:
        # Bulk match people associated with selected TrainingRequests to
        # trainings.
        match_form = BulkMatchTrainingRequestForm(request.POST)

        if match_form.is_valid():
            event = match_form.cleaned_data["event"]
            membership = match_form.cleaned_data["seat_membership"]
            membership_auto_assign = match_form.cleaned_data["seat_membership_auto_assign"]
            seat_public = match_form.cleaned_data["seat_public"]
            open_seat = match_form.cleaned_data["seat_open_training"]
            role = Role.objects.get(name="learner")

            # Perform bulk match using one of two methods
            training_requests = match_form.cleaned_data["requests"]
            errors = []
            warnings = []

            # Method 1: Auto assign membership
            # membership is different for each seat (and may not be None)
            if membership_auto_assign:
                for r in training_requests:
                    # find which membership to use
                    # if membership can't be determined, skip this request
                    try:
                        membership_to_use = get_membership_from_training_request_or_raise_error(r)
                    except (ValueError, Membership.DoesNotExist) as e:
                        errors.append(str(e))
                        continue

                    # perform match
                    accept_training_request_and_match_to_event(
                        request=r,
                        event=event,
                        role=role,
                        seat_public=seat_public,
                        seat_open_training=open_seat,
                        seat_membership=membership_to_use,
                    )

                    # collect warnings after each match
                    warnings += [
                        f"{r}: {w}"
                        for w in get_membership_warnings_after_match(
                            membership=membership_to_use,
                            seat_public=seat_public,
                            event=event,
                        )
                    ]

            # Method 2: Don't auto assign membership
            # membership is same for all seats (and may be None)
            else:
                # perform matches
                for r in training_requests:
                    accept_training_request_and_match_to_event(
                        request=r,
                        event=event,
                        role=role,
                        seat_public=seat_public,
                        seat_open_training=open_seat,
                        seat_membership=membership,
                    )

                # collect warnings after all requests are processed
                if membership:
                    warnings = get_membership_warnings_after_match(
                        membership=membership, seat_public=seat_public, event=event
                    )

            # Matching is complete, display messages
            for msg in warnings:
                messages.warning(request, msg)
            for msg in errors:
                messages.error(request, msg)
            if errors:
                changed_count = len(match_form.cleaned_data["requests"]) - len(errors)
                info_msg = (
                    f"Accepted and matched {changed_count} "
                    f'{"person" if changed_count == 1 else "people"} to training, '
                    f"which raised {len(warnings)} warning(s). "
                    f"{len(errors)} request(s) were skipped due to errors."
                )
                messages.info(request, info_msg)
            else:
                messages.success(
                    request,
                    "Successfully accepted and matched selected people to training.",
                )

    elif request.method == "POST" and "accept" in request.POST:
        # Bulk discard selected TrainingRequests.
        form = BulkChangeTrainingRequestForm(request.POST)

        if form.is_valid():
            # Perform bulk discard
            for r in form.cleaned_data["requests"]:
                r.state = "a"
                r.save()

            messages.success(request, "Successfully accepted selected " "requests.")

    elif request.method == "POST" and "discard" in request.POST:
        # Bulk discard selected TrainingRequests.
        form = BulkChangeTrainingRequestForm(request.POST)

        if form.is_valid():
            # Perform bulk discard
            for r in form.cleaned_data["requests"]:
                r.state = "d"
                r.save()

            messages.success(request, "Successfully discarded selected " "requests.")

    elif request.method == "POST" and "unmatch" in request.POST:
        # Bulk unmatch people associated with selected TrainingRequests from
        # trainings.
        form = BulkChangeTrainingRequestForm(request.POST)

        form.check_person_matched = True
        if form.is_valid():
            # Perform bulk unmatch
            for r in form.cleaned_data["requests"]:
                r.person.get_training_tasks().delete()

            messages.success(request, "Successfully unmatched selected " "people from trainings.")

    context = {
        "title": "Training Requests",
        "requests": filter_.qs,
        "filter": filter_,
        "form": form,
        "match_form": match_form,
    }

    return render(request, "requests/all_trainingrequests.html", context)


@transaction.atomic
def _match_training_request_to_person(
    request: HttpRequest,
    training_request: TrainingRequest,
    person: Person,
    create: bool = False,
) -> bool:
    if create:
        try:
            training_request.person = Person.objects.create_user(
                username=create_username(training_request.personal, training_request.family),
                personal=training_request.personal,
                family=training_request.family,
                email=training_request.email,
            )
        except IntegrityError:
            # email address is not unique
            messages.error(
                request,
                "Could not create a new person, because " "there already exists a person with " "exact email address.",
            )
            return False

    else:
        training_request.person = person

    # as per #1270:
    # https://github.com/carpentries/amy/issues/1270#issuecomment-407515948
    # let's rewrite everything that's possible to rewrite
    try:
        training_request.person.personal = training_request.personal
        training_request.person.middle = training_request.middle
        training_request.person.family = training_request.family
        training_request.person.email = training_request.email
        training_request.person.secondary_email = training_request.secondary_email
        training_request.person.country = training_request.country
        training_request.person.github = training_request.github
        training_request.person.affiliation = training_request.affiliation
        training_request.person.domains.set(training_request.domains.all())
        training_request.person.occupation = (
            training_request.get_occupation_display()  # type: ignore
            if training_request.occupation
            else training_request.occupation_other
        )
        training_request.person.is_active = True

        training_request.person.save()
        training_request.person.synchronize_usersocialauth()
        training_request.save()

        messages.success(request, "Request matched with the person.")

    except IntegrityError:
        # email or github not unique
        messages.warning(
            request,
            "It was impossible to update related "
            "person's data. Probably email address or "
            "Github handle used in the training request "
            "are not unique amongst person entries.",
        )
        return False

    # Create new style consents based on the training request consents used in the
    # training request form.
    training_request_consents = TrainingRequestConsent.objects.filter(training_request=training_request).select_related(
        "term_option", "term"
    )
    for consent in training_request_consents:
        try:
            option_type = consent.term_option.option_type
            reconsent_for_term_option_type(
                term_key=consent.term.key,
                term_option_type=option_type,
                person=training_request.person,
            )
        except (Term.DoesNotExist, TermOption.DoesNotExist):
            logger.warning(f"Either Term {consent.term.key} or its term option was not found, " "can't proceed.")
            messages.error(
                request,
                f"Error when setting person's consents. Term {consent.term.key} or "
                "related term option may not exist.",
            )
            return False

    return True


@admin_required
def trainingrequest_details(request: HttpRequest, pk: str) -> HttpResponse:
    req = get_object_or_404(TrainingRequest, pk=int(pk))

    if request.method == "POST":
        form = MatchTrainingRequestForm(request.POST)

        if form.is_valid():
            create = form.action == "create"
            person = form.cleaned_data["person"]
            ok = _match_training_request_to_person(request, training_request=req, person=person, create=create)
            if ok:
                next_url = request.GET.get("next", None)
                default_url = reverse("trainingrequest_details", args=[req.pk])
                return redirect(safe_next_or_default_url(next_url, default_url))

    else:  # GET request
        # Provide initial value for form.person
        if req.person is not None:
            person = req.person
        else:
            # No person is matched to the TrainingRequest yet. Suggest a
            # person from existing records.
            primary_email = Q(email__iexact=req.email) | Q(secondary_email__iexact=req.email)
            # only match secondary email if there's one provided, otherwise
            # we could get false-positive matches for empty email.
            secondary_email = (
                Q()
                if not req.secondary_email
                else (Q(email__iexact=req.secondary_email) | Q(secondary_email__iexact=req.secondary_email))
            )
            name = Q(
                personal__iexact=req.personal,
                middle__iexact=req.middle,
                family__iexact=req.family,
            )
            person = Person.objects.filter(primary_email | secondary_email | name).first()  # may return None
        form = MatchTrainingRequestForm(initial={"person": person})

    TERM_SLUGS = ["may-contact", "privacy-policy", "public-profile"]
    context = {
        "title": "Training request #{}".format(req.pk),
        "req": req,
        "form": form,
        "consents": {
            consent.term.key: consent
            for consent in TrainingRequestConsent.objects.select_related("term", "term_option").filter(
                training_request=req
            )
        },
        "consents_content": {term.key: term.content for term in Term.objects.filter(slug__in=TERM_SLUGS)},
    }
    return render(request, "requests/trainingrequest.html", context)


class TrainingRequestUpdate(RedirectSupportMixin, OnlyForAdminsMixin, AMYUpdateView):
    model = TrainingRequest
    form_class = TrainingRequestUpdateForm
    template_name = "generic_form_with_comments.html"

    def get_form_kwargs(self):
        # request is required for ENFORCE_MEMBER_CODES flag
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


@admin_required
@permission_required(
    ["workshops.delete_trainingrequest", "workshops.change_trainingrequest"],
    raise_exception=True,
)
def trainingrequests_merge(request: AuthenticatedHttpRequest) -> HttpResponse:
    """Display two training requests side by side on GET and merge them on
    POST.

    If no requests are supplied via GET params, display event selection
    form."""
    obj_a_pk = request.GET.get("trainingrequest_a")
    obj_b_pk = request.GET.get("trainingrequest_b")

    if not obj_a_pk or not obj_b_pk:
        context = {
            "title": "Select Training Requests to merge",
            "form": TrainingRequestsSelectionForm(),
        }
        return render(request, "generic_form.html", context)

    obj_a = get_object_or_404(TrainingRequest, pk=obj_a_pk)
    obj_b = get_object_or_404(TrainingRequest, pk=obj_b_pk)

    form = TrainingRequestsMergeForm(initial=dict(trainingrequest_a=obj_a, trainingrequest_b=obj_b))

    if request.method == "POST":
        form = TrainingRequestsMergeForm(request.POST)

        if form.is_valid():
            # merging in process
            data = form.cleaned_data

            obj_a = data["trainingrequest_a"]
            obj_b = data["trainingrequest_b"]

            # `base_obj` stays in the database after merge
            # `merging_obj` will be removed from DB after merge
            if data["id"] == "obj_a":
                base_obj = obj_a
                merging_obj = obj_b
                base_a = True
            else:
                base_obj = obj_b
                merging_obj = obj_a
                base_a = False

            # non-M2M-relationships:
            easy = (
                "state",
                "person",
                "member_code",
                "personal",
                "middle",
                "family",
                "email",
                "secondary_email",
                "github",
                "occupation",
                "occupation_other",
                "affiliation",
                "location",
                "country",
                "underresourced",
                "domains_other",
                "underrepresented",
                "underrepresented_details",
                "nonprofit_teaching_experience",
                "previous_training",
                "previous_training_other",
                "previous_training_explanation",
                "previous_experience",
                "previous_experience_other",
                "previous_experience_explanation",
                "programming_language_usage_frequency",
                "checkout_intent",
                "teaching_intent",
                "teaching_frequency_expectation",
                "teaching_frequency_expectation_other",
                "max_travelling_frequency",
                "max_travelling_frequency_other",
                "reason",
                "user_notes",
                "data_privacy_agreement",
                "code_of_conduct_agreement",
                "created_at",
                "last_updated_at",
            )
            # M2M relationships
            difficult = (
                "domains",
                "previous_involvement",
                "comments",
                "trainingrequestconsent_set",
            )

            try:
                _, integrity_errors = merge_objects(obj_a, obj_b, easy, difficult, choices=data, base_a=base_a)

                if integrity_errors:
                    msg = "There were integrity errors when merging related " "objects:\n" "\n".join(integrity_errors)
                    messages.warning(request, msg)

            except ProtectedError as e:
                return failed_to_delete(request, object=merging_obj, protected_objects=e.protected_objects)

            else:
                return redirect(base_obj.get_absolute_url())
        else:
            messages.error(request, "Fix errors in the form.")

    context = {
        "title": "Merge two training requets",
        "obj_a": obj_a,
        "obj_b": obj_b,
        "form": form,
        "obj_a_consents": {
            consent.term.key: consent
            for consent in TrainingRequestConsent.objects.select_related("term", "term_option").filter(
                training_request=obj_a
            )
        },
        "obj_b_consents": {
            consent.term.key: consent
            for consent in TrainingRequestConsent.objects.select_related("term", "term_option").filter(
                training_request=obj_b
            )
        },
    }
    return render(request, "requests/trainingrequests_merge.html", context)


@admin_required
@permission_required(["workshops.change_trainingrequest"], raise_exception=True)
def bulk_upload_training_request_scores(request):
    if request.method == "POST":
        form = BulkUploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            charset = request.FILES["file"].charset or settings.DEFAULT_CHARSET
            stream = io.TextIOWrapper(request.FILES["file"].file, charset)
            try:
                data = upload_trainingrequest_manual_score_csv(stream)
            except csv.Error as e:
                messages.error(request, "Error processing uploaded .CSV file: {}".format(e))
            except UnicodeDecodeError:
                messages.error(request, "Please provide a file in {} encoding.".format(charset))
            else:
                request.session["bulk-upload-training-request-scores"] = data
                return redirect("bulk_upload_training_request_scores_confirmation")

        else:
            messages.error(request, "Fix errors below.")

    else:
        form = BulkUploadCSVForm()

    context = {
        "title": "Bulk upload Training Requests manual score",
        "form": form,
        "charset": settings.DEFAULT_CHARSET,
    }
    return render(
        request,
        "requests/trainingrequest_bulk_upload_manual_score_form.html",
        context,
    )


@admin_required
@permission_required(["workshops.change_trainingrequest"], raise_exception=True)
def bulk_upload_training_request_scores_confirmation(request):
    """This view allows for verifying and saving of uploaded training
    request scores."""
    data = request.session.get("bulk-upload-training-request-scores")

    if not data:
        messages.warning(request, "Could not locate CSV data, please upload again.")
        return redirect("bulk_upload_training_request_scores")

    if request.method == "POST":
        if request.POST.get("confirm", None) and not request.POST.get("cancel", None):
            errors, cleaned_data = clean_upload_trainingrequest_manual_score(data)

            if not errors:
                try:
                    records_count = update_manual_score(cleaned_data)
                except (
                    IntegrityError,
                    ObjectDoesNotExist,
                    InternalError,
                    TypeError,
                    ValueError,
                ) as e:
                    messages.error(
                        request,
                        "Error saving data to the database: {}. Please make "
                        "sure to fix all errors listed below.".format(e),
                    )
                    errors, cleaned_data = clean_upload_trainingrequest_manual_score(data)
                else:
                    request.session["bulk-upload-training-request-scores"] = None
                    messages.success(
                        request,
                        "Successfully updated {} Training Requests.".format(records_count),
                    )
                    return redirect("bulk_upload_training_request_scores")
            else:
                messages.warning(
                    request,
                    "Please fix the data according to error messages below.",
                )

        else:
            # any "cancel" or lack of "confirm" in POST cancels the upload
            request.session["bulk-upload-training-request-scores"] = None
            return redirect("bulk_upload_training_request_scores")

    else:
        errors, cleaned_data = clean_upload_trainingrequest_manual_score(data)
        if errors:
            messages.warning(
                request,
                "Please fix errors in the provided CSV file and re-upload.",
            )

    context = {
        "title": "Confirm uploaded Training Requests manual score data",
        "any_errors": errors,
        "zipped": zip(cleaned_data, data),
    }
    return render(
        request,
        "requests/trainingrequest_bulk_upload_manual_score_confirmation.html",
        context,
    )
