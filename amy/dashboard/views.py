from datetime import date, timedelta
from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import (
    Case,
    Count,
    IntegerField,
    Prefetch,
    Q,
    QuerySet,
    Value,
    When,
)
from django.forms.widgets import HiddenInput
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView, View
from django.views.generic.detail import SingleObjectMixin
from django_comments.models import Comment
from flags.sources import get_flags
from flags.views import FlaggedViewMixin

from communityroles.models import CommunityRole
from consents.forms import TermBySlugsForm
from consents.models import Consent, Term, TermEnum
from dashboard.filters import UpcomingTeachingOpportunitiesFilter
from dashboard.forms import (
    AssignmentForm,
    AutoUpdateProfileForm,
    GetInvolvedForm,
    SearchForm,
    SignupForRecruitmentForm,
)
from dashboard.utils import (
    cross_multiple_Q_icontains,
    get_passed_or_last_progress,
    multiple_Q_icontains,
    tokenize,
)
from emails.signals import instructor_signs_up_for_workshop_signal
from extrequests.base_views import AMYCreateAndFetchObjectView
from fiscal.models import MembershipTask
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYListView,
    AMYUpdateView,
    ConditionallyEnabledMixin,
)
from workshops.models import (
    Airport,
    Badge,
    Event,
    Membership,
    Organization,
    Person,
    Qualification,
    Tag,
    Task,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
)
from workshops.utils.access import admin_required, login_required
from workshops.utils.urls import safe_next_or_default_url

# Terms shown on the instructor dashboard and can be updated by the user.
TERM_SLUGS = [TermEnum.MAY_CONTACT, TermEnum.PUBLIC_PROFILE, TermEnum.MAY_PUBLISH_NAME]


@login_required
def dispatch(request):
    """If user is admin, then show them admin dashboard; otherwise redirect
    them to instructor dashboard."""
    if request.user.is_admin:
        return redirect(reverse("admin-dashboard"))
    else:
        return redirect(reverse("instructor-dashboard"))


@admin_required
def admin_dashboard(request):
    """Home page for admins."""
    data = request.GET.copy()
    if "assigned_to" not in data:
        data["assigned_to"] = request.user.id
    assignment_form = AssignmentForm(data)
    assigned_to: Person | None = None
    if assignment_form.is_valid():
        assigned_to = assignment_form.cleaned_data["assigned_to"]

    current_events = Event.objects.current_events().prefetch_related("tags")

    # This annotation may produce wrong number of instructors when
    # `unpublished_events` filters out events that contain a specific tag.
    # The bug was fixed in #1130.
    unpublished_events = (
        Event.objects.active()
        .unpublished_events()
        .select_related("host")
        .annotate(
            num_instructors=Count(
                Case(
                    When(task__role__name="instructor", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
        )
        .order_by("-start")
    )

    # assigned events that have unaccepted changes
    updated_metadata = Event.objects.active().filter(metadata_changed=True)

    current_events = current_events.filter(assigned_to=assigned_to)
    unpublished_events = unpublished_events.filter(assigned_to=assigned_to)
    updated_metadata = updated_metadata.filter(assigned_to=assigned_to)

    context = {
        "title": None,
        "assignment_form": assignment_form,
        "assigned_to": assigned_to,
        "current_events": current_events,
        "unpublished_events": unpublished_events,
        "updated_metadata": updated_metadata.count(),
        "main_tags": Tag.objects.main_tags(),
    }
    return render(request, "dashboard/admin_dashboard.html", context)


# ------------------------------------------------------------
# Views for instructors and trainees


@login_required
def instructor_dashboard(request):
    qs = (
        Person.objects.annotate_with_role_count()  # type: ignore
        .select_related("airport")
        .prefetch_related(
            "badges",
            "lessons",
            "domains",
            "languages",
            Prefetch(
                "task_set",
                queryset=Task.objects.select_related("event", "role").order_by("event__start", "event__slug"),
            ),
            Prefetch(
                "membershiptask_set",
                queryset=MembershipTask.objects.select_related("membership", "role"),
            ),
        )
    )
    user = get_object_or_404(qs, id=request.user.id)

    consents = (
        Consent.objects.active()
        .filter(
            term__slug__in=TERM_SLUGS,
            person=user,
        )
        .select_related("term", "term_option")
    )
    consents_by_key = {consent.term.key: consent for consent in consents}
    # get display content for all visible terms
    consents_content = {term.key: term.content for term in Term.objects.filter(slug__in=TERM_SLUGS)}

    context = {
        "title": "Your profile",
        "user": user,
        "consents": consents_by_key,
        "consents_content": consents_content,
    }
    return render(request, "dashboard/instructor_dashboard.html", context)


@login_required
def autoupdate_profile(request):
    person = request.user
    consent_form_kwargs = {
        "initial": {"person": person},
        "widgets": {"person": HiddenInput()},
        "form_tag": False,
        "prefix": "consents",
    }
    form = AutoUpdateProfileForm(instance=person, form_tag=False, add_submit_button=False)
    consent_form = TermBySlugsForm(term_slugs=TERM_SLUGS, **consent_form_kwargs)

    if request.method == "POST":
        form = AutoUpdateProfileForm(request.POST, instance=person)
        consent_form = TermBySlugsForm(request.POST, term_slugs=TERM_SLUGS, **consent_form_kwargs)
        if form.is_valid() and form.instance == person and consent_form.is_valid():
            # save lessons
            person.lessons.clear()
            for lesson in form.cleaned_data["lessons"]:
                q = Qualification(lesson=lesson, person=person)
                q.save()

            # don't save related lessons
            del form.cleaned_data["lessons"]

            person = form.save()

            # save consents
            consent_form.save()

            messages.success(request, "Your profile was updated.")

            return redirect(reverse("instructor-dashboard"))
        else:
            messages.error(request, "Fix errors below.")

    context = {
        "title": "Update Your Profile",
        "form": form,
        "consents_form": consent_form,
    }
    return render(request, "dashboard/autoupdate_profile.html", context)


@login_required
def training_progress(request):
    # Add information about instructor training progress to request.user.
    request.user = (
        Person.objects.annotate_with_instructor_eligibility()
        .prefetch_related(
            Prefetch(
                "badges",
                to_attr="instructor_badges",
                queryset=Badge.objects.instructor_badges(),
            ),
        )
        .get(pk=request.user.pk)
    )

    progress_training = get_passed_or_last_progress(request.user, "Training")
    progress_get_involved = get_passed_or_last_progress(request.user, "Get Involved")
    progress_welcome = get_passed_or_last_progress(request.user, "Welcome Session")
    progress_demo = get_passed_or_last_progress(request.user, "Demo")

    context = {
        "title": "Your training progress",
        "progress_training": progress_training,
        "progress_get_involved": progress_get_involved,
        "progress_welcome": progress_welcome,
        "progress_demo": progress_demo,
    }
    return render(request, "dashboard/training_progress.html", context)


class GetInvolvedCreateView(LoginRequiredMixin, AMYCreateView):
    model = TrainingProgress
    form_class = GetInvolvedForm
    template_name = "get_involved_form.html"
    success_url = reverse_lazy("training-progress")
    success_message = "Thank you. Your Get Involved submission will be evaluated within 7-10 days."

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["title"] = "Submit your Get Involved activity"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        base_training_progress = TrainingProgress(
            trainee=self.request.user,
            state="n",  # not evaluated yet
            requirement=TrainingRequirement.objects.get(name="Get Involved"),
        )
        kwargs["instance"] = base_training_progress
        return kwargs

    def post(self, request, *args, **kwargs):
        self.request = request
        return super().post(request, *args, **kwargs)


class GetInvolvedUpdateView(LoginRequiredMixin, AMYUpdateView):
    form_class = GetInvolvedForm
    template_name = "get_involved_form.html"
    success_url = reverse_lazy("training-progress")
    success_message = "Your Get Involved submission was updated successfully."
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[TrainingProgress]:
        # user should only be able to update progress that belongs to them and has not
        # been evaluated yet
        return TrainingProgress.objects.filter(
            trainee=self.request.user,
            requirement__name="Get Involved",
            state="n",
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["title"] = "Update your Get Involved submission"
        return context


class GetInvolvedDeleteView(LoginRequiredMixin, AMYDeleteView):
    model = TrainingProgress
    success_url = reverse_lazy("training-progress")
    success_message = "Your Get Involved submission was deleted."
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[TrainingProgress]:
        # user should only be able to delete progress that belongs to them and has not
        # been evaluated yet
        return TrainingProgress.objects.filter(
            trainee=self.request.user,
            requirement__name="Get Involved",
            state="n",
        )


# ------------------------------------------------------------
# Views for instructors - upcoming teaching opportunities


class UpcomingTeachingOpportunitiesList(LoginRequiredMixin, FlaggedViewMixin, ConditionallyEnabledMixin, AMYListView):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.view_instructorrecruitment"
    title = "Upcoming Teaching Opportunities"
    template_name = "dashboard/upcoming_teaching_opportunities.html"
    filter_class = UpcomingTeachingOpportunitiesFilter

    def get_queryset(self):
        today = date.today()

        # this condition means: either venue, latitude and longitude are provided, or
        # the event has "online" tag
        location = (~Q(event__venue="") & Q(event__latitude__isnull=False) & Q(event__longitude__isnull=False)) | Q(
            event__tags__name="online"
        )

        self.queryset = (
            InstructorRecruitment.objects.annotate_with_priority()
            .select_related("event", "event__host")
            .filter(status="o", event__start__gte=today)
            .filter(location)
            .prefetch_related(
                "event__curricula",
                Prefetch(
                    "signups",
                    queryset=InstructorRecruitmentSignup.objects.filter(
                        person=self.request.user,
                    ),
                    to_attr="person_signup",
                ),
            )
            .order_by("event__start")
            .distinct()
        )
        return super().get_queryset()

    def get_view_enabled(self, request) -> bool:
        if request.user.is_admin:
            return True

        try:
            role = CommunityRole.objects.get(person=self.request.user, config__name="instructor")
            return role.is_active()
        except CommunityRole.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # person details with tasks counted
        context["person"] = (
            Person.objects.annotate_with_role_count().select_related("airport").get(pk=self.request.user.pk)
        )
        context["person_instructor_tasks_slugs"] = Task.objects.filter(
            role__name="instructor", person__pk=self.request.user.pk
        ).values_list("event__slug", flat=True)

        context["person_instructor_task_events"] = {
            task.event
            for task in Task.objects.filter(role__name="instructor", person__pk=self.request.user.pk).select_related(
                "event"
            )
        }

        context["person_signups"] = InstructorRecruitmentSignup.objects.filter(person=self.request.user).select_related(
            "recruitment", "recruitment__event"
        )

        return context


class SignupForRecruitment(
    LoginRequiredMixin,
    FlaggedViewMixin,
    ConditionallyEnabledMixin,
    AMYCreateAndFetchObjectView,
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = [
        "recruitment.view_instructorrecruitment",
        "recruitment.add_instructorrecruitmentsignup",
    ]
    title = "Signup for workshop"
    model = InstructorRecruitmentSignup
    queryset_other = InstructorRecruitment.objects.filter(status="o").select_related("event")
    context_other_object_name = "recruitment"
    pk_url_kwarg = "recruitment_pk"

    form_class = SignupForRecruitmentForm
    template_name = "dashboard/signup_for_recruitment.html"

    def get_view_enabled(self, request) -> bool:
        if request.user.is_admin:
            return True

        try:
            role = CommunityRole.objects.get(person=self.request.user, config__name="instructor")
            return role.is_active()
        except CommunityRole.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        self.other_object: InstructorRecruitment
        event = self.other_object.event

        context = super().get_context_data(**kwargs)
        context["title"] = f"Signup for workshop {event}"

        # person details with tasks counted
        context["person"] = (
            Person.objects.annotate_with_role_count().select_related("airport").get(pk=self.request.user.pk)
        )

        return context

    def get_success_message(self, cleaned_data):
        self.other_object: InstructorRecruitment
        event = self.other_object.event
        return f"Your interest in teaching at {event} has been recorded and is now " "pending."

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next", None)
        if next_url:
            next_url = unquote(next_url)
        success_url = reverse("upcoming-teaching-opportunities")
        return safe_next_or_default_url(next_url, success_url)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"person": self.request.user, "recruitment": self.other_object})
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.recruitment = self.other_object
        obj.person = self.request.user
        obj.save()

        # Check and display warnings
        recruitment: InstructorRecruitment = self.other_object
        event: Event = recruitment.event

        # existing instructor tasks within +-14days of this event
        if tasks_nearby := Task.objects.exclude(event=event).filter(
            person=self.request.user,
            role__name="instructor",
            event__start__lte=event.end + timedelta(days=14),
            event__end__gte=event.start - timedelta(days=14),
        ):
            messages.warning(
                self.request,
                "Selected event dates fall within 14 days of your other workshops: "
                f"{', '.join(task.event.slug for task in tasks_nearby)}",
            )

        # instructor has applied for opportunities in the same dates
        if conflicting_signups := InstructorRecruitmentSignup.objects.exclude(recruitment=recruitment).filter(
            person=self.request.user,
            recruitment__event__start__lte=event.end,
            recruitment__event__end__gte=event.start,
        ):
            gen = (signup.recruitment.event.slug for signup in conflicting_signups)
            messages.warning(
                self.request,
                "You have applied to other workshops on the same dates: " f"{', '.join(gen)}",
            )

        instructor_signs_up_for_workshop_signal.send(
            sender=obj,
            request=self.request,
            person_id=obj.person.pk,
            event_id=obj.recruitment.event.pk,
            instructor_recruitment_id=obj.recruitment.pk,
            instructor_recruitment_signup_id=obj.pk,
        )

        return super().form_valid(form)


class ResignFromRecruitment(
    LoginRequiredMixin,
    FlaggedViewMixin,
    ConditionallyEnabledMixin,
    SingleObjectMixin,
    View,
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = [
        "recruitment.view_instructorrecruitmentsignup",
        "recruitment.delete_instructorrecruitmentsignup",
    ]
    default_redirect_url = reverse_lazy("upcoming-teaching-opportunities")
    pk_url_kwarg = "signup_pk"

    def post(self, request, *args, **kwargs):
        self.request = request

        signup = self.get_object()
        recruitment = signup.recruitment
        signup.delete()

        messages.success(
            self.request,
            f"Your teaching request was removed from recruitment {recruitment.event}",
        )

        redirect_url = self.get_redirect_url()
        return redirect(redirect_url)

    def get_view_enabled(self, request) -> bool:
        if request.user.is_admin:
            return True

        try:
            role = CommunityRole.objects.get(person=self.request.user, config__name="instructor")
            return role.is_active()
        except CommunityRole.DoesNotExist:
            return False

    def get_queryset(self):
        return InstructorRecruitmentSignup.objects.filter(person=self.request.user, recruitment__status="o")

    def get_redirect_url(self) -> str:
        next_url = self.request.POST.get("next", None)
        return safe_next_or_default_url(next_url, self.default_redirect_url)


# ------------------------------------------------------------


@require_GET
@admin_required
def search(request: HttpRequest) -> HttpResponse:
    """Search the database by term."""

    term = ""
    organizations = None
    memberships = None
    events = None
    persons = None
    airports = None
    training_requests = None
    comments = None

    if request.method == "GET" and "term" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            term = form.cleaned_data.get("term", "").strip()
            tokens = tokenize(term)
            results_combined = []

            organizations = Organization.objects.filter(multiple_Q_icontains(term, "domain", "fullname")).order_by(
                "fullname"
            )
            results_combined += list(organizations)

            memberships = Membership.objects.filter(multiple_Q_icontains(term, "name", "registration_code")).order_by(
                "-agreement_start"
            )
            results_combined += list(memberships)

            events = Event.objects.filter(
                multiple_Q_icontains(
                    term, "slug", "host__domain", "host__fullname", "url", "contact", "venue", "address"
                )
            ).order_by("-slug")
            results_combined += list(events)

            persons = Person.objects.filter(
                multiple_Q_icontains(term, "personal", "middle", "family", "email", "secondary_email", "github")
                | (cross_multiple_Q_icontains(tokens[0], tokens[1], "personal", "family") if len(tokens) == 2 else Q())
            ).order_by("family")
            results_combined += list(persons)

            airports = Airport.objects.filter(multiple_Q_icontains(term, "iata", "fullname")).order_by("iata")
            results_combined += list(airports)

            training_requests = TrainingRequest.objects.filter(
                multiple_Q_icontains(
                    term,
                    "personal",
                    "middle",
                    "family",
                    "member_code",
                    "email",
                    "secondary_email",
                    "github",
                    "affiliation",
                    "location",
                    "user_notes",
                )
                | (cross_multiple_Q_icontains(tokens[0], tokens[1], "personal", "family") if len(tokens) == 2 else Q())
            ).order_by("family")
            results_combined += list(training_requests)

            comments = Comment.objects.filter(
                multiple_Q_icontains(
                    term,
                    "comment",
                    "user_name",
                    "user_email",
                    "user__personal",
                    "user__family",
                    "user__email",
                    "user__github",
                )
            ).prefetch_related("content_object")
            results_combined += list(comments)

            # only 1 record found? Let's move to it immediately
            if len(results_combined) == 1 and not form.cleaned_data["no_redirect"]:
                result = results_combined[0]
                msg = format_html(
                    "You were moved to this page, because your search <code>{}</code> yields only this result.",
                    term,
                )
                if isinstance(result, Comment):
                    messages.success(request, msg)
                    return redirect(result.content_object.get_absolute_url() + "#c{}".format(result.id))
                elif hasattr(result, "get_absolute_url"):
                    messages.success(request, msg)
                    return redirect(result.get_absolute_url())

        else:
            messages.error(request, "Fix errors below.")

    # if empty GET, we'll create a blank form
    else:
        form = SearchForm()

    context = {
        "title": "Search",
        "form": form,
        "term": term,
        "organisations": organizations,
        "memberships": memberships,
        "events": events,
        "persons": persons,
        "airports": airports,
        "comments": comments,
        "training_requests": training_requests,
    }
    return render(request, "dashboard/search.html", context)


# ------------------------------------------------------------


class AllFeatureFlags(ConditionallyEnabledMixin, LoginRequiredMixin, TemplateView):
    template_name = "dashboard/all_feature_flags.html"

    def get_view_enabled(self, request) -> bool:
        return bool(settings.PROD_ENVIRONMENT and request.user.is_superuser) or not bool(settings.PROD_ENVIRONMENT)

    def get(self, request: HttpRequest, *args, **kwargs):
        self.request = request
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flags = get_flags(request=self.request)
        context["feature_flags"] = sorted(flags.values(), key=lambda x: x.name)
        context["title"] = "Feature flags"
        return context
