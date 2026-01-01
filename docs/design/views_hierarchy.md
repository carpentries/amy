# Views hierarchy

["View"](https://docs.djangoproject.com/en/dev/glossary/#term-view) is Django term for
a piece of logic responsible for rendering a page (using
[template](https://docs.djangoproject.com/en/4.1/glossary/#term-template)) or processing
a request (for example adding a blog post through some form).

There's a lot of various views in AMY, but some of them share common behavior. Since
they are implemented in OOP
([object-oriented programming](https://en.wikipedia.org/wiki/Object-oriented_programming)),
it was possible to extract common behaviours in form of class mixins. They are described
below.

## Mixins and base views

The concept of mixins is extensively used in Django's
[class based views](https://docs.djangoproject.com/en/dev/topics/class-based-views/).
A lot of them is used in AMY, too. Good resource to read about the views is
[CCBV](https://ccbv.co.uk/).

### `ActionManageMixin` (`amy/autoemails/base_views.py`)

Note: no longer available in the codebase as `autoemails` application was removed.

This mixin was designed to support triggering actions (from
[automated emails](./projects/2019_automated_emails.md) project) by inheriting from it
in class-based views, but as it turned out this is never used. Its `add` and `remove`
static methods are used quite often, on the other hand.

This mixin should be redesigned to a controller or helper class.

### `WRFInitial` (`amy/extrequests/base_views.py`)

This mixin is used in views:

* `WorkshopRequestAcceptEvent`
* `WorkshopInquiryAcceptEvent`
* `SelfOrganisedSubmissionAcceptEvent`

The purpose is to provide initial values (like event start, end dates, tags, curricula,
public status, and contact information). Most of these values are the same for all 3
views, but in some corner cases they are located differently. For example, in
`SelfOrganisedSubmission` model there's a relation to curricula called `workshop_types`,
but in `WorkshopRequest` and `WorkshopInquiryRequest` the same relation is called
`requested_workshop_types`.

### `AMYCreateAndFetchObjectView` (`amy/extrequests/base_views.py`)

[`AMYCreateView`](#amycreateview-amyworkshopsbase_viewspy) extended with fetching
a different object based on URL parameter.

Useful when there's a need to create an object related to another existing object, e.g.
to create an event from a `WorkshopRequest` object.

### `GetMembershipMixin` (`amy/fiscal/base_views.py`)

A small mixin fetching membership based on URL parameter on every request.

### `MembershipFormsetView` (`amy/fiscal/base_views.py`)

A mixin based on [`FormView`](https://ccbv.co.uk/FormView) but intended for handling
[formsets](https://docs.djangoproject.com/en/dev/topics/forms/formsets/), especially
formsets containing multiple membership-related objects (e.g. membership member
organisations and their roles, or membership tasks).

### `UnquoteSlugMixin` (`amy/fiscal/base_views.py`)

Used when URL slug field, needed to access the object represented by that field, may
contain characters requiring unquoting. This is used by 3 organisation-related views
(details, update, delete).

### `FormInvalidMessageMixin` (`src/workshops/base_views.py`)

Add an error message on invalid form submission.

### `AMYDetailView` (`src/workshops/base_views.py`)

Almost a direct, not extended descendant of [`DetailView`](https://ccbv.co.uk/DetailView),
with one small exception: it contains type annotation for `object` attribute of the
class.

### `AMYCreateView` (`src/workshops/base_views.py`)

Class-based view for creating objects that extends default template context by adding
model class used in objects creation. Additionally defines default form template,
default
[form helper](https://django-crispy-forms.readthedocs.io/en/latest/form_helper.html),
default title, default success message, and default invalid form message.

### `AMYUpdateView` (`src/workshops/base_views.py`)

Class-based view for updating objects that extends default template context by adding
proper page title.

Provides the same changes as [`AMYCreateView`](#amycreateview-amyworkshopsbase_viewspy).

### `AMYDeleteView` (`src/workshops/base_views.py`)

Class-based view for deleting objects that additionally handles `ProtectedError`s (occur
when attempting to delete a foreign-referenced object). Blocks `GET` requests.

### `AMYFormView` (`src/workshops/base_views.py`)

Not used, should be removed.

### `AMYListView` (`src/workshops/base_views.py`)

Configures [`ListView`](https://ccbv.co.uk/ListView) with
[filters](https://django-filter.readthedocs.io/en/stable/) (if provided), pagination
using custom paginator, and some basic context.

### `EmailSendMixin` (`src/workshops/base_views.py`)

Used for sending emails when forms pass validation upon `POST` request.

### `RedirectSupportMixin` (`src/workshops/base_views.py`)

Implements a safe redirect after form is submitted.

### `PrepopulationSupportMixin` (`src/workshops/base_views.py`)

Supports populating some form fields with values, e.g. from `GET` parameters.

### `AutoresponderMixin` (`src/workshops/base_views.py`)

Automatically emails the form sender.

### `StateFilterMixin` (`src/workshops/base_views.py`)

Small mixin used to change default filter value for `state` field (sets it to pending).

### `ChangeRequestStateView` (`src/workshops/base_views.py`)

Almost standalone view used by `WorkshopRequest`, `WorkshopInquiryRequest`, and
`SelfOrganisedSubmission` to change request state (to accepted, discarded, or pending).

### `AssignView` (`src/workshops/base_views.py`)

Almost standalone view used to assign specific person to `WorkshopRequest`,
`WorkshopInquiryRequest`, `SelfOrganisedSubmission` or `Event`.

### `ConditionallyEnabledMixin` (`src/workshops/base_views.py`)

Mixin for enabling views based on feature flag.

### OnlyForAdminsMixin (`src/workshops/utils/access.py`)

Contains a pre-defined test function checking if user is authenticated and if user
is considered an administrator.

### OnlyForAdminsNoRedirectMixin (`src/workshops/utils/access.py`)

Same as [`OnlyForAdminsMixin`](#onlyforadminsmixin-amyworkshopsutilsaccesspy), but will
not redirect to the login page when test function fails, but instead will throw
"permissions denied" exception.

### LoginNotRequiredMixin (`src/workshops/utils/access.py`)

Empty class to indicate that specific view is open to public, and doesn't need any
permission checking.
