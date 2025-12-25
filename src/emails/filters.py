import django_filters

from src.emails.models import EmailTemplate, ScheduledEmail
from src.workshops.filters import AMYFilterSet


class EmailTemplateFilter(AMYFilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    signal = django_filters.CharFilter(lookup_expr="icontains")
    from_header = django_filters.CharFilter(lookup_expr="icontains")
    subject = django_filters.CharFilter(lookup_expr="icontains")
    body = django_filters.CharFilter(lookup_expr="icontains")

    order_by = django_filters.OrderingFilter(
        fields=(
            "name",
            "signal",
        ),
    )

    class Meta:
        model = EmailTemplate
        fields = [
            "name",
            "active",
            "signal",
            "from_header",
            "subject",
            "body",
        ]


class ScheduledEmailFilter(AMYFilterSet):
    name = django_filters.CharFilter(
        field_name="template__name",
        lookup_expr="icontains",
        label="Name",
    )
    subject = django_filters.CharFilter(lookup_expr="icontains")

    order_by = django_filters.OrderingFilter(
        fields=(
            "template__name",
            "state",
            "scheduled_at",
            "subject",
        ),
    )

    class Meta:
        model = ScheduledEmail
        fields = [
            "name",
            "state",
            "subject",
        ]
