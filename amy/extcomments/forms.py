from django import forms
from django.utils.translation import gettext_lazy as _
from django_comments.forms import COMMENT_MAX_LENGTH
from django_comments.forms import CommentForm as DjCF
from markdownx.fields import MarkdownxFormField


class CommentForm(DjCF):
    email = forms.EmailField(required=False)
    comment = MarkdownxFormField(label=_("Comment"), max_length=COMMENT_MAX_LENGTH)
