import datetime

from crispy_forms.bootstrap import FormActions
from crispy_forms.layout import HTML, Div, Layout, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, When
from django.http import HttpRequest

from extrequests.models import (
    DataVariant,
    InfoSource,
    SelfOrganisedSubmission,
    WorkshopInquiryRequest,
)
from workshops.fields import (
    CheckboxSelectMultipleWithOthers,
    CurriculumModelMultipleChoiceField,
    ModelSelect2Widget,
    RadioSelectFakeMultiple,
    RadioSelectWithOther,
    SafeModelMultipleChoiceField,
    Select2TagWidget,
    Select2Widget,
)
from workshops.forms import BootstrapHelper
from workshops.models import (
    AcademicLevel,
    Curriculum,
    Event,
    KnowledgeDomain,
    Membership,
    Organization,
    Person,
    Task,
    TrainingRequest,
    WorkshopRequest,
)
from workshops.utils.feature_flags import feature_flag_enabled


class BulkChangeTrainingRequestForm(forms.Form):
    """Form used to bulk discard training requests or bulk unmatch trainees
    from trainings."""

    requests = forms.ModelMultipleChoiceField(queryset=TrainingRequest.objects.all())

    helper = BootstrapHelper(
        add_submit_button=False,
        form_tag=False,
        display_labels=False,
        add_cancel_button=False,
    )
    helper.layout = Layout(
        # no 'requests' -- you should take care of generating it manually in
        # the template where this form is used
        # We use formnovalidate on submit buttons to disable browser
        # validation. This is necessary because this form is used along with
        # BulkMatchTrainingRequestForm, which have required fields. Both
        # forms live inside the same <form> tag. Without this attribute,
        # when you click one of the following submit buttons, the browser
        # reports missing values in required fields in
        # BulkMatchTrainingRequestForm.
        FormActions(
            Div(
                Submit(
                    "accept",
                    "Accept selected",
                    formnovalidate="formnovalidate",
                    css_class="btn-success",
                ),
                Submit(
                    "discard",
                    "Discard selected",
                    formnovalidate="formnovalidate",
                    css_class="btn-danger",
                ),
                Submit(
                    "unmatch",
                    "Unmatch selected from training",
                    formnovalidate="formnovalidate",
                    css_class="btn-primary",
                ),
                css_class="btn-group",
            ),
        )
    )

    # When set to True, the form is valid only if every request is matched to
    # one person. Set to True when 'unmatch' button is clicked, because
    # unmatching makes sense only if each selected TrainingRequest is matched
    # with one person.
    check_person_matched = False

    def clean(self):
        super().clean()
        unmatched_request_exists = any(
            r.person is None for r in self.cleaned_data.get("requests", [])
        )
        if self.check_person_matched and unmatched_request_exists:
            raise ValidationError("Select only requests matched to a person.")


class BulkMatchTrainingRequestForm(forms.Form):
    requests = forms.ModelMultipleChoiceField(queryset=TrainingRequest.objects.all())

    event = forms.ModelChoiceField(
        label="Training",
        required=True,
        queryset=Event.objects.filter(tags__name="TTT"),
        widget=ModelSelect2Widget(data_view="ttt-event-lookup"),
    )

    seat_membership = forms.ModelChoiceField(
        label="Membership seats",
        required=False,
        queryset=Membership.objects.all(),
        help_text="Assigned users will take instructor seats from selected "
        "member site.",
        widget=ModelSelect2Widget(data_view="membership-lookup"),
    )

    seat_public = forms.TypedChoiceField(
        coerce=lambda x: x == "True",
        choices=Task.SEAT_PUBLIC_CHOICES,
        initial=Task._meta.get_field("seat_public").default,
        required=False,
        label=Task._meta.get_field("seat_public").verbose_name,
        widget=forms.RadioSelect(),
    )

    seat_open_training = forms.BooleanField(
        label="Open training seat",
        required=False,
        help_text="Some TTT events allow for open training; check this field "
        "to count this person into open applications.",
    )

    helper = BootstrapHelper(
        add_submit_button=False, form_tag=False, add_cancel_button=False
    )
    helper.layout = Layout(
        "event",
        "seat_membership",
        "seat_public",
        "seat_open_training",
    )
    helper.add_input(
        Submit(
            "match",
            "Accept & match selected trainees to chosen training",
            **{
                "data-toggle": "popover",
                "data-html": "true",
                "data-trigger": "hover",
                "data-content": "If you want to <strong>re</strong>match "
                "trainees to other training, first "
                "<strong>unmatch</strong> them!",
            },
        )
    )

    def clean(self):
        super().clean()

        event = self.cleaned_data["event"]
        member_site = self.cleaned_data["seat_membership"]
        open_training = self.cleaned_data["seat_open_training"]

        if any(r.person is None for r in self.cleaned_data.get("requests", [])):
            raise ValidationError(
                "Some of the requests are not matched "
                "to a trainee yet. Before matching them to "
                "a training, you need to accept them "
                "and match with a trainee."
            )

        if member_site and open_training:
            raise ValidationError(
                "Cannot simultaneously match as open training and use "
                "a Membership instructor training seat."
            )

        if open_training and not event.open_TTT_applications:
            raise ValidationError(
                {
                    "seat_open_training": ValidationError(
                        "Selected TTT event does not allow for open training " "seats."
                    ),
                }
            )


class MatchTrainingRequestForm(forms.Form):
    """Form used to match a training request to a Person."""

    person = forms.ModelChoiceField(
        label="Trainee Account",
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),
    )

    helper = BootstrapHelper(add_submit_button=False, add_cancel_button=False)
    helper.layout = Layout(
        "person",
        FormActions(
            Submit("match-selected-person", "Match to selected trainee account"),
            HTML("&nbsp;<strong>OR</strong>&nbsp;&nbsp;"),
            Submit("create-new-person", "Create new trainee account"),
        ),
    )

    def clean(self):
        super().clean()

        if "match-selected-person" in self.data:
            self.person_required = True
            self.action = "match"
        elif "create-new-person" in self.data:
            self.person_required = False
            self.action = "create"
        else:
            raise ValidationError("Unknown action.")

        if self.person_required and self.cleaned_data["person"] is None:
            raise ValidationError({"person": "No person was selected."})

    class Meta:
        fields = [
            "person",
        ]


# ----------------------------------------------------------
# WorkshopRequest related forms


class WorkshopRequestBaseForm(forms.ModelForm):
    institution = forms.ModelChoiceField(
        required=False,
        queryset=Organization.objects.order_by("fullname").exclude(
            fullname="self-organized"
        ),
        widget=Select2Widget(fake_required=True),
        label=WorkshopRequest._meta.get_field("institution").verbose_name,
        help_text=WorkshopRequest._meta.get_field("institution").help_text,
    )

    travel_expences_agreement = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field("travel_expences_agreement").verbose_name,
    )
    data_privacy_agreement = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field("data_privacy_agreement").verbose_name,
    )
    code_of_conduct_agreement = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field("code_of_conduct_agreement").verbose_name,
    )
    host_responsibilities = forms.BooleanField(
        required=True,
        label=WorkshopRequest._meta.get_field("host_responsibilities").verbose_name,
    )
    instructor_availability = forms.BooleanField(
        required=False,
        label=WorkshopRequest._meta.get_field("instructor_availability").verbose_name,
    )

    requested_workshop_types = CurriculumModelMultipleChoiceField(
        required=True,
        queryset=Curriculum.objects.default_order(
            allow_unknown=False, allow_other=False
        ).filter(active=True),
        label=WorkshopRequest._meta.get_field("requested_workshop_types").verbose_name,
        help_text=WorkshopRequest._meta.get_field("requested_workshop_types").help_text,
        widget=RadioSelectFakeMultiple(),
    )

    carpentries_info_source = SafeModelMultipleChoiceField(
        required=WorkshopRequest._meta.get_field("carpentries_info_source").blank,
        queryset=InfoSource.objects.all(),
        label=WorkshopRequest._meta.get_field("carpentries_info_source").verbose_name,
        help_text=WorkshopRequest._meta.get_field("carpentries_info_source").help_text,
        widget=CheckboxSelectMultipleWithOthers("carpentries_info_source_other"),
    )

    helper = BootstrapHelper(add_cancel_button=False)

    class Media:
        js = ("instructor_availability_checkbox.js",)

    class Meta:
        model = WorkshopRequest
        fields = (
            "personal",
            "family",
            "email",
            "secondary_email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "member_code",
            "location",
            "country",
            "online_inperson",
            "requested_workshop_types",
            "preferred_dates",
            "other_preferred_dates",
            "language",
            "audience_description",
            "administrative_fee",
            "scholarship_circumstances",
            "travel_expences_management",
            "travel_expences_management_other",
            "travel_expences_agreement",
            "institution_restrictions",
            "institution_restrictions_other",
            "workshop_listed",
            "public_event",
            "public_event_other",
            "additional_contact",
            "carpentries_info_source",
            "carpentries_info_source_other",
            "user_notes",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
            "instructor_availability",
        )

        widgets = {
            "preferred_dates": forms.DateInput(attrs={"class": "nopastdates"}),
            "institution_other_URL": forms.TextInput(),
            "country": Select2Widget,
            "online_inperson": forms.RadioSelect(),
            "language": Select2Widget,
            "academic_levels": forms.CheckboxSelectMultiple(),
            "computing_levels": forms.CheckboxSelectMultiple(),
            "organization_type": forms.RadioSelect(),
            "administrative_fee": forms.RadioSelect(),
            "travel_expences_management": RadioSelectWithOther(
                "travel_expences_management_other"
            ),
            "workshop_listed": forms.RadioSelect(),
            "public_event": RadioSelectWithOther("public_event_other"),
            "institution_restrictions": RadioSelectWithOther(
                "institution_restrictions_other"
            ),
            "additional_contact": Select2TagWidget,
        }

    def __init__(self, *args, **kwargs):
        # request is required for ENFORCE_MEMBER_CODES flag
        self.request_http = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # the field isn't required, but we want user to fill it
        self.fields["preferred_dates"].widget.fake_required = True

        # change institution object labels (originally Organization displays
        # domain as well)
        self.fields[
            "institution"
        ].label_from_instance = self.institution_label_from_instance

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["travel_expences_management"].field.widget.other_field = self[
            "travel_expences_management_other"
        ]
        self["public_event"].field.widget.other_field = self["public_event_other"]
        self["institution_restrictions"].field.widget.other_field = self[
            "institution_restrictions_other"
        ]
        self["carpentries_info_source"].field.widget.other_field = self[
            "carpentries_info_source_other"
        ]

        # move "institution_other_name" field to "institution" subfield
        self["institution"].field.widget.subfields = [
            (self["institution_other_name"], "Institution name"),
            (self["institution_other_URL"], "Institution URL address"),
        ]

        # remove additional fields
        self.helper.layout.fields.remove("travel_expences_management_other")
        self.helper.layout.fields.remove("public_event_other")
        self.helper.layout.fields.remove("institution_restrictions_other")
        self.helper.layout.fields.remove("carpentries_info_source_other")
        self.helper.layout.fields.remove("institution_other_name")
        self.helper.layout.fields.remove("institution_other_URL")

        # add warning alert for dates falling within next 2-3 months
        DATES_TOO_SOON_WARNING = (
            "The dates you have selected occurs outside of our 2-3 month "
            "planning procedure. Please be advised that we will not be able "
            "to guarantee that instructors will be available. If you have "
            "flexibility with your dates please provide those dates or range "
            "of dates."
        )
        pos_index = self.helper.layout.fields.index("preferred_dates")
        self.helper.layout.insert(
            pos_index + 1,
            Div(
                Div(
                    HTML(DATES_TOO_SOON_WARNING),
                    css_class="alert alert-warning offset-lg-2 col-lg-8 col-12",
                ),
                id="preferred_dates_warning",
                css_class="form-group row d-none",
            ),
        )

        # add horizontal lines after some fields to visually group them
        # together
        hr_fields_after = (
            "secondary_email",
            "institution_department",
            "member_code",
            "country",
            "audience_description",
            "user_notes",
            "online_inperson",
        )
        hr_fields_before = ("carpentries_info_source",)
        for field in hr_fields_after:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field) + 1,
                HTML(self.helper.hr()),
            )
        for field in hr_fields_before:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field),
                HTML(self.helper.hr()),
            )

    @staticmethod
    def institution_label_from_instance(obj):
        """Static method that overrides ModelChoiceField choice labels,
        essentially works just like `Model.__str__`."""
        return "{}".format(obj.fullname)

    @feature_flag_enabled("ENFORCE_MEMBER_CODES")
    def validate_member_code(
        self, request: HttpRequest
    ) -> None | dict[str, ValidationError]:
        errors = dict()
        code = self.cleaned_data.get("member_code", "")
        error_msg = (
            "This code is invalid. "
            "Please contact your Member Affiliate to verify your code."
        )
        # ensure that code belongs to a membership
        try:
            Membership.objects.get(registration_code=code)
        except Membership.DoesNotExist:
            errors["member_code"] = ValidationError(error_msg)

        return errors

    def clean(self):
        super().clean()
        errors = dict()

        # 1: validate institution (allow for selected institution, or expect
        #    two other fields - name and URL)
        institution = self.cleaned_data.get("institution", None)
        institution_other_name = self.cleaned_data.get("institution_other_name", "")
        institution_other_URL = self.cleaned_data.get("institution_other_URL", "")
        if not institution and not institution_other_name and not institution_other_URL:
            errors["institution"] = ValidationError("Institution is required.")
        elif institution and institution_other_name:
            errors["institution_other_name"] = ValidationError(
                "You must select institution from the list, or enter its name "
                "below the list. You can't do both."
            )
        elif institution and institution_other_URL:
            errors["institution_other_URL"] = ValidationError(
                "You can't enter institution URL if you select institution "
                "from the list above."
            )
        elif (
            not institution
            and not institution_other_name
            and institution_other_URL
            or not institution
            and institution_other_name
            and not institution_other_URL
        ):
            errors["institution_other_name"] = ValidationError(
                "You must enter both institution name and its URL address."
            )

        # 2: require preferred_dates or its "other" counterpart
        preferred_dates = self.cleaned_data.get("preferred_dates", None)
        other_preferred_dates = self.cleaned_data.get("other_preferred_dates", None)
        if not preferred_dates and not other_preferred_dates:
            errors["preferred_dates"] = ValidationError(
                "This field or the field below is required."
            )

        yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
        if preferred_dates and preferred_dates < yesterday:
            errors["preferred_dates"] = ValidationError(
                "You cannot select date in the past."
            )

        # 3: circumstances for scholarship request only required if scholarship
        #    is chosen
        administrative_fee = self.cleaned_data.get("administrative_fee", "")
        scholarship_circumstances = self.cleaned_data.get(
            "scholarship_circumstances", ""
        )

        # 'waiver' is an old name for scholarship
        if administrative_fee == "waiver" and not scholarship_circumstances:
            errors["scholarship_circumstances"] = ValidationError(
                "This field is required if you're requesting a scholarship."
            )
        elif administrative_fee != "waiver" and scholarship_circumstances:
            errors["scholarship_circumstances"] = ValidationError(
                "This field should be empty if you're not requesting " "a scholarship."
            )

        # 4: require travel expenses
        travel_expences_management = self.cleaned_data.get(
            "travel_expences_management", ""
        )
        travel_expences_management_other = self.cleaned_data.get(
            "travel_expences_management_other", ""
        )
        if (
            travel_expences_management == "other"
            and not travel_expences_management_other
        ):
            errors["travel_expences_management"] = ValidationError(
                "This field is required."
            )
        elif travel_expences_management != "other" and travel_expences_management_other:
            errors["travel_expences_management"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 5: require institution restrictions
        institution_restrictions = self.cleaned_data.get("institution_restrictions", "")
        institution_restrictions_other = self.cleaned_data.get(
            "institution_restrictions_other", ""
        )
        if institution_restrictions == "other" and not institution_restrictions_other:
            errors["institution_restrictions"] = ValidationError(
                "This field is required."
            )
        elif institution_restrictions != "other" and institution_restrictions_other:
            errors["institution_restrictions"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 6: require public event
        public_event = self.cleaned_data.get("public_event", "")
        public_event_other = self.cleaned_data.get("public_event_other", "")
        if public_event == "other" and not public_event_other:
            errors["public_event"] = ValidationError(
                'Please provide description if you selected "Other".'
            )
        elif public_event != "other" and public_event_other:
            errors["public_event"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 7: if workshop is less than 2mo away, or if the dates are unknown, require the
        # confirmation in `instructor_availability`:
        instructor_availability: bool = self.cleaned_data.get("instructor_availability")
        two_months_away = datetime.date.today() + datetime.timedelta(days=60)
        if (
            preferred_dates and preferred_dates <= two_months_away
        ) or not preferred_dates:
            if not instructor_availability:
                errors["instructor_availability"] = ValidationError(
                    "Please confirm instructor availability, since the workshop is "
                    'planned for less than 2 months away or "Other" arrangements '
                    "were selected."
                )

        # 8: enforce membership registration codes
        membership_errors = self.validate_member_code(request=self.request_http)
        if membership_errors:
            errors.update(membership_errors)

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class WorkshopRequestAdminForm(WorkshopRequestBaseForm):
    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta(WorkshopRequestBaseForm.Meta):
        fields = ("state", "event") + WorkshopRequestBaseForm.Meta.fields

        widgets = WorkshopRequestBaseForm.Meta.widgets.copy()
        widgets.update({"event": Select2Widget})


# ----------------------------------------------------------
# WorkshopInquiryRequest related forms


class WorkshopInquiryRequestBaseForm(forms.ModelForm):
    institution = forms.ModelChoiceField(
        required=False,
        queryset=Organization.objects.order_by("fullname").exclude(
            domain="self-organized"
        ),
        widget=Select2Widget,
        label=WorkshopInquiryRequest._meta.get_field("institution").verbose_name,
        help_text=WorkshopInquiryRequest._meta.get_field("institution").help_text,
    )
    routine_data = forms.ModelMultipleChoiceField(
        required=False,
        queryset=DataVariant.objects.order_by(
            # always leave "Don't know yet" last
            Case(When(unknown=True, then=-1)),
        ),
        widget=CheckboxSelectMultipleWithOthers("routine_data_other"),
        label=WorkshopInquiryRequest._meta.get_field("routine_data").verbose_name,
        help_text=WorkshopInquiryRequest._meta.get_field("routine_data").help_text,
    )
    domains = forms.ModelMultipleChoiceField(
        required=False,
        queryset=KnowledgeDomain.objects.order_by(
            # this crazy django-ninja-code sorts by 'name', but leaves
            # "Don't know yet" entry last
            Case(When(name="Don't know yet", then=-1)),
            "name",
        ),
        widget=CheckboxSelectMultipleWithOthers("domains_other"),
        label=WorkshopInquiryRequest._meta.get_field("domains").verbose_name,
        help_text=WorkshopInquiryRequest._meta.get_field("domains").help_text,
    )
    academic_levels = forms.ModelMultipleChoiceField(
        required=False,
        queryset=AcademicLevel.objects.order_by(
            # always leave "Don't know yet" last
            Case(When(name="Don't know yet", then=-1)),
        ),
        widget=forms.CheckboxSelectMultiple(),
        label=WorkshopInquiryRequest._meta.get_field("academic_levels").verbose_name,
        help_text=WorkshopInquiryRequest._meta.get_field("academic_levels").help_text,
    )
    data_privacy_agreement = forms.BooleanField(
        required=True,
        label=WorkshopInquiryRequest._meta.get_field(
            "data_privacy_agreement"
        ).verbose_name,
    )
    code_of_conduct_agreement = forms.BooleanField(
        required=True,
        label=WorkshopInquiryRequest._meta.get_field(
            "code_of_conduct_agreement"
        ).verbose_name,
    )
    host_responsibilities = forms.BooleanField(
        required=True,
        label=WorkshopInquiryRequest._meta.get_field(
            "host_responsibilities"
        ).verbose_name,
    )
    instructor_availability = forms.BooleanField(
        required=False,
        label=WorkshopInquiryRequest._meta.get_field(
            "instructor_availability"
        ).verbose_name,
    )

    requested_workshop_types = CurriculumModelMultipleChoiceField(
        required=False,
        queryset=Curriculum.objects.default_order(
            allow_other=False, allow_unknown=True, dont_know_yet_first=True
        ).filter(active=True),
        label=WorkshopInquiryRequest._meta.get_field(
            "requested_workshop_types"
        ).verbose_name,
        help_text=WorkshopInquiryRequest._meta.get_field(
            "requested_workshop_types"
        ).help_text,
        widget=forms.CheckboxSelectMultiple(),
    )

    travel_expences_agreement = forms.BooleanField(
        required=True,
        label=WorkshopInquiryRequest._meta.get_field(
            "travel_expences_agreement"
        ).verbose_name,
    )

    carpentries_info_source = SafeModelMultipleChoiceField(
        required=not WorkshopInquiryRequest._meta.get_field(
            "carpentries_info_source"
        ).blank,
        queryset=InfoSource.objects.all(),
        label=WorkshopInquiryRequest._meta.get_field(
            "carpentries_info_source"
        ).verbose_name,
        help_text=WorkshopInquiryRequest._meta.get_field(
            "carpentries_info_source"
        ).help_text,
        widget=CheckboxSelectMultipleWithOthers("carpentries_info_source_other"),
    )

    helper = BootstrapHelper(add_cancel_button=False)

    class Media:
        js = ("instructor_availability_checkbox.js",)

    class Meta:
        model = WorkshopInquiryRequest
        fields = (
            "personal",
            "family",
            "email",
            "secondary_email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "location",
            "country",
            "online_inperson",
            # "your audience" section starts now
            "routine_data",
            "routine_data_other",
            "domains",
            "domains_other",
            "academic_levels",
            "computing_levels",
            "audience_description",
            "requested_workshop_types",
            "preferred_dates",
            "other_preferred_dates",
            "language",
            "administrative_fee",
            "travel_expences_management",
            "travel_expences_management_other",
            "travel_expences_agreement",
            "institution_restrictions",
            "institution_restrictions_other",
            "workshop_listed",
            "public_event",
            "public_event_other",
            "additional_contact",
            "carpentries_info_source",
            "carpentries_info_source_other",
            "user_notes",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
            "instructor_availability",
        )

        widgets = {
            "preferred_dates": forms.DateInput(attrs={"class": "nopastdates"}),
            "institution_other_URL": forms.TextInput(),
            "country": Select2Widget,
            "online_inperson": forms.RadioSelect(),
            "language": Select2Widget,
            "computing_levels": forms.CheckboxSelectMultiple(),
            "administrative_fee": forms.RadioSelect(),
            "travel_expences_management": RadioSelectWithOther(
                "travel_expences_management_other"
            ),
            "workshop_listed": forms.RadioSelect(),
            "public_event": RadioSelectWithOther("public_event_other"),
            "institution_restrictions": RadioSelectWithOther(
                "institution_restrictions_other"
            ),
            "additional_contact": Select2TagWidget,
        }

    @staticmethod
    def institution_label_from_instance(obj):
        """Static method that overrides ModelChoiceField choice labels,
        essentially works just like `Model.__str__`."""
        return "{}".format(obj.fullname)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # change institution object labels (originally Organization displays
        # domain as well)
        self.fields[
            "institution"
        ].label_from_instance = self.institution_label_from_instance

        self.fields["travel_expences_management"].required = False
        self.fields["institution_restrictions"].required = False
        self.fields["public_event"].required = False

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["routine_data"].field.widget.other_field = self["routine_data_other"]
        self["domains"].field.widget.other_field = self["domains_other"]
        self["travel_expences_management"].field.widget.other_field = self[
            "travel_expences_management_other"
        ]
        self["public_event"].field.widget.other_field = self["public_event_other"]
        self["institution_restrictions"].field.widget.other_field = self[
            "institution_restrictions_other"
        ]
        self["carpentries_info_source"].field.widget.other_field = self[
            "carpentries_info_source_other"
        ]

        # move "institution_other_name" field to "institution" subfield
        self["institution"].field.widget.subfields = [
            (self["institution_other_name"], "Institution name"),
            (self["institution_other_URL"], "Institution URL address"),
        ]

        # remove additional fields
        # self.helper.layout.fields.remove('domains_other')
        self.helper.layout.fields.remove("routine_data_other")
        self.helper.layout.fields.remove("domains_other")
        self.helper.layout.fields.remove("travel_expences_management_other")
        self.helper.layout.fields.remove("public_event_other")
        self.helper.layout.fields.remove("institution_restrictions_other")
        self.helper.layout.fields.remove("carpentries_info_source_other")
        self.helper.layout.fields.remove("institution_other_name")
        self.helper.layout.fields.remove("institution_other_URL")

        # add warning alert for proficiency computing level
        PROFICIENCY_WARNING = (
            "Our lessons are intended for novice or beginner level "
            "programmers. Please be advised that the material covered in this "
            "lesson may not match the skill set of your anticipated audience."
        )
        pos_index = self.helper.layout.fields.index("computing_levels")
        self.helper.layout.insert(
            pos_index + 1,
            Div(
                Div(
                    HTML(PROFICIENCY_WARNING),
                    css_class="alert alert-warning offset-lg-2 col-lg-8 col-12",
                ),
                id="computing_levels_warning",
                css_class="form-group row d-none",
            ),
        )

        # add warning alert for dates falling within next 2-3 months
        DATES_TOO_SOON_WARNING = (
            "The dates you have selected occurs outside of our 2-3 month "
            "planning procedure. Please be advised that we will not be able "
            "to guarantee that instructors will be available. If you have "
            "flexibility with your dates please provide those dates or range "
            "of dates."
        )
        pos_index = self.helper.layout.fields.index("preferred_dates")
        self.helper.layout.insert(
            pos_index + 1,
            Div(
                Div(
                    HTML(DATES_TOO_SOON_WARNING),
                    css_class="alert alert-warning offset-lg-2 col-lg-8 col-12",
                ),
                id="preferred_dates_warning",
                css_class="form-group row d-none",
            ),
        )

        # add horizontal lines after some fields to visually group them
        # together
        hr_fields_after = (
            "secondary_email",
            "institution_department",
            "audience_description",
            "country",
            "user_notes",
            "online_inperson",
        )
        hr_fields_before = (
            "administrative_fee",
            "carpentries_info_source",
        )
        for field in hr_fields_after:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field) + 1,
                HTML(self.helper.hr()),
            )
        for field in hr_fields_before:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field),
                HTML(self.helper.hr()),
            )

        AGREEMENTS_TEXT = (
            "If we proceed with coordinating a workshop, you will agree to"
            " the following:"
        )
        self.helper.layout.insert(
            self.helper.layout.fields.index("data_privacy_agreement"),
            HTML(f"<p class='lead offset-lg-2'>{AGREEMENTS_TEXT}</p>"),
        )
        TRAVEL_AGR_TEXT = (
            "If we proceed with coordinating a workshop, I will agree to"
            " the following:"
        )
        self.helper.layout.insert(
            self.helper.layout.fields.index("travel_expences_agreement"),
            HTML(f"<p class='lead offset-lg-2'>{TRAVEL_AGR_TEXT}</p>"),
        )

    def clean(self):
        super().clean()
        errors = dict()

        # 1: validate institution (allow for selected institution, or expect
        #    two other fields - name and URL)
        institution = self.cleaned_data.get("institution", None)
        institution_other_name = self.cleaned_data.get("institution_other_name", "")
        institution_other_URL = self.cleaned_data.get("institution_other_URL", "")
        if institution and institution_other_name:
            errors["institution_other_name"] = ValidationError(
                "You must select institution from the list, or enter its name "
                "below the list. You can't do both."
            )
        elif institution and institution_other_URL:
            errors["institution_other_URL"] = ValidationError(
                "You can't enter institution URL if you select institution "
                "from the list above."
            )
        elif (
            not institution
            and not institution_other_name
            and institution_other_URL
            or not institution
            and institution_other_name
            and not institution_other_URL
        ):
            errors["institution_other_name"] = ValidationError(
                "You must enter both institution name and its URL address."
            )

        # 2: make sure routine data, domains, academic level, computing level,
        #    workshop type all have something selected, but if it's "Don't know yet"
        #    then it must be the only option
        routine_data = self.cleaned_data.get("routine_data", None)
        routine_data_other = self.cleaned_data.get("routine_data_other", None)
        domains = self.cleaned_data.get("domains", None)
        domains_other = self.cleaned_data.get("domains_other", None)
        academic_levels = self.cleaned_data.get("academic_levels", None)
        computing_levels = self.cleaned_data.get("computing_levels", None)
        requested_workshop_types = self.cleaned_data.get(
            "requested_workshop_types",
            None,
        )

        if routine_data and routine_data.filter(unknown=True):
            if len(routine_data) > 1 or routine_data_other:
                errors["routine_data"] = ValidationError(
                    "If you select \"Don't know yet\", you can't select "
                    "anything else or enter other values."
                )

        if domains and domains.filter(name="Don't know yet"):
            if len(domains) > 1 or domains_other:
                errors["domains"] = ValidationError(
                    "If you select \"Don't know yet\", you can't select "
                    "anything else or enter other values."
                )

        if (
            academic_levels
            and academic_levels.filter(name="Don't know yet")
            and len(academic_levels) > 1
        ):
            errors["academic_levels"] = ValidationError(
                "If you select \"Don't know yet\", you can't select " "anything else."
            )

        if (
            computing_levels
            and computing_levels.filter(name="Don't know yet")
            and len(computing_levels) > 1
        ):
            errors["computing_levels"] = ValidationError(
                "If you select \"Don't know yet\", you can't select " "anything else."
            )

        if (
            requested_workshop_types
            and requested_workshop_types.filter(unknown=True)
            and len(requested_workshop_types) > 1
        ):
            errors["requested_workshop_types"] = ValidationError(
                "If you select \"Don't know yet\", you can't select " "anything else."
            )

        # 3: require preferred_dates or its "other" counterpart
        preferred_dates = self.cleaned_data.get("preferred_dates", None)

        yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
        if preferred_dates and preferred_dates < yesterday:
            errors["preferred_dates"] = ValidationError(
                "You cannot select date in the past."
            )

        # 4: require travel expenses
        travel_expences_management = self.cleaned_data.get(
            "travel_expences_management", ""
        )
        travel_expences_management_other = self.cleaned_data.get(
            "travel_expences_management_other", ""
        )
        if (
            travel_expences_management == "other"
            and not travel_expences_management_other
        ):
            errors["travel_expences_management"] = ValidationError(
                'Please provide description if you selected "Other".'
            )
        elif travel_expences_management != "other" and travel_expences_management_other:
            errors["travel_expences_management"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 5: require institution restrictions
        institution_restrictions = self.cleaned_data.get("institution_restrictions", "")
        institution_restrictions_other = self.cleaned_data.get(
            "institution_restrictions_other", ""
        )
        if institution_restrictions == "other" and not institution_restrictions_other:
            errors["institution_restrictions"] = ValidationError(
                'Please provide description if you selected "Other".'
            )
        elif institution_restrictions != "other" and institution_restrictions_other:
            errors["institution_restrictions"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 6: require public event
        public_event = self.cleaned_data.get("public_event", "")
        public_event_other = self.cleaned_data.get("public_event_other", "")
        if public_event == "other" and not public_event_other:
            errors["public_event"] = ValidationError(
                'Please provide description if you selected "Other".'
            )
        elif public_event != "other" and public_event_other:
            errors["public_event"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 7: if workshop is less than 2mo away, or if the dates are unknown, require the
        # confirmation in `instructor_availability`:
        instructor_availability: bool = self.cleaned_data.get("instructor_availability")
        two_months_away = datetime.date.today() + datetime.timedelta(days=60)
        if (
            not preferred_dates or preferred_dates <= two_months_away
        ) and not instructor_availability:
            errors["instructor_availability"] = ValidationError(
                "Please confirm instructor availability, since the workshop is "
                'planned for less than 2 months away or "Other" arrangements '
                "were selected."
            )

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class WorkshopInquiryRequestAdminForm(WorkshopInquiryRequestBaseForm):
    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta(WorkshopInquiryRequestBaseForm.Meta):
        fields = (
            "state",
            "event",
        ) + WorkshopInquiryRequestBaseForm.Meta.fields

        widgets = WorkshopInquiryRequestBaseForm.Meta.widgets.copy()
        widgets.update({"event": Select2Widget})


# ----------------------------------------------------------
# SelfOrganisedSubmission related forms


class SelfOrganisedSubmissionBaseForm(forms.ModelForm):
    institution = forms.ModelChoiceField(
        required=False,
        queryset=Organization.objects.order_by("fullname").exclude(
            fullname="self-organized"
        ),
        widget=Select2Widget(fake_required=True),
        label=SelfOrganisedSubmission._meta.get_field("institution").verbose_name,
        help_text=SelfOrganisedSubmission._meta.get_field("institution").help_text,
    )

    data_privacy_agreement = forms.BooleanField(
        required=True,
        label=SelfOrganisedSubmission._meta.get_field(
            "data_privacy_agreement"
        ).verbose_name,
    )
    code_of_conduct_agreement = forms.BooleanField(
        required=True,
        label=SelfOrganisedSubmission._meta.get_field(
            "code_of_conduct_agreement"
        ).verbose_name,
    )
    host_responsibilities = forms.BooleanField(
        required=True,
        label=SelfOrganisedSubmission._meta.get_field(
            "host_responsibilities"
        ).verbose_name,
    )

    workshop_types = CurriculumModelMultipleChoiceField(
        required=True,
        queryset=Curriculum.objects.default_order(
            allow_other=False, allow_unknown=False, allow_mix_match=True
        ).filter(active=True),
        label=SelfOrganisedSubmission._meta.get_field("workshop_types").verbose_name,
        help_text=SelfOrganisedSubmission._meta.get_field("workshop_types").help_text,
        widget=RadioSelectFakeMultiple(),
    )

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = SelfOrganisedSubmission
        fields = (
            "personal",
            "family",
            "email",
            "secondary_email",
            "institution",
            "institution_other_name",
            "institution_other_URL",
            "institution_department",
            "online_inperson",
            "workshop_format",
            "workshop_format_other",
            "start",
            "end",
            "workshop_url",
            "workshop_types",
            "workshop_types_other_explain",
            "country",
            "language",
            "workshop_listed",
            "public_event",
            "public_event_other",
            "additional_contact",
            "data_privacy_agreement",
            "code_of_conduct_agreement",
            "host_responsibilities",
        )

        widgets = {
            "institution_other_URL": forms.TextInput(),
            "workshop_url": forms.TextInput(),
            "country": Select2Widget,
            "online_inperson": forms.RadioSelect(),
            "language": Select2Widget,
            "workshop_format": RadioSelectWithOther(
                "workshop_format_other", fake_required=True
            ),
            "workshop_listed": forms.RadioSelect(),
            "public_event": RadioSelectWithOther("public_event_other"),
            "additional_contact": Select2TagWidget,
        }

    class Media:
        js = ("selforganisedsubmission_form.js",)

    @staticmethod
    def institution_label_from_instance(obj):
        """Static method that overrides ModelChoiceField choice labels,
        essentially works just like `Model.__str__`."""
        return "{}".format(obj.fullname)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # change institution object labels (originally Organization displays
        # domain as well)
        self.fields[
            "institution"
        ].label_from_instance = self.institution_label_from_instance

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["workshop_format"].field.widget.other_field = self["workshop_format_other"]
        self["public_event"].field.widget.other_field = self["public_event_other"]

        # move "institution_other_name" field to "institution" subfield
        self["institution"].field.widget.subfields = [
            (self["institution_other_name"], "Institution name"),
            (self["institution_other_URL"], "Institution URL address"),
        ]

        # remove additional fields
        self.helper.layout.fields.remove("workshop_format_other")
        self.helper.layout.fields.remove("public_event_other")
        self.helper.layout.fields.remove("institution_other_name")
        self.helper.layout.fields.remove("institution_other_URL")

        # add horizontal lines after some fields to visually group them
        # together
        hr_fields_after = (
            "secondary_email",
            "institution_department",
            "additional_contact",
            "language",
            "online_inperson",
        )
        hr_fields_before = []
        for field in hr_fields_after:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field) + 1,
                HTML(self.helper.hr()),
            )
        for field in hr_fields_before:
            self.helper.layout.insert(
                self.helper.layout.fields.index(field),
                HTML(self.helper.hr()),
            )

        # add warning alert for workshop URL
        REPO_WARNING = (
            "Would you be able to update the name of the workshop webpage prior to "
            "submitting this notification? If so, we recommend using the following "
            "name: YEAR-MM-DD-site-online. If not, that's okay and please feel free "
            "to submit the form."
        )
        URL_WARNING = (
            "Please adjust the URL format so that it points to the workshop website. "
            "The format for this is: https://username.github.io/repo"
        )
        pos_index = self.helper.layout.fields.index("workshop_url")
        self.helper.layout.insert(
            pos_index + 1,
            Div(
                Div(
                    HTML(REPO_WARNING),
                    css_class="alert alert-warning offset-lg-2 col-lg-8 col-12",
                ),
                id="workshop_url_repo_warning",
                css_class="form-group row d-none",
            ),
        )
        self.helper.layout.insert(
            pos_index + 2,
            Div(
                Div(
                    HTML(URL_WARNING),
                    css_class="alert alert-warning offset-lg-2 col-lg-8 col-12",
                ),
                id="workshop_url_warning",
                css_class="form-group row d-none",
            ),
        )

    def clean(self):
        super().clean()
        errors = dict()

        # 1: validate institution (allow for selected institution, or expect
        #    two other fields - name and URL)
        institution = self.cleaned_data.get("institution", None)
        institution_other_name = self.cleaned_data.get("institution_other_name", "")
        institution_other_URL = self.cleaned_data.get("institution_other_URL", "")
        if not institution and not institution_other_name and not institution_other_URL:
            errors["institution"] = ValidationError("Institution is required.")
        elif institution and institution_other_name:
            errors["institution_other_name"] = ValidationError(
                "You must select institution from the list, or enter its name "
                "below the list. You can't do both."
            )
        elif institution and institution_other_URL:
            errors["institution_other_URL"] = ValidationError(
                "You can't enter institution URL if you select institution "
                "from the list above."
            )
        elif (
            not institution
            and not institution_other_name
            and institution_other_URL
            or not institution
            and institution_other_name
            and not institution_other_URL
        ):
            errors["institution_other_name"] = ValidationError(
                "You must enter both institution name and its URL address."
            )

        # 2: require workshop URL only if the format is standard 2-day workshop
        workshop_format = self.cleaned_data.get("workshop_format", "")
        workshop_url = self.cleaned_data.get("workshop_url", "")
        if workshop_format == "standard" and not workshop_url:
            errors["workshop_url"] = ValidationError(
                "This field is required if workshop format is standard two-day"
                " Carpentries workshop."
            )

        # 3: require "other" value for workshop format if it's selected
        workshop_format_other = self.cleaned_data.get("workshop_format_other", "")
        if workshop_format == "other" and not workshop_format_other:
            errors["workshop_format"] = ValidationError(
                'Please provide description if you selected "Other".'
            )
        elif workshop_format != "other" and workshop_format_other:
            errors["workshop_format"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # 4: make sure workshop types has something selected, but if it's
        #    "Mix & Match" then additionally require
        #    `workshop_types_other_explain`
        workshop_types = self.cleaned_data.get("workshop_types", None)
        workshop_types_other_explain = self.cleaned_data.get(
            "workshop_types_other_explain", None
        )
        if (
            workshop_types
            and workshop_types.filter(mix_match=True)
            and not workshop_types_other_explain
        ):
            errors["workshop_types_other_explain"] = ValidationError(
                'This field is required if you select "Mix & Match".'
            )

        # 5: require public event
        public_event = self.cleaned_data.get("public_event", "")
        public_event_other = self.cleaned_data.get("public_event_other", "")
        if public_event == "other" and not public_event_other:
            errors["public_event"] = ValidationError(
                'Please provide description if you selected "Other".'
            )
        elif public_event != "other" and public_event_other:
            errors["public_event"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class SelfOrganisedSubmissionAdminForm(SelfOrganisedSubmissionBaseForm):
    helper = BootstrapHelper(add_cancel_button=False, duplicate_buttons_on_top=True)

    class Meta(SelfOrganisedSubmissionBaseForm.Meta):
        fields = (
            "state",
            "event",
        ) + SelfOrganisedSubmissionBaseForm.Meta.fields

        widgets = SelfOrganisedSubmissionBaseForm.Meta.widgets.copy()
        widgets.update({"event": Select2Widget})


# ----------------------------------------------------------
# Training Requests


class TrainingRequestUpdateForm(forms.ModelForm):
    person = forms.ModelChoiceField(
        label="Matched Trainee",
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2Widget(data_view="person-lookup"),
    )

    score_auto = forms.IntegerField(
        disabled=True,
        label=TrainingRequest._meta.get_field("score_auto").verbose_name,
        help_text=TrainingRequest._meta.get_field("score_auto").help_text,
    )

    helper = BootstrapHelper(duplicate_buttons_on_top=True, submit_label="Update")

    class Meta:
        model = TrainingRequest
        exclude = ()
        widgets = {
            "occupation": forms.RadioSelect(),
            "domains": forms.CheckboxSelectMultiple(),
            "previous_involvement": forms.CheckboxSelectMultiple(),
            "previous_training": forms.RadioSelect(),
            "previous_experience": forms.RadioSelect(),
            "programming_language_usage_frequency": forms.RadioSelect(),
            "teaching_frequency_expectation": forms.RadioSelect(),
            "max_travelling_frequency": forms.RadioSelect(),
            "state": forms.RadioSelect(),
        }


class TrainingRequestsSelectionForm(forms.Form):
    trainingrequest_a = forms.ModelChoiceField(
        label="Training request A",
        required=True,
        queryset=TrainingRequest.objects.all(),
        widget=ModelSelect2Widget(data_view="trainingrequest-lookup"),
    )

    trainingrequest_b = forms.ModelChoiceField(
        label="Training request B",
        required=True,
        queryset=TrainingRequest.objects.all(),
        widget=ModelSelect2Widget(data_view="trainingrequest-lookup"),
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class TrainingRequestsMergeForm(forms.Form):
    TWO = (
        ("obj_a", "Use A"),
        ("obj_b", "Use B"),
    )
    THREE = TWO + (("combine", "Combine"),)
    DEFAULT = "obj_a"

    trainingrequest_a = forms.ModelChoiceField(
        queryset=TrainingRequest.objects.all(), widget=forms.HiddenInput
    )

    trainingrequest_b = forms.ModelChoiceField(
        queryset=TrainingRequest.objects.all(), widget=forms.HiddenInput
    )

    id = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    state = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    person = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    member_code = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    personal = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    middle = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    family = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    email = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    secondary_email = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    github = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    occupation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    occupation_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    affiliation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    location = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    country = forms.ChoiceField(choices=TWO, initial=DEFAULT, widget=forms.RadioSelect)
    underresourced = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    domains = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    domains_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    underrepresented = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    underrepresented_details = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    nonprofit_teaching_experience = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_involvement = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_training = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_training_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_training_explanation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_experience = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_experience_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    previous_experience_explanation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    programming_language_usage_frequency = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    teaching_frequency_expectation = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    teaching_frequency_expectation_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    max_travelling_frequency = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    max_travelling_frequency_other = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    reason = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    user_notes = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    training_completion_agreement = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    workshop_teaching_agreement = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    data_privacy_agreement = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    code_of_conduct_agreement = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    created_at = forms.ChoiceField(
        choices=TWO,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    comments = forms.ChoiceField(
        choices=THREE,
        initial=DEFAULT,
        widget=forms.RadioSelect,
    )
    trainingrequestconsent_set = forms.ChoiceField(
        choices=(("most_recent", "Use the most recent consents"),),
        initial="most_recent",
        widget=forms.RadioSelect,
    )
