from django.utils.translation import ugettext_lazy as _
from django_comments.forms import COMMENT_MAX_LENGTH
from django_comments.forms import CommentForm as DjCF
from markdownx.fields import MarkdownxFormField


class CommentForm(DjCF):
    comment = MarkdownxFormField(label=_("Comment"), max_length=COMMENT_MAX_LENGTH)
