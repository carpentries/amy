from selectable.base import ModelLookup
from selectable.registry import registry

from . import models


class SiteLookup(ModelLookup):
    model = models.Site
    search_fields = ('domain__icontains', )


registry.register(SiteLookup)
