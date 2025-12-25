from django.core.exceptions import ValidationError


class TermOptionDoesNotBelongToTermException(ValidationError):
    pass
