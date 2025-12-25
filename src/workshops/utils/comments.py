import datetime
from typing import Any

from django.contrib.sites.models import Site
from django.db.models import Model
from django_comments.models import Comment


def add_comment(content_object: Model, comment: str, **kwargs: Any) -> Comment:
    """A simple way to create a comment for specific object."""
    user = kwargs.get("user")
    user_name = kwargs.get("user_name", "Automatic comment")
    submit_date = kwargs.get("submit_date", datetime.datetime.now(datetime.UTC))
    site = kwargs.get("site", Site.objects.get_current())

    return Comment.objects.create(  # type: ignore[no-any-return]
        comment=comment,
        content_object=content_object,
        user=user,
        user_name=user_name,
        submit_date=submit_date,
        site=site,
    )
