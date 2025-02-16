from collections import defaultdict
from typing import Any, Optional, Protocol

from django.db import IntegrityError
from django.db.models import Model
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from workshops.models import Person


class Assignable(Protocol):
    assigned_to: Optional[Person]

    def save(self) -> None: ...


def failed_to_delete(
    request: HttpRequest, object: Model, protected_objects: set[Model], back: str | None = None
) -> HttpResponse:
    context: dict[str, Any] = {
        "title": "Failed to delete",
        "back": back or getattr(object, "get_absolute_url"),
        "object": object,
        "refs": defaultdict(list),
    }

    for obj in protected_objects:
        # e.g. for model Award its plural name is 'awards'
        name = str(obj.__class__._meta.verbose_name_plural)
        context["refs"][name].append(obj)

    # this trick enables looping through defaultdict instance
    context["refs"].default_factory = None

    return render(request, "workshops/failed_to_delete.html", context)


def assign(obj: Assignable, /, person: Optional[Person]) -> None:
    """Set obj.assigned_to."""
    try:
        obj.assigned_to = person
        obj.save()
    except IntegrityError:
        raise Http404(f"Unable to assign {person} to {obj}.")
