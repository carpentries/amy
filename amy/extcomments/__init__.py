def get_model():
    from django_comments.models import Comment
    return Comment


def get_form():
    from extcomments.forms import CommentForm
    return CommentForm
