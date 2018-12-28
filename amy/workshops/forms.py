from datetime import datetime, timezone
import re

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Submit, Button, Field
from django import forms
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.dispatch import receiver
from django.forms import (
    SelectMultiple,
    CheckboxSelectMultiple,
    TextInput,
    RadioSelect,
)
from django_comments.models import Comment
from django_countries import Countries
from django_countries.fields import CountryField

from workshops.models import (
    Award,
    Event,
    Lesson,
    Person,
    Task,
    Airport,
    Organization,
    Membership,
    Tag,
    Language,
)
# this is used instead of Django Autocomplete Light widgets
# see issue #1330: https://github.com/swcarpentry/amy/issues/1330
from workshops.fields import (
    Select2Multiple,
    ListSelect2,
    ModelSelect2,
    ModelSelect2Multiple,
)
from workshops.signals import create_comment_signal


# settings for Select2
# this makes it possible for autocomplete widget to fit in low-width sidebar
SIDEBAR_DAL_WIDTH = {
    'data-width': '100%',
    'width': 'style',
}


class BootstrapHelper(FormHelper):
    """Layout and behavior for crispy-displayed forms."""
    html5_required = True
    form_id = 'main-form'

    def __init__(self,
                 form=None,
                 duplicate_buttons_on_top=False,
                 submit_label='Submit',
                 submit_name='submit',
                 use_get_method=False,
                 wider_labels=False,
                 add_submit_button=True,
                 add_delete_button=False,
                 add_cancel_button=True,
                 additional_form_class='',
                 form_tag=True,
                 display_labels=True,
                 form_action=None,
                 form_id=None,
                 include_media=True):
        """
        `duplicate_buttons_on_top` -- Whether submit buttons should be
        displayed on both top and bottom of the form.

        `use_get_method` -- Force form to use GET instead of default POST.

        `wider_labels` -- SWCEventRequestForm and DCEventRequestForm have
        long labels, so this flag (set to True) is used to address that issue.

        `add_delete_button` -- displays additional red "delete" button.
        If you want to use it, you need to include in your template the
        following code:

            <form action="delete?next={{ request.GET.next|urlencode }}" method="POST" id="delete-form">
              {% csrf_token %}
            </form>

        This is necessary, because delete button must be reassigned from the
        form using this helper to "delete-form". This reassignment is done
        via HTML5 "form" attribute on the "delete" button.

        `display_labels` -- Set to False, when your form has only submit
        buttons and you want these buttons to be aligned to left.
        """

        super().__init__(form)

        self.attrs['role'] = 'form'

        self.duplicate_buttons_on_top = duplicate_buttons_on_top

        self.submit_label = submit_label

        if use_get_method:
            self.form_method = 'get'

        if wider_labels:
            assert display_labels
            self.label_class = 'col-12 col-lg-3'
            self.field_class = 'col-12 col-lg-7'
        elif display_labels:
            self.label_class = 'col-12 col-lg-2'
            self.field_class = 'col-12 col-lg-8'
        else:
            self.label_class = ''
            self.field_class = 'col-lg-12'

        if add_submit_button:
            self.add_input(Submit(submit_name, submit_label))

        if add_delete_button:
            self.add_input(Submit(
                'delete', 'Delete',
                onclick='return '
                        'confirm("Are you sure you want to delete it?");',
                form='delete-form',
                css_class='btn-danger float-right'))

        if add_cancel_button:
            self.add_input(Button(
                'cancel', 'Cancel',
                css_class='btn-secondary float-right',
                onclick='window.history.back()'))

        self.form_class = 'form-horizontal ' + additional_form_class

        self.form_tag = form_tag

        if form_action is not None:
            self.form_action = form_action

        if form_id is not None:
            self.form_id = form_id

        # don't prevent from loading media by default
        self.include_media = include_media


class BootstrapHelperFilter(FormHelper):
    """A differently shaped forms (more space-efficient) for use in sidebar as
    filter forms."""
    form_method = 'get'
    form_id = 'filter-form'

    def __init__(self, form=None):
        super().__init__(form)
        self.attrs['role'] = 'form'
        self.inputs.append(Submit('', 'Submit'))


class BootstrapHelperFormsetInline(BootstrapHelper):
    """For use in inline formsets."""
    template = 'bootstrap/table_inline_formset.html'


bootstrap_helper_filter = BootstrapHelperFilter()
bootstrap_helper_inline_formsets = BootstrapHelperFormsetInline()


# ----------------------------------------------------------
# MixIns

class PrivacyConsentMixin(forms.Form):
    privacy_consent = forms.BooleanField(
        label='*I have read and agree to <a href='
              '"https://docs.carpentries.org/topic_folders/policies/'
              'privacy.html" target="_blank">'
              'the data privacy policy of The Carpentries</a>.',
        required=True)


class WidgetOverrideMixin:
    def __init__(self, *args, **kwargs):
        widgets = kwargs.pop('widgets', {})
        super().__init__(*args, **kwargs)
        for field, widget in widgets.items():
            self.fields[field].widget = widget


# ----------------------------------------------------------
# Forms

class WorkshopStaffForm(forms.Form):
    '''Represent instructor matching form.'''

    latitude = forms.FloatField(label='Latitude',
                                min_value=-90.0,
                                max_value=90.0,
                                required=False)
    longitude = forms.FloatField(label='Longitude',
                                 min_value=-180.0,
                                 max_value=180.0,
                                 required=False)
    airport = forms.ModelChoiceField(
        label='Airport',
        required=False,
        queryset=Airport.objects.all(),
        widget=ModelSelect2(
            url='airport-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        )
    )
    languages = forms.ModelMultipleChoiceField(
        label='Languages',
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2Multiple(
            url='language-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        )
    )

    country = forms.MultipleChoiceField(choices=[])

    lessons = forms.ModelMultipleChoiceField(
        queryset=Lesson.objects.all(),
        widget=SelectMultiple(),
        required=False,
    )

    INSTRUCTOR_BADGE_CHOICES = (
        ('swc-instructor', 'Software Carpentry Instructor'),
        ('dc-instructor', 'Data Carpentry Instructor'),
        ('lc-instructor', 'Library Carpentry Instructor'),
    )
    instructor_badges = forms.MultipleChoiceField(
        choices=INSTRUCTOR_BADGE_CHOICES,
        widget=CheckboxSelectMultiple(),
        required=False,
    )

    GENDER_CHOICES = ((None, '---------'), ) + Person.GENDER_CHOICES
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)

    was_helper = forms.BooleanField(
        required=False, label='Was helper at least once before')
    was_organizer = forms.BooleanField(
        required=False, label='Was organizer at least once before')
    is_in_progress_trainee = forms.BooleanField(
        required=False, label='Is an in-progress instructor trainee')

    def __init__(self, *args, **kwargs):
        '''Build form layout dynamically.'''
        super().__init__(*args, **kwargs)

        # dynamically build choices for country field
        only = Airport.objects.distinct().exclude(country='') \
                                         .exclude(country=None) \
                                         .values_list('country', flat=True)
        countries = Countries()
        countries.only = only

        choices = list(countries)
        self.fields['country'] = forms.MultipleChoiceField(
            choices=choices, required=False, widget=Select2Multiple,
        )

        self.helper = FormHelper(self)
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML('<h5 class="card-title">Location close to</h5>'),
                    'airport',
                    HTML('<hr>'),
                    'country',
                    HTML('<hr>'),
                    'latitude',
                    'longitude',
                    css_class='card-body'
                ),
                css_class='card',
            ),
            'instructor_badges',
            HTML('<hr>'),
            'was_helper',
            'was_organizer',
            'is_in_progress_trainee',
            'languages',
            'gender',
            'lessons',
            Submit('submit', 'Submit'),
        )

    def clean(self):
        cleaned_data = super().clean()
        lat = bool(cleaned_data.get('latitude'))
        lng = bool(cleaned_data.get('longitude'))
        airport = bool(cleaned_data.get('airport'))
        country = bool(cleaned_data.get('country'))
        latlng = lat and lng

        # if searching by coordinates, then there must be both lat & lng
        # present
        if lat ^ lng:
            raise forms.ValidationError(
                'Must specify both latitude and longitude if searching by '
                'coordinates')

        # User must search by airport, or country, or coordinates, or none
        # of them. Sum of boolean elements must be equal 0 (if general search)
        # or 1 (if searching by airport OR country OR lat/lng).
        if sum([airport, country, latlng]) not in [0, 1]:
            raise forms.ValidationError(
                'Must specify an airport OR a country, OR use coordinates, OR '
                'none of them.')
        return cleaned_data


class BulkUploadCSVForm(forms.Form):
    """This form allows to upload a single file; it's used by person bulk
    upload and training request manual score bulk upload."""
    file = forms.FileField()


class SearchForm(forms.Form):
    '''Represent general searching form.'''

    term = forms.CharField(label='Term',
                           max_length=100)
    in_organizations = forms.BooleanField(label='in organizations',
                                          required=False,
                                          initial=True)
    in_events = forms.BooleanField(label='in events',
                                   required=False,
                                   initial=True)
    in_persons = forms.BooleanField(label='in persons',
                                    required=False,
                                    initial=True)
    in_airports = forms.BooleanField(label='in airports',
                                     required=False,
                                     initial=True)
    in_training_requests = forms.BooleanField(label='in training requests',
                                              required=False,
                                              initial=True)

    helper = BootstrapHelper(
        add_cancel_button=False,
        use_get_method=True,
    )


class EventForm(forms.ModelForm):
    host = forms.ModelChoiceField(
        label='Host',
        required=True,
        help_text=Event._meta.get_field('host').help_text,
        queryset=Organization.objects.all(),
        widget=ModelSelect2(url='organization-lookup')
    )

    administrator = forms.ModelChoiceField(
        label='Administrator',
        required=False,
        help_text=Event._meta.get_field('administrator').help_text,
        queryset=Organization.objects.all(),
        widget=ModelSelect2(url='organization-lookup')
    )

    assigned_to = forms.ModelChoiceField(
        label='Assigned to',
        required=False,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='admin-lookup')
    )

    language = forms.ModelChoiceField(
        label='Language',
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2(url='language-lookup')
    )

    country = CountryField().formfield(
        required=False,
        help_text=Event._meta.get_field('country').help_text,
        widget=ListSelect2(),
    )

    helper = BootstrapHelper(add_cancel_button=False,
                             duplicate_buttons_on_top=True)

    class Meta:
        model = Event
        fields = ['slug', 'completed', 'start', 'end', 'host', 'administrator',
                  'assigned_to', 'tags', 'url', 'language', 'reg_key', 'venue',
                  'attendance', 'contact',
                  'country', 'address', 'latitude', 'longitude',
                  'open_TTT_applications', 'curricula', ]
        widgets = {
            'attendance': TextInput,
            'latitude': TextInput,
            'longitude': TextInput,
            'invoice_status': RadioSelect,
            'tags': SelectMultiple(attrs={
                'size': Tag.ITEMS_VISIBLE_IN_SELECT_WIDGET
            }),
            'curricula': CheckboxSelectMultiple(),
        }

    class Media:
        # thanks to this, {{ form.media }} in the template will generate
        # a <link href=""> (for CSS files) or <script src=""> (for JS files)
        js = (
            'date_yyyymmdd.js',
            'edit_from_url.js',
            'online_country.js',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            Field('slug', placeholder='YYYY-MM-DD-location'),
            'completed',
            Field('start', placeholder='YYYY-MM-DD'),
            Field('end', placeholder='YYYY-MM-DD'),
            'host',
            'administrator',
            'assigned_to',
            'tags',
            'open_TTT_applications',
            'curricula',
            'url',
            'language',
            'reg_key',
            'attendance',
            'contact',
            Div(
                Div(HTML('Location details'), css_class='card-header'),
                Div('country',
                    'venue',
                    'address',
                    'latitude',
                    'longitude',
                    css_class='card-body'),
                css_class='card mb-2'
            ),
        )

    def clean_slug(self):
        # Ensure slug is in "YYYY-MM-DD-location" format
        data = self.cleaned_data['slug']
        match = re.match(r'(\d{4}|x{4})-(\d{2}|x{2})-(\d{2}|x{2})-.+', data)
        if not match:
            raise forms.ValidationError('Slug must be in "YYYY-MM-DD-location"'
                                        ' format, where "YYYY", "MM", "DD" can'
                                        ' be unspecified (ie. "xx").')
        return data

    def clean_end(self):
        """Ensure end >= start."""
        start = self.cleaned_data['start']
        end = self.cleaned_data['end']

        if start and end and end < start:
            raise forms.ValidationError('Must not be earlier than start date.')
        return end

    def clean_open_TTT_applications(self):
        """Ensure there's a TTT tag applied to the event, if the
        `open_TTT_applications` is True."""
        open_TTT_applications = self.cleaned_data['open_TTT_applications']
        tags = self.cleaned_data.get('tags', None)
        error_msg = 'You cannot open applications on a non-TTT event.'

        if open_TTT_applications and tags:
            # find TTT tag
            TTT_tag = False
            for tag in tags:
                if tag.name == 'TTT':
                    TTT_tag = True
                    break

            if not TTT_tag:
                raise forms.ValidationError(error_msg)

        elif open_TTT_applications:
            raise forms.ValidationError(error_msg)

        return open_TTT_applications

    def clean_curricula(self):
        """Validate tags when some curricula are selected."""
        curricula = self.cleaned_data['curricula']
        tags = self.cleaned_data['tags']

        try:
            expected_tags = [
                c.slug.split("-")[0].upper() for c in curricula
                if c.active and not c.unknown
            ]
        except (ValueError, TypeError):
            expected_tags = []

        for tag in expected_tags:
            if not tags.filter(name=tag):
                raise forms.ValidationError(
                    "You must add tags corresponding to these curricula.")

        return curricula


class EventCreateForm(EventForm):
    comment = forms.CharField(
        label='Comment',
        help_text='This will be added to comments after the event is created',
        widget=forms.Textarea,
        required=False,
    )

    class Meta(EventForm.Meta):
        fields = EventForm.Meta.fields.copy()
        fields.append('comment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.append('comment')

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(sender=self.__class__,
                                   content_object=res,
                                   comment=self.cleaned_data['comment'],
                                   timestamp=None)

        return res


class TaskForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper(add_cancel_button=False)

    SEAT_MEMBERSHIP_HELP_TEXT = (
        '{}<br><b>Hint:</b> you can use input format YYYY-MM-DD to display '
        'memberships available on that date.'.format(
            Task._meta.get_field('seat_membership').help_text
        )
    )
    seat_membership = forms.ModelChoiceField(
        label=Task._meta.get_field('seat_membership').verbose_name,
        help_text=SEAT_MEMBERSHIP_HELP_TEXT,
        required=False,
        queryset=Membership.objects.all(),
        widget=ModelSelect2(
            url='membership-lookup',
            attrs=SIDEBAR_DAL_WIDTH,
        )
    )

    class Meta:
        model = Task
        fields = '__all__'
        widgets = {
            'person': ModelSelect2(url='person-lookup',
                                   attrs=SIDEBAR_DAL_WIDTH),
            'event': ModelSelect2(url='event-lookup',
                                  attrs=SIDEBAR_DAL_WIDTH),
        }


class PersonForm(forms.ModelForm):
    airport = forms.ModelChoiceField(
        label='Airport',
        required=False,
        queryset=Airport.objects.all(),
        widget=ModelSelect2(url='airport-lookup')
    )
    languages = forms.ModelMultipleChoiceField(
        label='Languages',
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2Multiple(url='language-lookup')
    )

    helper = BootstrapHelper(add_cancel_button=False,
                             duplicate_buttons_on_top=True)

    class Meta:
        model = Person
        # don't display the 'password', 'user_permissions',
        # 'groups' or 'is_superuser' fields
        # + reorder fields
        fields = [
            'username',
            'personal',
            'middle',
            'family',
            'may_contact',
            'publish_profile',
            'lesson_publication_consent',
            'data_privacy_agreement',
            'email',
            'gender',
            'country',
            'airport',
            'affiliation',
            'github',
            'twitter',
            'url',
            'occupation',
            'orcid',
            'user_notes',
            'lessons',
            'domains',
            'languages',
        ]

        widgets = {
            'country': ListSelect2(),
        }


class PersonCreateForm(PersonForm):
    comment = forms.CharField(
        label='Comment',
        help_text='This will be added to comments after the event is created',
        widget=forms.Textarea,
        required=False,
    )

    class Meta(PersonForm.Meta):
        # remove 'username' field as it's being populated after form save
        # in the `views.PersonCreate.form_valid`
        fields = PersonForm.Meta.fields.copy()
        fields.remove('username')
        fields.append('comment')

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)

        create_comment_signal.send(sender=self.__class__,
                                   content_object=res,
                                   comment=self.cleaned_data['comment'],
                                   timestamp=None)

        return res


class PersonPermissionsForm(forms.ModelForm):
    helper = BootstrapHelper(add_cancel_button=False)

    user_permissions = forms.ModelMultipleChoiceField(
        label=Person._meta.get_field('user_permissions').verbose_name,
        help_text=Person._meta.get_field('user_permissions').help_text,
        required=False,
        queryset=Permission.objects.select_related('content_type'),
    )
    user_permissions.widget.attrs.update({'class': 'resizable-vertical',
                                          'size': '20'})

    class Meta:
        model = Person
        # only display administration-related fields: groups, permissions,
        # being a superuser or being active (== ability to log in)
        fields = [
            'is_active',
            'is_superuser',
            'user_permissions',
            'groups',
        ]


class PersonsSelectionForm(forms.Form):
    person_a = forms.ModelChoiceField(
        label='Person From',
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='person-lookup')
    )

    person_b = forms.ModelChoiceField(
        label='Person To',
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='person-lookup')
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class PersonsMergeForm(forms.Form):
    TWO = (
        ('obj_a', 'Use A'),
        ('obj_b', 'Use B'),
    )
    THREE = TWO + (('combine', 'Combine'), )
    DEFAULT = 'obj_a'

    person_a = forms.ModelChoiceField(queryset=Person.objects.all(),
                                      widget=forms.HiddenInput)

    person_b = forms.ModelChoiceField(queryset=Person.objects.all(),
                                      widget=forms.HiddenInput)

    id = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    username = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    personal = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    middle = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    family = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    email = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    may_contact = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    publish_profile = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    data_privacy_agreement = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    gender = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    airport = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    github = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    twitter = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    url = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    affiliation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    occupation = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    orcid = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    award_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    qualification_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
        label='Lessons',
    )
    domains = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    languages = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    task_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    is_active = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    trainingprogress_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    comment_comments = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    comments = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )


class AwardForm(WidgetOverrideMixin, forms.ModelForm):

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = Award
        fields = '__all__'
        widgets = {
            'person': ModelSelect2(url='person-lookup',
                                   attrs=SIDEBAR_DAL_WIDTH),
            'event': ModelSelect2(url='event-lookup',
                                  attrs=SIDEBAR_DAL_WIDTH),
            'awarded_by': ModelSelect2(url='admin-lookup',
                                       attrs=SIDEBAR_DAL_WIDTH),
        }


class EventLookupForm(forms.Form):
    event = forms.ModelChoiceField(
        label='Event',
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2(url='event-lookup')
    )

    helper = BootstrapHelper(add_cancel_button=False)


class PersonLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label='Person',
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='person-lookup')
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class AdminLookupForm(forms.Form):
    person = forms.ModelChoiceField(
        label='Administrator',
        required=True,
        queryset=Person.objects.all(),
        widget=ModelSelect2(url='admin-lookup')
    )

    helper = BootstrapHelper(add_cancel_button=False)


class EventsSelectionForm(forms.Form):
    event_a = forms.ModelChoiceField(
        label='Event A',
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2(url='event-lookup')
    )

    event_b = forms.ModelChoiceField(
        label='Event B',
        required=True,
        queryset=Event.objects.all(),
        widget=ModelSelect2(url='event-lookup')
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class EventsMergeForm(forms.Form):
    TWO = (
        ('obj_a', 'Use A'),
        ('obj_b', 'Use B'),
    )
    THREE = TWO + (('combine', 'Combine'), )
    DEFAULT = 'obj_a'

    event_a = forms.ModelChoiceField(queryset=Event.objects.all(),
                                     widget=forms.HiddenInput)

    event_b = forms.ModelChoiceField(queryset=Event.objects.all(),
                                     widget=forms.HiddenInput)

    id = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    slug = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    completed = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    assigned_to = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    start = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    end = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    host = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    administrator = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    tags = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    url = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    language = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    reg_key = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    admin_fee = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    invoice_status = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    attendance = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    contact = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    country = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    venue = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    address = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    latitude = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    longitude = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    learners_pre = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    learners_post = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    instructors_pre = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    instructors_post = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    learners_longterm = forms.ChoiceField(
        choices=TWO, initial=DEFAULT, widget=forms.RadioSelect,
    )
    task_set = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )
    comments = forms.ChoiceField(
        choices=THREE, initial=DEFAULT, widget=forms.RadioSelect,
    )


# ----------------------------------------------------------
# Action required forms

class ActionRequiredPrivacyForm(forms.ModelForm):
    data_privacy_agreement = forms.BooleanField(
        label='*I have read and agree to <a href='
              '"https://docs.carpentries.org/topic_folders/policies/'
              'privacy.html" target="_blank">'
              'the data privacy policy of The Carpentries</a>.',
        required=True)

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = Person
        fields = [
            'data_privacy_agreement',
            'may_contact',
            'publish_profile',
        ]


# ----------------------------------------------------------
# Signals

@receiver(create_comment_signal, sender=EventCreateForm)
@receiver(create_comment_signal, sender=PersonCreateForm)
def form_saved_add_comment(sender, **kwargs):
    """A receiver for custom form.save() signal. This is intended to save
    comment, entered as a form field, when creating a new object, and present
    it as automatic system Comment (from django_comments app)."""
    content_object = kwargs.get('content_object', None)
    comment = kwargs.get('comment', None)
    timestamp = kwargs.get('timestamp', datetime.now(timezone.utc))

    # only proceed if we have an actual object (that exists in DB), and
    # comment contents
    if content_object and comment and content_object.pk:
        site = Site.objects.get_current()
        Comment.objects.create(
            content_object=content_object,
            site=site,
            user=None,
            user_name='Automatic comment',
            submit_date=timestamp,
            comment=comment,
        )
