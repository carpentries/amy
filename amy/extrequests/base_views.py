from django.core.exceptions import ImproperlyConfigured

from workshops.base_views import AMYCreateView


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
