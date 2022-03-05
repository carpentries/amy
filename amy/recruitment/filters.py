import django_filters

from workshops.fields import ModelSelect2Widget
from workshops.filters import AMYFilterSet
from workshops.forms import SELECT2_SIDEBAR
from workshops.models import Person

from .models import InstructorRecruitment


class InstructorRecruitmentFilter(AMYFilterSet):
    assigned_to = django_filters.ModelChoiceFilter(
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="admin-lookup", attrs=SELECT2_SIDEBAR),
    )

    class Meta:
        model = InstructorRecruitment
        fields = [
            "assigned_to",
            "status",
        ]
