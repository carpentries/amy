from collections import defaultdict
from typing import Any, Protocol

from django.db import IntegrityError
from django.db.models import Model
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from src.workshops.models import Person


class Assignable(Protocol):
    assigned_to: Person | None

    def save(self) -> None: ...


class ModelWithGetAbsoluteURL(Protocol):
    def save(self) -> None: ...
    def get_absolute_url(self) -> str: ...


def failed_to_delete(
    request: HttpRequest, object: ModelWithGetAbsoluteURL, protected_objects: set[Model], back: str | None = None
) -> HttpResponse:
    context: dict[str, Any] = {
        "title": "Failed to delete",
        "back": back or object.get_absolute_url,
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


def assign(obj: Assignable, /, person: Person | None) -> None:
    """Set obj.assigned_to."""
    try:
        obj.assigned_to = person
        obj.save()
    except IntegrityError as e:
        raise Http404(f"Unable to assign {person} to {obj}.") from e
