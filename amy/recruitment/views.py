import logging
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.db.models import Case, Count, IntegerField, Prefetch, Value, When
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View
from django.views.generic.edit import FormMixin, FormView
import django_rq

from autoemails.actions import (
    DeclinedInstructorsAction,
    InstructorsHostIntroductionAction,
    NewInstructorAction,
)
from autoemails.base_views import ActionManageMixin
from autoemails.job import Job
from autoemails.models import RQJob, Trigger
from autoemails.utils import safe_next_or_default_url
from recruitment.filters import InstructorRecruitmentFilter
from recruitment.forms import (
    InstructorRecruitmentAddSignupForm,
    InstructorRecruitmentCreateForm,
    InstructorRecruitmentSignupChangeStateForm,
)
from workshops.base_views import (
    AMYCreateView,
    AMYDetailView,
    AMYListView,
    ConditionallyEnabledMixin,
    RedirectSupportMixin,
)
from workshops.models import Event, Person, Role, Task
from workshops.util import OnlyForAdminsMixin, human_daterange

from .models import InstructorRecruitment, InstructorRecruitmentSignup

logger = logging.getLogger("amy.signals")
scheduler = django_rq.get_scheduler("default")
redis_connection = django_rq.get_connection("default")


# ------------------------------------------------------------
# InstructorRecruitment related views


class RecruitmentEnabledMixin:
    def get_view_enabled(self) -> bool:
        return settings.INSTRUCTOR_RECRUITMENT_ENABLED is True


class InstructorRecruitmentList(
    OnlyForAdminsMixin, RecruitmentEnabledMixin, ConditionallyEnabledMixin, AMYListView
):
    permission_required = "recruitment.view_instructorrecruitment"
    title = "Recruitment processes"
    filter_class = InstructorRecruitmentFilter

    queryset = (
        InstructorRecruitment.objects.select_related("event", "assigned_to")
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
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    AMYCreateView,
):
    permission_required = "recruitment.add_instructorrecruitment"
    model = InstructorRecruitment
    template_name = "recruitment/instructorrecruitment_add.html"
    form_class = InstructorRecruitmentCreateForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event: Optional[Event] = None

    def get_other_object(self) -> Event:
        event_id = self.kwargs.get("event_id")
        return Event.objects.select_related("administrator").get(pk=event_id)

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
        context["event_dates"] = human_daterange(
            self.event.start, self.event.end, common_month_left=r"%B %d", range_char="-"
        )
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
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    AMYDetailView,
):
    permission_required = "recruitment.view_instructorrecruitment"
    queryset = InstructorRecruitment.objects.prefetch_related(
        Prefetch(
            "signups",
            queryset=(
                InstructorRecruitmentSignup.objects.select_related(
                    "recruitment", "person"
                ).annotate(
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
    ).annotate(
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
    template_name = "recruitment/instructorrecruitment_details.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context


class InstructorRecruitmentAddSignup(
    OnlyForAdminsMixin,
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    SuccessMessageMixin,
    PermissionRequiredMixin,
    FormView,
):
    """POST requests for adding new signup for an existing recruitment."""

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
        next_url = self.request.POST.get("next", None)
        default_url = reverse("all_instructorrecruitment")
        return safe_next_or_default_url(next_url, default_url)

    def get_success_message(self, cleaned_data: dict[str, str]) -> str:
        return f"Added {cleaned_data['person']} to {self.object}"

    def form_valid(self, form: InstructorRecruitmentAddSignupForm) -> HttpResponse:
        signup: InstructorRecruitmentSignup = form.save(commit=False)
        signup.recruitment = self.object
        signup.save()
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
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    FormMixin,
    PermissionRequiredMixin,
    View,
):
    """POST requests for editing (confirming or declining) the instructor signup."""

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

        state_to_method_action_mapping = {
            "a": self.add_instructor_task,
            "d": self.remove_instructor_task,
        }
        handler = state_to_method_action_mapping[self.object.state]
        try:
            handler(self.object.person, self.object.recruitment.event)
            return super().form_valid(form)
        except IntegrityError:
            messages.error(
                self.request,
                "Unable to create or remove instructor task due to database error.",
            )
            return HttpResponseRedirect(self.get_success_url())

    def add_instructor_task(self, person: Person, event: Event) -> Task:
        role = Role.objects.get(name="instructor")
        task = Task.objects.create(
            event=event,
            person=person,
            role=role,
        )
        self.add_automated_email(task)
        return task

    def remove_instructor_task(self, person: Person, event: Event) -> None:
        task = Task.objects.get(role__name="instructor", person=person, event=event)
        self.remove_automated_email(task)
        task.delete()

    def add_automated_email(self, task: Task) -> tuple[list[Job], list[RQJob]]:
        trigger_name = "new-instructor"
        triggers = Trigger.objects.filter(active=True, action=trigger_name)
        return ActionManageMixin.add(
            action_class=NewInstructorAction,
            logger=logger,
            scheduler=scheduler,
            triggers=triggers,
            context_objects=dict(task=task, event=task.event),
            object_=task,
            request=self.request,
        )

    def remove_automated_email(self, task: Task) -> None:
        trigger_name = "new-instructor"
        jobs = task.rq_jobs.filter(trigger__action=trigger_name).values_list(
            "job_id", flat=True
        )
        return ActionManageMixin.remove(
            action_class=NewInstructorAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs,
            object_=task,
            request=self.request,
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
    RecruitmentEnabledMixin,
    ConditionallyEnabledMixin,
    FormMixin,
    PermissionRequiredMixin,
    View,
):
    """POST requests for editing (e.g. closing) the instructor recruitment."""

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
            self.send_introduction_email(self.object.event, self.object)
            self.send_thank_you_to_declined(self.object)

        return HttpResponseRedirect(self.get_success_url())

    def send_introduction_email(
        self, event: Event, recruitment: InstructorRecruitment
    ) -> None:
        if InstructorsHostIntroductionAction.check(event):
            triggers = Trigger.objects.filter(
                active=True, action="instructors-host-introduction"
            )
            ActionManageMixin.add(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=event, recruitment=recruitment),
                object_=event,
                request=self.request,
            )
        else:
            messages.warning(
                self.request,
                "Instructors-Host introduction email was not sent due to "
                "unmet conditions.",
            )

    def send_thank_you_to_declined(self, recruitment: InstructorRecruitment) -> None:
        declined_instructor_signups = recruitment.signups.filter(state="d")
        triggers = Trigger.objects.filter(
            active=True, action=DeclinedInstructorsAction.trigger_name
        )

        for signup in declined_instructor_signups:
            if DeclinedInstructorsAction.check(signup):
                ActionManageMixin.add(
                    action_class=DeclinedInstructorsAction,
                    logger=logger,
                    scheduler=scheduler,
                    triggers=triggers,
                    context_objects=dict(
                        recruitment=recruitment,
                        event=recruitment.event,
                        person=signup.person,
                    ),
                    object_=signup,
                    request=self.request,
                )

    def post(self, request, *args, **kwargs) -> HttpResponse:
        self.request = request
        self.object = self.get_object()

        action = "close"
        # For future if we need to handle other actions
        action_handler_mapping = {
            "close": self.close_recruitment,
        }

        return action_handler_mapping[action]()
