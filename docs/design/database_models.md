# Database models

This document describes and summarizes roles of database models used in AMY. Models are
stored in each of the applications, in `models.py` file, for example:
`workshops/models.py`.

## Mixins

Following classes are used to extend models with some features:

### `PermissionsMixin`
Django mechanism for extending custom user classes, see
[documentation](https://docs.djangoproject.com/en/dev/topics/auth/customizing/#django.contrib.auth.models.PermissionsMixin).

### `AssignmentMixin`
Adds `assigned_to` field to the model. Used to define which [`Person`](#person) is
handling given model instance.

### `ActiveMixin`
Adds `active` boolean field to the model. Determines if model instance is considered
active (enabled) or inactive (disabled).

### `CreatedUpdatedMixin`
Adds `created_at` and `last_updated_at` datetime fields to the model. `created_at` is
updated to current timestamp only on model's creation, `last_updated_at` is updated on
every model instance save.

### `CreatedUpdatedArchivedMixin`
Extends `CreatedUpdatedMixin` with `archived_at` field, empty and nullable. This is
used by consents feature.  #TODO: add link to consents project

### `DataPrivacyAgreementMixin`
Adds boolean field for storing agreement to privacy policy. Used by [`Person`](#person)
model, as well as all requests models ([`TrainingRequest`](#trainingrequest),
[`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission)).

### `COCAgreementMixin`
Adds boolean field for storing agreement to code of conduct. Used by all requests models
([`TrainingRequest`](#trainingrequest), [`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission)).

### `HostResponsibilitiesMixin`
Adds boolean field for storing agreement to list of workshop host responsibilities. Used
by all workshop requests models ([`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission)).

### `InstructorAvailabilityMixin`
Adds boolean field for storing agreement to lack of guarantee to allocate instructors
for a centrally-organised workshop. Used by [`WorkshopRequest`](#workshoprequest) and
[`WorkshopInquiryRequest`](#workshopinquiryrequest).

### `EventLinkMixin`
Adds field to link model instance to a particular event. Used by workshop request
models: [`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission).

### `StateMixin`
Adds a choice field with 3 options: "Pending", "Discarded" and "Accepted". Used for
determining state of a particular request (usually). Used by
[`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission),
[`InstructorRecruitmentSignup`](#instructorrecruitmentsignup).

### `StateExtendedMixin`
Extends `StateMixin` with new choice: "Withdrawn". Used only by
[`TrainingRequest`](#trainingrequest).

### `GenderMixin`
Adds two fields. First with a list of available genders to choose from, including gender
variant, undisclosed, and other. Second field allows for text entry of "other" gender
value. Used by [`Person`](#person) model, but also appears in some forms for updating
or creating `Person` model instances.

### `SecondaryEmailMixin`
Adds an email field for storing alternative email address. Used by [`Person`](#person),
[`TrainingRequest`](#trainingrequest) and [`CommonRequest`](#commonrequest) mixin.

### `RQJobsMixin`
Adds field to link model instance to [`RQJob`](#rqjob) instance. Usually this indicates
that a particular model instance triggered and automated email (represented by `RQJob`
instance). Used by [`Term`](#term),
[`InstructorRecruitmentSignup`](#instructorrecruitmentsignup), [`Person`](#person),
[`Event`](#event), [`Task`](#task) and [`WorkshopRequest`](#workshoprequest).

### `CommonRequest`
Adds multiple fields in common between workshop requests models
([`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission)).

## Reversion mechanism

Some of the models are using a `@reversion.register` decorator. This
decorator comes from a `django-reversion`
[package](https://django-reversion.readthedocs.io/en/stable/) indended for
storing and easily restoring of historic "versions" of model instances.

## Auxiliary functions and models

`django-countries`
([documentation](https://pypi.python.org/pypi/django-countries)) is used for
location purposes within `Airport`, `Organization` and
`Event`-related models.

`django-airports` was considered for implementing world-wide airports, but it turned out it required geo extensions to the database.

An `is_admin` function defined within models is used for determining if
a person has administration role. People who are superusers (in terms of
Django authentication system) or belong to one of administrative groups
(again in terms of Django authentication system), including
"administrators", "steering committee", "trainers" and "invoicing", are
thought to be administrators.

## User management and authentication

A custom user model (`Person`) was defined according to Django documentation.


## Base models

### `Organization`
### `Membership`
### `Airport`
### `Person`
### `Event`
### `Role`
### `Task`
### `Lesson`
### `Qualification`
### `Badge`
### `Award`
### `KnowledgeDomain`
### `Tag`
### `Language`

## Todo models
### `InstructorRecruitmentSignup`
### `Term`
### `RQJob`

## Requests and form-models
### `WorkshopRequest`
### `WorkshopInquiryRequest`
### `SelfOrganisedSubmission`
### `AcademicLevel`
### `ComputingExperienceLevel`
### `DataAnalysisLevel`
### `DCWorkshopTopic`
### `DCWorkshopDomain`

## Training-connected models
### `TrainingRequest`
### `TrainingRequirement`
### `TrainingProgress`

## Query sets
### `TagQuerySet`
### `EventQuerySet`
### `BadgeQuerySet`

## Deprecated
### `TodoItemQuerySet`
### `TodoItem`
