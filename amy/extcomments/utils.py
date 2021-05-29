from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import Model
from django_comments import get_form
from django_comments.models import Comment


def add_comment_for_object(
    object: Model,
    user: AbstractBaseUser,
    content: str,
) -> Comment:
    """A simple utility to add a comment for given object by given user."""

    # Adding comment is the easiest to achieve using comment form methods.
    CommentForm = get_form()

    security_data = CommentForm(object).generate_security_data()
    data = {
        "honeypot": "",
        "comment": content,
        "name": user.get_username(),
        **security_data,
    }

    form = CommentForm(object, data=data)
    comment = form.get_comment_object()
    comment.user = user

    # Original code in django_comments emits `comment_will_be_posted` signal at this
    # point and checks if any of the receivers prevents comment from posting. For
    # simplicity this behavior has not been implemented here.

    comment.save()
    return comment
