from datetime import timedelta
from typing import Any, cast

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model, QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse

from extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from extrequests.utils import get_membership_or_none_from_code
from workshops.base_views import AMYCreateView
from workshops.models import Curriculum, Tag, WorkshopRequest


class WRFInitial:
    other_object: WorkshopRequest | WorkshopInquiryRequest | SelfOrganisedSubmission

    def get_initial(self) -> dict[str, Any]:
        curricula = Curriculum.objects.none()

        if hasattr(self.other_object, "workshop_types"):
            curricula = self.other_object.workshop_types.all()
        elif hasattr(self.other_object, "requested_workshop_types"):
            curricula = self.other_object.requested_workshop_types.all()

        tag_names = [C.carpentry for C in curricula if C.carpentry]
        if curricula.filter(mix_match=True).exists():
            tag_names.append("Circuits")
        if self.other_object.online_inperson == "online":
            tag_names.append("online")

        listed = self.other_object.workshop_listed
        if not listed:
            tag_names.append("private-event")

        initial: dict[str, Any] = {
            "public_status": "public" if listed else "private",
            "curricula": curricula,
            "tags": Tag.objects.filter(name__in=tag_names),
            "contact": self.other_object.additional_contact,
        }

        host = self.other_object.institution
        if host:
            initial["host"] = host

        start = None
        end = None
        if hasattr(self.other_object, "preferred_dates"):
            start = self.other_object.preferred_dates
            if start:
                end = start + timedelta(days=1)
        elif hasattr(self.other_object, "start"):
            start = self.other_object.start
            end = self.other_object.end

        if start:
            initial["start"] = start
        if end:
            initial["end"] = end

        if hasattr(self.other_object, "member_code"):
            code = self.other_object.member_code
            initial["membership"] = get_membership_or_none_from_code(code)

        return initial


class AMYCreateAndFetchObjectView[
    _M: Model,
    _M2: Model,
    _MF: BaseModelForm,  # type: ignore[type-arg]
](AMYCreateView[_MF, _M]):
    """AMY-based CreateView extended with fetching a different object based on
    URL parameter."""

    model_other: type[_M2] | None = None
    queryset_other: QuerySet[_M2] | None = None
    other_object: _M2 | None = None
    context_other_object_name = "other_object"

    pk_url_kwarg = "pk"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    query_pk_and_slug = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize some internal vars."""
        self.other_object = None
        super().__init__(*args, **kwargs)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Load other object upon GET request. Save the request."""
        if self.other_object is None:
            self.other_object = self.get_other_object()

        self.request = request
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Load other object upon POST request. Save the request."""
        if self.other_object is None:
            self.other_object = self.get_other_object()

        self.request = request
        return super().post(request, *args, **kwargs)

    def get_other_object(self, queryset: QuerySet[_M2] | None = None) -> _M2:
        """Similar to `get_object`, but uses other queryset."""
        queryset = self.get_other_queryset()
        return cast(
            _M2,
            super().get_object(
                queryset=queryset,  # type: ignore
            ),
        )

    def get_other_queryset(self) -> QuerySet[_M2]:
        """Similar to `get_queryset`, but uses other queryset/model."""
        if self.queryset_other is None:
            if self.model_other:
                return self.model_other._default_manager.all()
            else:
                cls = self.__class__.__name__
                raise ImproperlyConfigured(
                    f"{cls} is missing a QuerySet. Define {cls}.model_other, "
                    f"{cls}.queryset_other, or override "
                    f"{cls}.get_other_queryset()."
                )
        return self.queryset_other.all()

    def get_form_kwargs(self) -> dict[str, Any]:
        """Remove `instance` from form's parameters.

        This is necessary because having `pk_url_kwarg` / `slug_url_kwarg`
        makes this form into edit form."""
        kwargs = super().get_form_kwargs()
        if "instance" in kwargs:
            del kwargs["instance"]
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add other object to the template context."""
        kwargs[self.context_other_object_name] = self.other_object
        return super().get_context_data(**kwargs)
