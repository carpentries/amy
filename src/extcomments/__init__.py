from typing import Any


def get_model() -> type[Any]:
    from django_comments.models import Comment

    return Comment


def get_form() -> type[Any]:
    from src.extcomments.forms import CommentForm

    return CommentForm
