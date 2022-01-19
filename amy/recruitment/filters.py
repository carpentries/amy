from workshops.fields import Select2Widget
from workshops.filters import AMYFilterSet, ForeignKeyAllValuesFilter
from workshops.models import Person

from .models import InstructorRecruitment


class InstructorRecruitmentFilter(AMYFilterSet):
    assigned_to = ForeignKeyAllValuesFilter(Person, widget=Select2Widget)

    class Meta:
        model = InstructorRecruitment
        fields = [
            "assigned_to",
            "status",
        ]
