from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, IntegerField, Prefetch, Sum, When
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from trainings.filters import TraineeFilter
from trainings.forms import BulkAddTrainingProgressForm, TrainingProgressForm
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYListView,
    AMYUpdateView,
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


class AllTrainings(OnlyForAdminsMixin, AMYListView):
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
    RedirectSupportMixin, PrepopulationSupportMixin, OnlyForAdminsMixin, AMYCreateView
):
    model = TrainingProgress
    form_class = TrainingProgressForm
    populate_fields = ["trainee"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"].helper = context["form"].create_helper
        return context


class TrainingProgressUpdate(RedirectSupportMixin, OnlyForAdminsMixin, AMYUpdateView):
    model = TrainingProgress
    form_class = TrainingProgressForm
    template_name = "trainings/trainingprogress_form.html"


class TrainingProgressDelete(RedirectSupportMixin, OnlyForAdminsMixin, AMYDeleteView):
    model = TrainingProgress
    success_url = reverse_lazy("all_trainees")


def all_trainees_queryset():
    return (
        Person.objects.annotate_with_instructor_eligibility()
        .prefetch_related(
            Prefetch(
                "task_set",
                to_attr="training_tasks",
                queryset=Task.objects.filter(
                    role__name="learner", event__tags__name="TTT"
                ),
            ),
            "training_tasks__event",
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
def all_trainees(request):
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
                    progress = TrainingProgress(
                        trainee=trainee,
                        requirement=form.cleaned_data["requirement"],
                        involvement_type=form.cleaned_data["involvement_type"],
                        state=form.cleaned_data["state"],
                        event=form.cleaned_data["event"],
                        url=form.cleaned_data["url"],
                        date=form.cleaned_data["date"],
                        notes=form.cleaned_data["notes"],
                    )
                    progress.full_clean()
                    progress.save()
                except ValidationError as e:
                    errors.append(e)

            if len(errors) > 0:
                # build a user-friendly error set
                for e in errors:
                    for k, v in e.error_dict.items():
                        for field_error in v:
                            error_list = " ".join(
                                [f.message for f in field_error.error_list]
                            )
                            msg = f"{form.fields[k].label}: {error_list}"
                            messages.error(request, msg)

                changed_count = len(form.cleaned_data["trainees"]) - len(errors)
                info_msg = (
                    f"Changed progress of {changed_count} trainee(s). "
                    f"{len(errors)} trainee(s) were skipped due to errors."
                )
                messages.info(request, info_msg)
            else:
                messages.success(
                    request, "Successfully changed progress of all selected trainees."
                )

            return redirect(request.get_raw_uri())

    else:  # GET request
        # If the user filters by training, we want to set initial values for
        # "requirement" and "training" fields.
        training_id = request.GET.get("training", None) or None
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
