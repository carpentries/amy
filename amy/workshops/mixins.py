from django.db import models
from django.utils.functional import cached_property


class AssignmentMixin(models.Model):
    """This abstract model acts as a mix-in, so it adds
    "assigned to admin [...]" field to any inheriting model."""

    assigned_to = models.ForeignKey(
        "workshops.Person", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        abstract = True


class ActiveMixin(models.Model):
    """This mixin adds 'active' field for marking model instances as active or
    inactive (e.g. closed or in 'not have to worry about it' state)."""

    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class CreatedUpdatedMixin(models.Model):
    """This mixin provides two fields for storing instance creation time and
    last update time. It's faster than checking model revisions (and they
    aren't always enabled for some models)."""

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class DataPrivacyAgreementMixin(models.Model):
    """This mixin provides a data privacy agreement. Instead of being in the
    forms only (as a additional and required input), we're switching to having
    this agreement stored in the database."""

    data_privacy_agreement = models.BooleanField(
        null=False,
        blank=False,
        default=False,  # for 'normal' migration purposes
        verbose_name="I have read and agree to <a href="
        '"https://docs.carpentries.org/topic_folders/policies/privacy.html" '
        'target="_blank" rel="noreferrer">the data privacy policy</a> '
        "of The Carpentries.",
    )

    class Meta:
        abstract = True


class COCAgreementMixin(models.Model):
    """This mixin provides a code-of-conduct agreement. Instead of being in the
    forms only (as a additional and required input), we're switching to having
    this agreement stored in the database."""

    code_of_conduct_agreement = models.BooleanField(
        null=False,
        blank=False,
        default=False,  # for 'normal' migration purposes
        verbose_name="I agree to abide by The Carpentries' <a href="
        '"https://docs.carpentries.org/topic_folders/policies/code-of-conduct.html" '
        'target="_blank" rel="noreferrer">Code of Conduct</a>.',
    )

    class Meta:
        abstract = True


class HostResponsibilitiesMixin(models.Model):
    """This mixin provides a workshop host responsibilities checkbox."""

    host_responsibilities = models.BooleanField(
        null=False,
        blank=False,
        default=False,
        verbose_name='I understand <a href="https://docs.carpentries.org/'
        "topic_folders/hosts_instructors/hosts_instructors_checklist.html"
        '#host-checklist">the responsibilities of the workshop host</a>,'
        " including recruiting local helpers to support the workshop "
        "(1 helper for every 8-10 learners).",
    )

    class Meta:
        abstract = True


class InstructorAvailabilityMixin(models.Model):
    """This mixin provides a checkbox for confirming agreement to no guarantee of
    instructors availability in case of short-notice workshops."""

    instructor_availability = models.BooleanField(
        null=False,
        blank=True,  # special condition check in the form
        default=False,
        verbose_name="I understand that if my workshop is less than two months away,"
        " The Carpentries can not guarantee availability of Instructors"
        " and I may not be able to hold my workshop as scheduled.",
    )

    class Meta:
        abstract = True


class EventLinkMixin(models.Model):
    """This mixin provides a one-to-one link between a model, in which it's
    used, and single Event instance."""

    event = models.OneToOneField(
        "workshops.Event",
        null=True,
        blank=True,
        verbose_name="Linked event object",
        help_text="Link to the event instance created or otherwise related to this"
        " object.",
        on_delete=models.PROTECT,
    )

    class Meta:
        abstract = True


class StateMixin(models.Model):
    """A more extensive state field - previously a boolean `active` field was
    used, with only two states. Now there's three and can be extended."""

    STATE_CHOICES = (
        ("p", "Pending"),
        ("d", "Discarded"),
        ("a", "Accepted"),
    )
    state = models.CharField(
        max_length=1, choices=STATE_CHOICES, null=False, blank=False, default="p"
    )

    class Meta:
        abstract = True

    @cached_property
    def active(self):
        # after changing ActiveMixin to StateMixin, this should help in some
        # cases with code refactoring; will be removed later
        return self.state == "p"


class StateExtendedMixin(models.Model):
    """State field with representation of 'Withdrawn' state, for now only used in
    TrainingRequest.

    This was rewritten instead of inherited from `StateMixin` - there were some
    issues with `get_state_display` method for "withdrawn" state."""

    STATE_CHOICES = StateMixin.STATE_CHOICES + (("w", "Withdrawn"),)

    state = models.CharField(
        max_length=1, choices=STATE_CHOICES, null=False, blank=False, default="p"
    )

    class Meta:
        abstract = True

    @property
    def active(self):
        return self.state == "p"


class GenderMixin(models.Model):
    """Gender mixin for including gender fields in various models."""

    UNDISCLOSED = "U"  # Undisclosed (prefer not to say)
    MALE = "M"  # Male
    FEMALE = "F"  # Female
    VARIANT = "V"  # Gender variant / non-conforming
    OTHER = "O"  # Other

    GENDER_CHOICES = (
        (UNDISCLOSED, "Prefer not to say (undisclosed)"),
        (FEMALE, "Female"),
        (VARIANT, "Gender variant / non-conforming"),
        (MALE, "Male"),
        (OTHER, "Other: "),
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=False,
        null=False,
        default=UNDISCLOSED,
    )
    gender_other = models.CharField(
        max_length=100,
        verbose_name="Other gender",
        blank=True,
        null=False,
    )

    class Meta:
        abstract = True


class SecondaryEmailMixin(models.Model):
    """Mixin for adding a secondary (optional) email field."""

    secondary_email = models.EmailField(
        null=False,
        blank=True,
        default="",
        verbose_name="Secondary email address",
        help_text="This is an optional, secondary email address we can "
        "use to contact you.",
    )

    class Meta:
        abstract = True
