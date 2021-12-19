from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin

from recruitment.forms import InstructorRecruitmentCreateForm
from workshops.base_views import (
    AMYCreateView,
    AMYDetailView,
    ConditionallyEnabledMixin,
    RedirectSupportMixin,
)
from workshops.models import Event
from workshops.util import OnlyForAdminsMixin, human_daterange

from .models import InstructorRecruitment

# ------------------------------------------------------------
# InstructorRecruitment related views


class InstructorRecruitmentCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    RedirectSupportMixin,
    ConditionallyEnabledMixin,
    AMYCreateView,
):
    permission_required = "recruitment.add_instructorrecruitment"
    model = InstructorRecruitment
    template_name = "recruitment/instructorrecruitment_add.html"
    form_class = InstructorRecruitmentCreateForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = None

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

    def get_view_enabled(self) -> bool:
        return settings.INSTRUCTOR_RECRUITMENT_ENABLED is True

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

    def form_valid(self, form):
        self.object: InstructorRecruitment = form.save(commit=False)
        self.object.event = self.event
        self.object.save()
        return super().form_valid(form)


class InstructorRecruitmentDetails(
    OnlyForAdminsMixin, ConditionallyEnabledMixin, AMYDetailView
):
    queryset = InstructorRecruitment.objects.all()
    context_object_name = "role"
    template_name = "recruitment/instructor_recruitment.html"

    def get_view_enabled(self) -> bool:
        return settings.INSTRUCTOR_RECRUITMENT_ENABLED is True

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["title"] = str(self.object)
        return context
