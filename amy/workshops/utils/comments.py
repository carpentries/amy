import datetime

from django.contrib.sites.models import Site
from django_comments.models import Comment


def add_comment(content_object, comment, **kwargs):
    """A simple way to create a comment for specific object."""
    user = kwargs.get("user", None)
    user_name = kwargs.get("user_name", "Automatic comment")
    submit_date = kwargs.get(
        "submit_date", datetime.datetime.now(datetime.timezone.utc)
    )
    site = kwargs.get("site", Site.objects.get_current())

    return Comment.objects.create(
        comment=comment,
        content_object=content_object,
        user=user,
        user_name=user_name,
        submit_date=submit_date,
        site=site,
    )
