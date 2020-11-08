from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

from workshops.base_views import AMYCreateView
from workshops.models import Tag, Curriculum


class WRFInitial:
    def get_initial(self):
        curricula = Curriculum.objects.none()

        if hasattr(self.other_object, "workshop_types"):
            curricula = self.other_object.workshop_types.all()
        elif hasattr(self.other_object, "requested_workshop_types"):
            curricula = self.other_object.requested_workshop_types.all()

        tag_names = [
            C.carpentry for C in curricula if C.carpentry
        ]
        if curricula.filter(mix_match=True).exists():
            tag_names.append("Circuits")
        if self.other_object.online_inperson == "online":
            tag_names.append("online")

        listed = self.other_object.workshop_listed
        if not listed:
            tag_names.append("private-event")

        initial = {
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
            location = getattr(self.other_object, "location", "XXX")
            initial["slug"] = "{:%Y-%m-%d}-{}".format(
                start, location.replace(" ", "-").lower()
            )

        if end:
            initial["end"] = end

        return initial


class AMYCreateAndFetchObjectView(AMYCreateView):
    """AMY-based CreateView extended with fetching a different object based on
    URL parameter."""

    model_other = None
    queryset_other = None
    context_other_object_name = 'other_object'
    pk_url_kwarg = 'pk'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    query_pk_and_slug = False

    def __init__(self, *args, **kwargs):
        """Initialize some internal vars."""
        self.other_object = None
        super().__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Load other object upon GET request. Save the request."""
        if self.other_object is None:
            self.other_object = self.get_other_object()

        self.request = request
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Load other object upon POST request. Save the request."""
        if self.other_object is None:
            self.other_object = self.get_other_object()

        self.request = request
        return super().post(request, *args, **kwargs)

    def get_other_object(self, queryset=None):
        """Similar to `get_object`, but uses other queryset."""
        queryset = self.get_other_queryset()
        return super().get_object(queryset=queryset)

    def get_other_queryset(self):
        """Similar to `get_queryset`, but uses other queryset/model."""
        if self.queryset_other is None:
            if self.other_model:
                return self.model_other._default_manager.all()
            else:
                cls = self.__class__.__name__
                raise ImproperlyConfigured(
                    f"{cls} is missing a QuerySet. Define {cls}.model_other, "
                    f"{cls}.queryset_other, or override "
                    f"{cls}.get_other_queryset()."
                )
        return self.queryset_other.all()

    def get_form_kwargs(self):
        """Remove `instance` from form's parameters.

        This is necessary because having `pk_url_kwarg` / `slug_url_kwarg`
        makes this form into edit form."""
        kwargs = super().get_form_kwargs()
        if 'instance' in kwargs:
            del kwargs['instance']
        return kwargs

    def get_context_data(self, **kwargs):
        """Add other object to the template context."""
        kwargs[self.context_other_object_name] = self.other_object
        return super().get_context_data(**kwargs)
