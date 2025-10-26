from datetime import date
import logging
from typing import Any, Callable
from urllib.parse import unquote

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import View
from django.views.generic.edit import FormMixin, FormView
from flags.views import FlaggedViewMixin  # type: ignore[import-untyped]

from emails.actions.host_instructors_introduction import (
    host_instructors_introduction_strategy,
    run_host_instructors_introduction_strategy,
)
from emails.actions.instructor_confirmed_for_workshop import (
    instructor_confirmed_for_workshop_strategy,
    run_instructor_confirmed_for_workshop_strategy,
)
from emails.actions.instructor_declined_from_workshop import (
    instructor_declined_from_workshop_strategy,
    run_instructor_declined_from_workshop_strategy,
)
from emails.signals import admin_signs_instructor_up_for_workshop_signal
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
    AuthenticatedHttpRequest,
    RedirectSupportMixin,
)
from workshops.models import Event, Person, Role, Task
from workshops.utils.access import OnlyForAdminsMixin
from workshops.utils.urls import safe_next_or_default_url

from .models import InstructorRecruitment, InstructorRecruitmentSignup

logger = logging.getLogger("amy")


# ------------------------------------------------------------
# InstructorRecruitment related views


class InstructorRecruitmentList(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYListView[InstructorRecruitment],
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.view_instructorrecruitment"
    title = "Recruitment processes"
    filter_class = InstructorRecruitmentFilter
    request: AuthenticatedHttpRequest

    queryset = (
        InstructorRecruitment.objects.annotate_with_priority()
        .select_related("event", "assigned_to")
        .prefetch_related(
            Prefetch(
                "signups",
                queryset=(
                    InstructorRecruitmentSignup.objects.select_related("recruitment", "person").annotate(
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

    def get_filter_data(self) -> QueryDict | dict[str, Any]:
        """If no filter value present for `assigned_to`, set default to current user.

        This means that by default the filter will be set to currently logged-in user;
        it's still possible to clear that filter value, in which case the query param
        will become `?assigned_to=` (empty)."""
        data = super().get_filter_data().copy()
        data.setdefault("assigned_to", str(self.request.user.pk))
        return data

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["personal_conflicts"] = (
            Person.objects.filter(instructorrecruitmentsignup__recruitment__in=self.get_queryset())
            .distinct()
            .prefetch_related(
                Prefetch(
                    "task_set",
                    Task.objects.select_related("event", "role").filter(role__name="instructor"),
                )
            )
        )
        return context


class InstructorRecruitmentCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    RedirectSupportMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYCreateView[InstructorRecruitmentCreateForm, InstructorRecruitment],
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.add_instructorrecruitment"
    model = InstructorRecruitment
    template_name = "recruitment/instructorrecruitment_add.html"
    form_class = InstructorRecruitmentCreateForm
    request: AuthenticatedHttpRequest

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.event: Event

    def get_other_object(self) -> Event:
        event_id = self.kwargs.get("event_id")
        today = date.today()

        # this condition means: either venue, latitude and longitude are provided, or
        # the event has "online" tag
        location = (~Q(venue="") & Q(latitude__isnull=False) & Q(longitude__isnull=False)) | Q(tags__name="online")
        qs = Event.objects.filter(start__gte=today).filter(location).select_related("administrator").distinct()
        return get_object_or_404(qs, pk=event_id)

    def get(
        self,
        request: AuthenticatedHttpRequest,  # type: ignore[override]
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Load other object upon GET request. Save the request."""
        self.request = request
        self.event = self.get_other_object()
        return super().get(request, *args, **kwargs)

    def post(
        self,
        request: AuthenticatedHttpRequest,  # type: ignore[override]
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Load other object upon POST request. Save the request."""
        self.request = request
        self.event = self.get_other_object()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "instructorrecruitment"})
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f"Begin Instructor Selection Process for {self.event}"
        context["event"] = self.event
        context["event_dates"] = self.event.human_readable_date(common_month_left=r"%B %d", separator="-")
        context["priority"] = InstructorRecruitment.calculate_priority(self.event)
        return context

    def get_initial(self) -> dict[str, Any]:
        try:
            workshop_request = self.event.workshoprequest
            return {"notes": (f"{workshop_request.audience_description}\n\n" f"{workshop_request.user_notes}")}
        except Event.workshoprequest.RelatedObjectDoesNotExist:
            return {}

    def form_valid(self, form: InstructorRecruitmentCreateForm) -> HttpResponse:
        self.object: InstructorRecruitment = form.save(commit=False)
        self.object.assigned_to = self.request.user
        self.object.event = self.event
        self.object.save()
        return super().form_valid(form)


class InstructorRecruitmentDetails(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYDetailView[InstructorRecruitment],
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.view_instructorrecruitment"
    queryset = (
        InstructorRecruitment.objects.annotate_with_priority()
        .prefetch_related(
            Prefetch(
                "signups",
                queryset=(
                    InstructorRecruitmentSignup.objects.select_related("recruitment", "person").annotate(
                        num_instructor=Count(
                            Case(
                                When(person__task__role__name="instructor", then=Value(1)),
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

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class InstructorRecruitmentAddSignup(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    SuccessMessageMixin[InstructorRecruitmentAddSignupForm],
    PermissionRequiredMixin,
    FormView[InstructorRecruitmentAddSignupForm],
):
    """POST requests for adding new signup for an existing recruitment."""

    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = [
        "recruitment.change_instructorrecruitment",
        "recruitment.view_instructorrecruitmentsignup",
    ]
    form_class = InstructorRecruitmentAddSignupForm
    template_name = "recruitment/instructorrecruitment_add_signup.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
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

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["recruitment"] = self.object
        return kwargs

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

    def get(
        self,
        request: AuthenticatedHttpRequest,  # type: ignore[override]
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        self.request = request
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(
        self,
        request: AuthenticatedHttpRequest,  # type: ignore[override]
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        self.request = request
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


class InstructorRecruitmentSignupChangeState(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    FormMixin[InstructorRecruitmentSignupChangeStateForm],
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

    def form_invalid(self, form: InstructorRecruitmentSignupChangeStateForm) -> HttpResponse:
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form: InstructorRecruitmentSignupChangeStateForm) -> HttpResponse:
        action_to_state_mapping = {
            "confirm": "a",
            "decline": "d",
        }
        self.object.state = action_to_state_mapping[form.cleaned_data["action"]]
        self.object.save()

        state_to_method_action_mapping: dict[
            str,
            Callable[[HttpRequest, InstructorRecruitmentSignup, Person, Event], Task | None],
        ] = {
            "a": self.accept_signup,
            "d": self.decline_signup,
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
        except IntegrityError as exc:
            logger.error(f"{exc}")
            messages.error(
                self.request,
                "Unable to create or remove instructor task due to database error.",
            )
            return HttpResponseRedirect(self.get_success_url())

    def accept_signup(
        self,
        request: HttpRequest,
        signup: InstructorRecruitmentSignup,
        person: Person,
        event: Event,
    ) -> Task:
        role = Role.objects.get(name="instructor")
        task, created = Task.objects.get_or_create(
            event=event,
            person=person,
            role=role,
        )
        if not created:
            messages.warning(
                request,
                format_html(
                    "The signup was accepted, but instructor task already " '<a href="{}">exists</a>.',
                    task.get_absolute_url(),
                ),
            )

        run_instructor_confirmed_for_workshop_strategy(
            instructor_confirmed_for_workshop_strategy(signup),
            request,
            signup=signup,
            person_id=person.pk,
            event_id=event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )
        run_instructor_declined_from_workshop_strategy(
            instructor_declined_from_workshop_strategy(signup),
            request,
            signup=signup,
            person_id=person.pk,
            event_id=event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

        return task

    def decline_signup(
        self,
        request: HttpRequest,
        signup: InstructorRecruitmentSignup,
        person: Person,
        event: Event,
    ) -> None:
        try:
            task = Task.objects.get(role__name="instructor", person=person, event=event)
            messages.warning(
                request,
                format_html(
                    "The signup was declined, but instructor task was " '<a href="{}">found</a>. ',
                    task.get_absolute_url(),
                ),
            )
        except Task.DoesNotExist:
            pass

        run_instructor_confirmed_for_workshop_strategy(
            instructor_confirmed_for_workshop_strategy(signup),
            request,
            signup=signup,
            person_id=person.pk,
            event_id=event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )
        run_instructor_declined_from_workshop_strategy(
            instructor_declined_from_workshop_strategy(signup),
            request,
            signup=signup,
            person_id=person.pk,
            event_id=event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

    def post(self, request: AuthenticatedHttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.request = request
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class InstructorRecruitmentChangeState(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    FormMixin[InstructorRecruitmentChangeStateForm],
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
            messages.success(self.request, f"Successfully re-opened recruitment {self.object}.")

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

    def post(self, request: AuthenticatedHttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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
    FlaggedViewMixin,  # type: ignore[misc]
    AMYUpdateView[InstructorRecruitmentSignupUpdateForm, InstructorRecruitmentSignup],
):
    flag_name = "INSTRUCTOR_RECRUITMENT"
    permission_required = "recruitment.change_instructorrecruitmentsignup"
    form_class = InstructorRecruitmentSignupUpdateForm
    model = InstructorRecruitmentSignup

    def get_success_url(self) -> str:
        return reverse("all_instructorrecruitment")
