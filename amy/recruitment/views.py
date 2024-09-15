from datetime import date
import logging
from typing import Callable
from urllib.parse import unquote

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import View
from django.views.generic.edit import FormMixin, FormView
import django_rq
from flags.views import FlaggedViewMixin

from emails.actions.host_instructors_introduction import (
    host_instructors_introduction_strategy,
    run_host_instructors_introduction_strategy,
)
from emails.signals import (
    admin_signs_instructor_up_for_workshop_signal,
    instructor_confirmed_for_workshop_signal,
    instructor_declined_from_workshop_signal,
)
from recruitment.filters import InstructorRecruitmentFilter
from recruitment.forms import (
    InstructorRecruitmentAddSignupForm,
    InstructorRecruitmentChangeStateForm,
    InstructorRecruitmentCreateForm,
    InstructorRecruitmentSignupChangeStateForm,
    InstructorRecruitmentSignupUpdateForm,
)
from workshops.base_views import (
    AMYCreateView,
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
    RedirectSupportMixin,
)
from workshops.models import Event, Person, Role, Task
from workshops.utils.access import OnlyForAdminsMixin
from workshops.utils.urls import safe_next_or_default_url

from .models import InstructorRecruitment, InstructorRecruitmentSignup

logger = logging.getLogger("amy")
scheduler = django_rq.get_scheduler("default")
redis_connection = django_rq.get_connection("default")


# ------------------------------------------------------------
# InstructorRecruitment related views


class InstructorRecruitmentList(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.view_instructorrecruitment"
    title = "Recruitment processes"
    filter_class = InstructorRecruitmentFilter

    queryset = (
        InstructorRecruitment.objects.annotate_with_priority()
        .select_related("event", "assigned_to")
        .prefetch_related(
            Prefetch(
                "signups",
                queryset=(
                    InstructorRecruitmentSignup.objects.select_related(
                        "recruitment", "person"
                    ).annotate(
                        num_instructor=Count(
                            Case(
                                When(
                                    person__task__role__name="instructor",
                                    then=Value(1),
                                ),
                                output_field=IntegerField(),
                            )
                        ),
                        num_supporting=Count(
                            Case(
                                When(
                                    person__task__role__name="supporting-instructor",
                                    then=Value(1),
                                ),
                                output_field=IntegerField(),
                            )
                        ),
                        num_helper=Count(
                            Case(
                                When(
                                    person__task__role__name="helper",
                                    then=Value(1),
                                ),
                                output_field=IntegerField(),
                            )
                        ),
                    )
                ),
            )
        )
        .annotate(
            num_pending=Count(
                Case(
                    When(
                        signups__state="p",
                        then=Value(1),
                    ),
                    output_field=IntegerField(),
                )
            )
        )
        .order_by("-created_at")
    )
    template_name = "recruitment/instructorrecruitment_list.html"

    def get_filter_data(self):
        """If no filter value present for `assigned_to`, set default to current user.

        This means that by default the filter will be set to currently logged-in user;
        it's still possible to clear that filter value, in which case the query param
        will become `?assigned_to=` (empty)."""
        data = super().get_filter_data().copy()
        data.setdefault("assigned_to", self.request.user.pk)
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["personal_conflicts"] = (
            Person.objects.filter(
                instructorrecruitmentsignup__recruitment__in=self.get_queryset()
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    "task_set",
                    Task.objects.select_related("event", "role").filter(
                        role__name="instructor"
                    ),
                )
            )
        )
        return context


class InstructorRecruitmentCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    RedirectSupportMixin,
    FlaggedViewMixin,
    AMYCreateView,
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.add_instructorrecruitment"
    model = InstructorRecruitment
    template_name = "recruitment/instructorrecruitment_add.html"
    form_class = InstructorRecruitmentCreateForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event: Event

    def get_other_object(self) -> Event:
        event_id = self.kwargs.get("event_id")
        today = date.today()

        # this condition means: either venue, latitude and longitude are provided, or
        # the event has "online" tag
        location = (
            ~Q(venue="") & Q(latitude__isnull=False) & Q(longitude__isnull=False)
        ) | Q(tags__name="online")
        qs = (
            Event.objects.filter(start__gte=today)
            .filter(location)
            .select_related("administrator")
            .distinct()
        )
        return get_object_or_404(qs, pk=event_id)

    def get(self, request, *args, **kwargs):
        """Load other object upon GET request. Save the request."""
        self.request = request
        self.event = self.get_other_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Load other object upon POST request. Save the request."""
        self.request = request
        self.event = self.get_other_object()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "instructorrecruitment"})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Begin Instructor Selection Process for {self.event}"
        context["event"] = self.event
        context["event_dates"] = self.event.human_readable_date(
            common_month_left=r"%B %d", separator="-"
        )
        context["priority"] = InstructorRecruitment.calculate_priority(self.event)
        return context

    def get_initial(self) -> dict:
        try:
            workshop_request = self.event.workshoprequest
            return {
                "notes": (
                    f"{workshop_request.audience_description}\n\n"
                    f"{workshop_request.user_notes}"
                )
            }
        except Event.workshoprequest.RelatedObjectDoesNotExist:
            return {}

    def form_valid(self, form: InstructorRecruitmentCreateForm):
        self.object: InstructorRecruitment = form.save(commit=False)
        self.object.assigned_to = self.request.user
        self.object.event = self.event
        self.object.save()
        return super().form_valid(form)


class InstructorRecruitmentDetails(
    OnlyForAdminsMixin,
    FlaggedViewMixin,
    AMYDetailView,
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.view_instructorrecruitment"
    queryset = (
        InstructorRecruitment.objects.annotate_with_priority()
        .prefetch_related(
            Prefetch(
                "signups",
                queryset=(
                    InstructorRecruitmentSignup.objects.select_related(
                        "recruitment", "person"
                    ).annotate(
                        num_instructor=Count(
                            Case(
                                When(
                                    person__task__role__name="instructor", then=Value(1)
                                ),
                                output_field=IntegerField(),
                            )
                        ),
                        num_supporting=Count(
                            Case(
                                When(
                                    person__task__role__name="supporting-instructor",
                                    then=Value(1),
                                ),
                                output_field=IntegerField(),
                            )
                        ),
                        num_helper=Count(
                            Case(
                                When(person__task__role__name="helper", then=Value(1)),
                                output_field=IntegerField(),
                            )
                        ),
                    )
                ),
            )
        )
        .annotate(
            num_pending=Count(
                Case(
                    When(
                        signups__state="p",
                        then=Value(1),
                    ),
                    output_field=IntegerField(),
                )
            )
        )
    )
    template_name = "recruitment/instructorrecruitment_details.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class InstructorRecruitmentAddSignup(
    OnlyForAdminsMixin,
    FlaggedViewMixin,
    SuccessMessageMixin,
    PermissionRequiredMixin,
    FormView,
):
    """POST requests for adding new signup for an existing recruitment."""

    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = [
        "recruitment.change_instructorrecruitment",
        "recruitment.view_instructorrecruitmentsignup",
    ]
    form_class = InstructorRecruitmentAddSignupForm
    template_name = "recruitment/instructorrecruitment_add_signup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Add instructor application to {self.object}"
        return context

    def get_object(self) -> InstructorRecruitment:
        return InstructorRecruitment.objects.get(pk=self.kwargs["pk"])

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next", None)
        if next_url:
            next_url = unquote(next_url)
        default_url = reverse("all_instructorrecruitment")
        return safe_next_or_default_url(next_url, default_url)

    def get_success_message(self, cleaned_data: dict[str, str]) -> str:
        return f"Added {cleaned_data['person']} to {self.object}"

    def form_valid(self, form: InstructorRecruitmentAddSignupForm) -> HttpResponse:
        signup: InstructorRecruitmentSignup = form.save(commit=False)
        signup.recruitment = self.object
        signup.save()

        admin_signs_instructor_up_for_workshop_signal.send(
            sender=signup,
            request=self.request,
            person_id=signup.person.pk,
            event_id=signup.recruitment.event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        self.request = request
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.request = request
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


class InstructorRecruitmentSignupChangeState(
    OnlyForAdminsMixin,
    FlaggedViewMixin,
    FormMixin,
    PermissionRequiredMixin,
    View,
):
    """POST requests for editing (confirming or declining) the instructor signup."""

    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.change_instructorrecruitmentsignup"
    form_class = InstructorRecruitmentSignupChangeStateForm

    def get_object(self) -> InstructorRecruitmentSignup:
        return InstructorRecruitmentSignup.objects.get(pk=self.kwargs["pk"])

    def get_success_url(self) -> str:
        next_url = self.request.POST.get("next", None)
        default_url = reverse("all_instructorrecruitment")
        return safe_next_or_default_url(next_url, default_url)

    def form_invalid(self, form) -> HttpResponse:
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form) -> HttpResponse:
        action_to_state_mapping = {
            "confirm": "a",
            "decline": "d",
        }
        self.object.state = action_to_state_mapping[form.cleaned_data["action"]]
        self.object.save()

        state_to_method_action_mapping: dict[
            str,
            Callable[
                [HttpRequest, InstructorRecruitmentSignup, Person, Event], Task | None
            ],
        ] = {
            "a": self.add_instructor_task,
            "d": self.remove_instructor_task,
        }
        handler = state_to_method_action_mapping[self.object.state]
        try:
            handler(
                self.request,
                self.object,
                self.object.person,
                self.object.recruitment.event,
            )
            return super().form_valid(form)
        except IntegrityError:
            messages.error(
                self.request,
                "Unable to create or remove instructor task due to database error.",
            )
            return HttpResponseRedirect(self.get_success_url())

    def add_instructor_task(
        self,
        request: HttpRequest,
        signup: InstructorRecruitmentSignup,
        person: Person,
        event: Event,
    ) -> Task:
        role = Role.objects.get(name="instructor")
        task = Task.objects.create(
            event=event,
            person=person,
            role=role,
        )

        # Note: there's a strategy for this email, but this case may be simple enough
        # that we don't need to use it.
        instructor_confirmed_for_workshop_signal.send(
            sender=signup,
            request=request,
            person_id=person.pk,
            event_id=event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

        return task

    def remove_instructor_task(
        self,
        request: HttpRequest,
        signup: InstructorRecruitmentSignup,
        person: Person,
        event: Event,
    ) -> None:
        """Remove instructor task from a Person only if the task exists. If it doesn't,
        don't throw errors."""
        try:
            task = Task.objects.get(role__name="instructor", person=person, event=event)
        except Task.DoesNotExist:
            pass
        else:
            task.delete()

        instructor_declined_from_workshop_signal.send(
            sender=signup,
            request=request,
            person_id=person.pk,
            event_id=event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

    def post(self, request, *args, **kwargs):
        self.request = request
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class InstructorRecruitmentChangeState(
    OnlyForAdminsMixin,
    FlaggedViewMixin,
    FormMixin,
    PermissionRequiredMixin,
    View,
):
    """POST requests for editing (e.g. closing) the instructor recruitment."""

    flag_name = "INSTRUCTOR_RECRUITMENT"
    form_class = InstructorRecruitmentChangeStateForm
    permission_required = "recruitment.change_instructorrecruitment"

    def get_object(self) -> InstructorRecruitment:
        return InstructorRecruitment.objects.annotate(
            num_pending=Count(
                Case(
                    When(
                        signups__state="p",
                        then=Value(1),
                    ),
                    output_field=IntegerField(),
                )
            )
        ).get(pk=self.kwargs["pk"])

    def get_success_url(self) -> str:
        next_url = self.request.POST.get("next", None)
        default_url = reverse("all_instructorrecruitment")
        return safe_next_or_default_url(next_url, default_url)

    @staticmethod
    def _validate_for_closing(recruitment: InstructorRecruitment) -> bool:
        if getattr(recruitment, "num_pending", 1) != 0:
            return False
        if recruitment.status != "o":
            return False
        return True

    def close_recruitment(self) -> HttpResponse:
        if not self._validate_for_closing(self.object):
            messages.error(
                self.request,
                "Unable to close recruitment.",
            )

        else:
            self.object.status = "c"
            self.object.save()
            messages.success(
                self.request,
                f"Successfully closed recruitment {self.object}.",
            )

            run_host_instructors_introduction_strategy(
                host_instructors_introduction_strategy(self.object.event),
                self.request,
                self.object.event,
            )

        return HttpResponseRedirect(self.get_success_url())

    @staticmethod
    def _validate_for_reopening(recruitment: InstructorRecruitment) -> bool:
        if recruitment.status != "c":
            return False
        return True

    def reopen_recruitment(self) -> HttpResponse:
        if not self._validate_for_reopening(self.object):
            messages.error(
                self.request,
                "Unable to re-open recruitment.",
            )

        else:
            self.object.status = "o"
            self.object.save()
            messages.success(
                self.request, f"Successfully re-opened recruitment {self.object}."
            )

            run_host_instructors_introduction_strategy(
                host_instructors_introduction_strategy(self.object.event),
                self.request,
                self.object.event,
            )

        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form: BaseForm) -> HttpResponse:
        action = form.cleaned_data["action"]

        action_handler_mapping = {
            "close": self.close_recruitment,
            "reopen": self.reopen_recruitment,
        }

        return action_handler_mapping[action]()

    def form_invalid(self, form: BaseForm) -> HttpResponse:
        messages.error(self.request, "Please choose correct action.")
        # Note: there's not really a place to redirect user to... So worst-case scenario
        # they will be redirected to the success URL.
        referrer = self.request.headers.get("Referer", self.get_success_url())
        next_url = self.request.POST.get("next", None)
        return HttpResponseRedirect(safe_next_or_default_url(next_url, referrer))

    def post(self, request, *args, **kwargs) -> HttpResponse:
        self.request = request
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class InstructorRecruitmentSignupUpdate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    RedirectSupportMixin,
    FlaggedViewMixin,
    AMYUpdateView,
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.change_instructorrecruitmentsignup"
    form_class = InstructorRecruitmentSignupUpdateForm
    model = InstructorRecruitmentSignup

    def get_success_url(self):
        return reverse("all_instructorrecruitment")
