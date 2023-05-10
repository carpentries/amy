from datetime import date, timedelta
import re
from urllib.parse import unquote

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
from django.forms.widgets import HiddenInput
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.decorators.http import require_GET
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django_comments.models import Comment

from autoemails.utils import safe_next_or_default_url
from communityroles.models import CommunityRole
from consents.forms import TermBySlugsForm
from consents.models import Consent, Term, TermEnum
from dashboard.filters import UpcomingTeachingOpportunitiesFilter
from dashboard.forms import (
    AssignmentForm,
    AutoUpdateProfileForm,
    LessonContributionForm,
    SearchForm,
    SignupForRecruitmentForm,
)
from extrequests.base_views import AMYCreateAndFetchObjectView
from fiscal.models import MembershipTask
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from recruitment.views import RecruitmentEnabledMixin
from workshops.base_views import AMYListView, ConditionallyEnabledMixin
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
    qs = Person.objects.select_related("airport").prefetch_related(
        "badges",
        "lessons",
        "domains",
        "languages",
        Prefetch(
            "task_set",
            queryset=Task.objects.select_related("event", "role").order_by(
                "event__start", "event__slug"
            ),
        ),
        Prefetch(
            "membershiptask_set",
            queryset=MembershipTask.objects.select_related("membership", "role"),
        ),
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
    consents_content = {
        term.key: term.content for term in Term.objects.filter(slug__in=TERM_SLUGS)
    }

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
    form = AutoUpdateProfileForm(
        instance=person, form_tag=False, add_submit_button=False
    )
    consent_form = TermBySlugsForm(term_slugs=TERM_SLUGS, **consent_form_kwargs)

    if request.method == "POST":
        form = AutoUpdateProfileForm(request.POST, instance=person)
        consent_form = TermBySlugsForm(
            request.POST, term_slugs=TERM_SLUGS, **consent_form_kwargs
        )
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
    lesson_contribution_form = LessonContributionForm()

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

    progresses = request.user.trainingprogress_set
    last_lesson_contribution = (
        progresses.filter(requirement__name="Lesson Contribution")
        .order_by("-created_at")
        .first()
    )

    if request.method == "POST":
        lesson_contribution_form = LessonContributionForm(data=request.POST)
        if lesson_contribution_form.is_valid():
            TrainingProgress.objects.create(
                trainee=request.user,
                state="n",  # not evaluated yet
                requirement=TrainingRequirement.objects.get(name="Lesson Contribution"),
                url=lesson_contribution_form.cleaned_data["url"],
            )
            messages.success(
                request, "Your Lesson Contribution submission will be evaluated soon."
            )
            return redirect(reverse("training-progress"))

    context = {
        "title": "Your training progress",
        "lesson_contribution_form": lesson_contribution_form,
        "lesson_contribution_in_evaluation": (
            last_lesson_contribution is not None
            and last_lesson_contribution.state == "n"
        ),
    }
    return render(request, "dashboard/training_progress.html", context)


# ------------------------------------------------------------
# Views for instructors - upcoming teaching opportunities


class UpcomingTeachingOpportunitiesList(
    LoginRequiredMixin, RecruitmentEnabledMixin, ConditionallyEnabledMixin, AMYListView
):
    permission_required = "recruitment.view_instructorrecruitment"
    title = "Upcoming Teaching Opportunities"
    template_name = "dashboard/upcoming_teaching_opportunities.html"
    filter_class = UpcomingTeachingOpportunitiesFilter

    def get_queryset(self):
        today = date.today()

        # this condition means: either venue, latitude and longitude are provided, or
        # the event has "online" tag
        location = (
            ~Q(event__venue="")
            & Q(event__latitude__isnull=False)
            & Q(event__longitude__isnull=False)
        ) | Q(event__tags__name="online")

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

    def get_view_enabled(self) -> bool:
        try:
            role = CommunityRole.objects.get(
                person=self.request.user, config__name="instructor"
            )
            return role.is_active() and super().get_view_enabled()
        except CommunityRole.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # person details with tasks counted
        context["person"] = (
            Person.objects.annotate_with_role_count()
            .select_related("airport")
            .get(pk=self.request.user.pk)
        )
        context["person_instructor_tasks_slugs"] = Task.objects.filter(
            role__name="instructor", person__pk=self.request.user.pk
        ).values_list("event__slug", flat=True)

        context["person_instructor_task_events"] = {
            task.event
            for task in Task.objects.filter(
                role__name="instructor", person__pk=self.request.user.pk
            ).select_related("event")
        }

        context["person_signups"] = InstructorRecruitmentSignup.objects.filter(
            person=self.request.user
        ).select_related("recruitment", "recruitment__event")

        return context


class SignupForRecruitment(
    LoginRequiredMixin,
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    AMYCreateAndFetchObjectView,
):
    permission_required = [
        "recruitment.view_instructorrecruitment",
        "recruitment.add_instructorrecruitmentsignup",
    ]
    title = "Signup for workshop"
    model = InstructorRecruitmentSignup
    queryset_other = InstructorRecruitment.objects.filter(status="o").select_related(
        "event"
    )
    context_other_object_name = "recruitment"
    pk_url_kwarg = "recruitment_pk"

    form_class = SignupForRecruitmentForm
    template_name = "dashboard/signup_for_recruitment.html"

    def get_view_enabled(self) -> bool:
        try:
            role = CommunityRole.objects.get(
                person=self.request.user, config__name="instructor"
            )
            return role.is_active() and super().get_view_enabled()
        except CommunityRole.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        self.other_object: InstructorRecruitment
        event = self.other_object.event

        context = super().get_context_data(**kwargs)
        context["title"] = f"Signup for workshop {event}"

        # person details with tasks counted
        context["person"] = (
            Person.objects.annotate_with_role_count()
            .select_related("airport")
            .get(pk=self.request.user.pk)
        )

        return context

    def get_success_message(self, cleaned_data):
        self.other_object: InstructorRecruitment
        event = self.other_object.event
        return (
            f"Your interest in teaching at {event} has been recorded and is now "
            "pending."
        )

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
        if conflicting_signups := InstructorRecruitmentSignup.objects.exclude(
            recruitment=recruitment
        ).filter(
            person=self.request.user,
            recruitment__event__start__lte=event.end,
            recruitment__event__end__gte=event.start,
        ):
            gen = (signup.recruitment.event.slug for signup in conflicting_signups)
            messages.warning(
                self.request,
                "You have applied to other workshops on the same dates: "
                f"{', '.join(gen)}",
            )

        return super().form_valid(form)


class ResignFromRecruitment(
    LoginRequiredMixin,
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    SingleObjectMixin,
    View,
):
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

    def get_view_enabled(self) -> bool:
        try:
            role = CommunityRole.objects.get(
                person=self.request.user, config__name="instructor"
            )
            return role.is_active() and super().get_view_enabled()
        except CommunityRole.DoesNotExist:
            return False

    def get_queryset(self):
        return InstructorRecruitmentSignup.objects.filter(
            person=self.request.user, recruitment__status="o"
        )

    def get_redirect_url(self) -> str:
        next_url = self.request.POST.get("next", None)
        return safe_next_or_default_url(next_url, self.default_redirect_url)


# ------------------------------------------------------------


@require_GET
@admin_required
def search(request):
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
            tokens = re.split(r"\s+", term)
            results_combined = []

            organizations = list(
                Organization.objects.filter(
                    Q(domain__icontains=term) | Q(fullname__icontains=term)
                ).order_by("fullname")
            )
            results_combined += organizations

            memberships = list(
                Membership.objects.filter(
                    Q(name__icontains=term) | Q(registration_code__icontains=term)
                ).order_by("-agreement_start")
            )
            results_combined += memberships

            events = list(
                Event.objects.filter(
                    Q(slug__icontains=term)
                    | Q(host__domain__icontains=term)
                    | Q(host__fullname__icontains=term)
                    | Q(url__icontains=term)
                    | Q(contact__icontains=term)
                    | Q(venue__icontains=term)
                    | Q(address__icontains=term)
                ).order_by("-slug")
            )
            results_combined += events

            # if user searches for two words, assume they mean a person
            # name
            if len(tokens) == 2:
                name1, name2 = tokens
                complex_q = (
                    (Q(personal__icontains=name1) & Q(family__icontains=name2))
                    | (Q(personal__icontains=name2) & Q(family__icontains=name1))
                    | Q(email__icontains=term)
                    | Q(secondary_email__icontains=term)
                    | Q(github__icontains=term)
                )
                persons = list(Person.objects.filter(complex_q).order_by("family"))
            else:
                persons = list(
                    Person.objects.filter(
                        Q(personal__icontains=term)
                        | Q(family__icontains=term)
                        | Q(email__icontains=term)
                        | Q(secondary_email__icontains=term)
                        | Q(github__icontains=term)
                    ).order_by("family")
                )

            results_combined += persons

            airports = list(
                Airport.objects.filter(
                    Q(iata__icontains=term) | Q(fullname__icontains=term)
                ).order_by("iata")
            )
            results_combined += airports

            if len(tokens) == 2:
                name1, name2 = tokens
                complex_q = (
                    Q(group_name__icontains=term)
                    | (Q(personal__icontains=name1) & Q(family__icontains=name2))
                    | (Q(personal__icontains=name2) & Q(family__icontains=name1))
                    | Q(email__icontains=term)
                    | Q(secondary_email__icontains=term)
                    | Q(github__icontains=term)
                    | Q(affiliation__icontains=term)
                    | Q(location__icontains=term)
                    | Q(user_notes__icontains=term)
                )
                training_requests = list(
                    TrainingRequest.objects.filter(complex_q).order_by("family")
                )

            else:
                training_requests = list(
                    TrainingRequest.objects.filter(
                        Q(group_name__icontains=term)
                        | Q(family__icontains=term)
                        | Q(email__icontains=term)
                        | Q(github__icontains=term)
                        | Q(affiliation__icontains=term)
                        | Q(location__icontains=term)
                        | Q(user_notes__icontains=term)
                    ).order_by("family")
                )

            results_combined += training_requests

            comments = list(
                Comment.objects.filter(
                    Q(comment__icontains=term)
                    | Q(user_name__icontains=term)
                    | Q(user_email__icontains=term)
                    | Q(user__personal__icontains=term)
                    | Q(user__family__icontains=term)
                    | Q(user__email__icontains=term)
                    | Q(user__github__icontains=term)
                ).prefetch_related("content_object")
            )
            results_combined += comments

            # only 1 record found? Let's move to it immediately
            if len(results_combined) == 1 and not form.cleaned_data["no_redirect"]:
                result = results_combined[0]
                msg = format_html(
                    "You were moved to this page, because your search <i>{}</i> "
                    "yields only this result.",
                    term,
                )
                if isinstance(result, Comment):
                    messages.success(request, msg)
                    return redirect(
                        result.content_object.get_absolute_url()
                        + "#c{}".format(result.id)
                    )
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
