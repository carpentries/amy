from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models


GHUSERNAME_MAX_LENGTH_VALIDATOR = MaxLengthValidator(39,
    message='Maximum allowed username length is 39 characters.',
)
# according to https://stackoverflow.com/q/30281026,
# GH username can only contain alphanumeric characters and
# hyphens (but not consecutive), cannot start or end with
# a hyphen, and can't be longer than 39 characters
GHUSERNAME_REGEX_VALIDATOR = RegexValidator(
    # regex inspired by above StackOverflow thread
    regex=r'^([a-zA-Z\d](?:-?[a-zA-Z\d])*)$',
    message='This is not a valid GitHub username.',
)


class NullableGithubUsernameField(models.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('default', '')
        # max length of the GH username is 39 characters
        kwargs.setdefault('max_length', 39)
        super().__init__(**kwargs)

    default_validators = [
        GHUSERNAME_MAX_LENGTH_VALIDATOR,
        GHUSERNAME_REGEX_VALIDATOR,
    ]
