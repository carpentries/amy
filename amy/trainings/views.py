from typing import Any

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, IntegerField, Prefetch, QuerySet, Sum, When
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from emails.actions.exceptions import EmailStrategyException
from emails.actions.instructor_training_completed_not_badged import (
    instructor_training_completed_not_badged_strategy,
    run_instructor_training_completed_not_badged_strategy,
)
from trainings.filters import TraineeFilter
from trainings.forms import BulkAddTrainingProgressForm, TrainingProgressForm
from trainings.utils import raise_validation_error_if_no_learner_task
from workshops.base_forms import GenericDeleteForm
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYListView,
    AMYUpdateView,
    AuthenticatedHttpRequest,
    PrepopulationSupportMixin,
    RedirectSupportMixin,
)
from workshops.models import (
    Badge,
    Event,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)
from workshops.utils.access import OnlyForAdminsMixin, admin_required
from workshops.utils.pagination import get_pagination_items


class AllTrainings(OnlyForAdminsMixin, AMYListView[Event]):
    context_object_name = "all_trainings"
    template_name = "trainings/all_trainings.html"
    queryset = (
        Event.objects.filter(tags__name="TTT")
        .annotate(
            trainees=Count(
                Case(
                    When(task__role__name="learner", then=F("task__person__id")),
                    output_field=IntegerField(),
                ),
                distinct=True,
            ),
            finished=Count(
                Case(
                    When(
                        task__role__name="learner",
                        task__person__badges__in=Badge.objects.instructor_badges(),
                        then=F("task__person__id"),
                    ),
                    output_field=IntegerField(),
                ),
                distinct=True,
            ),
        )
        .exclude(trainees=0)
        .order_by("-start")
    )
    title = "All Instructor Trainings"


# ------------------------------------------------------------
# Instructor Training related views


class TrainingProgressCreate(
    RedirectSupportMixin,
    PrepopulationSupportMixin[TrainingProgressForm],
    OnlyForAdminsMixin,
    AMYCreateView[TrainingProgressForm, TrainingProgress],
):
    model = TrainingProgress
    form_class = TrainingProgressForm
    populate_fields = ["trainee"]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["form"].helper = context["form"].create_helper
        return context

    def form_valid(self, form: TrainingProgressForm) -> HttpResponse:
        person = form.cleaned_data["trainee"]
        event = form.cleaned_data["event"]
        result = super().form_valid(form)
        try:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(person),
                request=self.request,
                person=person,
                training_completed_date=event.end if event else None,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when running instructor training completed strategy. {exc}",
            )
        return result


class TrainingProgressUpdate(
    RedirectSupportMixin, OnlyForAdminsMixin, AMYUpdateView[TrainingProgressForm, TrainingProgress]
):
    model = TrainingProgress
    form_class = TrainingProgressForm
    template_name = "trainings/trainingprogress_form.html"

    def form_valid(self, form: TrainingProgressForm) -> HttpResponse:
        person = form.cleaned_data["trainee"]
        event = form.cleaned_data["event"]
        result = super().form_valid(form)
        try:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(person),
                request=self.request,
                person=person,
                training_completed_date=event.end if event else None,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when creating or updating scheduled email. {exc}",
            )
        return result


class TrainingProgressDelete(
    RedirectSupportMixin, OnlyForAdminsMixin, AMYDeleteView[TrainingProgress, GenericDeleteForm[TrainingProgress]]
):
    model = TrainingProgress
    success_url = reverse_lazy("all_trainees")
    object: TrainingProgress

    def before_delete(self, *args: Any, **kwargs: Any) -> None:
        """Save for use in `after_delete` method."""
        self._person = self.object.trainee
        self._event = self.object.event

    def after_delete(self, *args: Any, **kwargs: Any) -> None:
        person = self._person
        event = self._event
        try:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(person),
                request=self.request,
                person=person,
                training_completed_date=event.end if event else None,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when running instructor training completed strategy. {exc}",
            )


def all_trainees_queryset() -> QuerySet[Person]:
    return (
        Person.objects.annotate_with_instructor_eligibility()
        .prefetch_related(
            Prefetch(
                "task_set",
                to_attr="training_tasks",
                queryset=Task.objects.filter(role__name="learner", event__tags__name="TTT").select_related("event"),
            ),
            "trainingrequest_set",
            "trainingprogress_set",
            "trainingprogress_set__requirement",
        )
        .annotate(
            is_instructor=Sum(
                Case(
                    When(badges__name=Badge.SINGLE_INSTRUCTOR_BADGE, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
        )
        .order_by("family", "personal")
    )


@admin_required
def all_trainees(request: AuthenticatedHttpRequest) -> HttpResponse:
    filter = TraineeFilter(
        request.GET,
        queryset=all_trainees_queryset(),
    )
    trainees = get_pagination_items(request, filter.qs)

    if request.method == "POST":
        # Bulk add progress to selected trainees
        form = BulkAddTrainingProgressForm(request.POST)
        if form.is_valid():
            errors = []
            for trainee in form.cleaned_data["trainees"]:
                try:
                    event = form.cleaned_data["event"]
                    raise_validation_error_if_no_learner_task(trainee, event)
                    progress = TrainingProgress(
                        trainee=trainee,
                        requirement=form.cleaned_data["requirement"],
                        involvement_type=form.cleaned_data["involvement_type"],
                        state=form.cleaned_data["state"],
                        event=event,
                        url=form.cleaned_data["url"],
                        date=form.cleaned_data["date"],
                        notes=form.cleaned_data["notes"],
                    )
                    progress.full_clean()
                    progress.save()

                    try:
                        run_instructor_training_completed_not_badged_strategy(
                            instructor_training_completed_not_badged_strategy(trainee),
                            request=request,
                            person=trainee,
                            training_completed_date=event.end if event else None,
                        )
                    except EmailStrategyException as exc:
                        messages.error(
                            request,
                            "Error when running instructor training completed strategy." f" {exc}",
                        )

                except ValidationError as e:
                    unique_constraint_message = "Training progress with this Trainee " "and Training already exists."
                    if unique_constraint_message in e.messages:
                        msg = (
                            f"Trainee {trainee} already has a training progress "
                            f'for event {form.cleaned_data["event"]}.'
                        )
                        e.error_dict["__all__"].append(ValidationError(msg))
                    errors.append(e)

            if errors:
                # build a user-friendly error set
                for error in errors:
                    msg = " ".join(error.messages)
                    messages.error(request, msg)

                changed_count = len(form.cleaned_data["trainees"]) - len(errors)
                info_msg = (
                    f"Changed progress of {changed_count} trainee(s). "
                    f"{len(errors)} trainee(s) were skipped due to errors."
                )
                messages.info(request, info_msg)
            else:
                messages.success(request, "Successfully changed progress of all selected trainees.")

            return redirect(request.build_absolute_uri())

    else:  # GET request
        # If the user filters by training, we want to set initial values for
        # "requirement" and "training" fields.
        training_id = request.GET.get("training", 0) or 0
        try:
            initial = {
                "event": Event.objects.get(pk=training_id),
                "requirement": TrainingRequirement.objects.get(name="Training"),
            }
        except Event.DoesNotExist:  # or there is no `training` GET parameter
            initial = None

        form = BulkAddTrainingProgressForm(initial=initial)

    context = {
        "title": "Trainees",
        "all_trainees": trainees,
        "filter": filter,
        "form": form,
    }
    return render(request, "trainings/all_trainees.html", context)
