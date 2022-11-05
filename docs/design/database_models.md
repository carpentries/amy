# Database models

This document describes and summarizes roles of database models used in AMY. Models are
stored in each of the applications, in `models.py` file, for example:
`workshops/models.py`.

----------------------------------------------------------------------------------------

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

----------------------------------------------------------------------------------------

## Versioning mechanism

Some of the models are using a `@reversion.register` decorator. This
decorator comes from a `django-reversion`
[package](https://django-reversion.readthedocs.io/en/stable/) indended for
storing and easily restoring of historic "versions" of model instances.

See [versioning](./model_versioning.md) documentation for more.

----------------------------------------------------------------------------------------

## Auxiliary functions and models

`django-countries`
([documentation](https://pypi.python.org/pypi/django-countries)) is used for
location purposes within `Airport`, `Organization` and
`Event`-related models.

[`django-contrib-comments`](https://github.com/django/django-contrib-comments) is
a package previously included in the Django itself. It's used as a comments framework.
Comments can be added to any model instance.

----------------------------------------------------------------------------------------

## User management and authentication

A custom user model (`Person`) was defined according to Django documentation.

----------------------------------------------------------------------------------------

## Core models - `workshops/models.py`

"Core" models are models defined inside `workshops` application, the oldest application
in AMY. Originally it was created as a single application project, at some point it was
split into more applications (modules).

### `Organization`
Represents an organisation, academic or business entity.
Multiple organisations can be linked (affiliated) together.

### `MemberRole`
Simple model representing a role assigned to a member.

### `Member`
An intermediate table for M2M between memberships and organisations.
Allows to specify organisation's membership and role inside a `Membership` model.

### `Membership`
Represents a membership of some organisation (or consortium of
organisations) in The Carpentries project. Memberships can be paid. With
each membership comes a number of fields defining perks like allowable
number of centrally-organised workshops that don't need to pay fee.

### `Airport`
Represents an airport (used for example to locate instructors).

### `Person`
Represents a single person. This is an extension of Django's default
`user` model, built with [`AbstractBaseuser`](https://docs.djangoproject.com/en/dev/topics/auth/customizing/#django.contrib.auth.models.AbstractBaseUser).

### `Tag`
Label for grouping events. In M2M relation with [`Event`](#event).

### `Language`
Represents a human language.
Used to indicate a language used at an event. In relation with models:
[`Event`](#event), [`WorkshopRequest`](#workshoprequest),
[`WorkshopInquiryRequest`](#workshopinquiryrequest),
[`SelfOrganisedSubmission`](#selforganisedsubmission).

### `Event`
Represents a single event. The most important model of all.

### `Role`
Simple model representing a role assinged to a person.

### `Task`
An intermediate table for M2M between events and persons. Represents a task person had
for a particular event. Links with a role to provide more detailed information.

### `Lesson`
Simple model representing a lesson someone might teach.

### `Qualification`
Intermediate table between person and a lesson. Nowadays probably not very much used.

### `Badge`
Quite important model to represent a certain skill (badge).

### `Award`
Intermediate table for M2M between persons and badges. Represents a badge that someone
was awarded.

### `KnowledgeDomain`
Represents a knowledge domain (like High Performance Computing) a person is engaged in.

### `TrainingRequest`
Represents a request for instructor training. Usually these requests come from people
who are not AMY users.

This model falls into `external requests` domain, which also includes `WorkshopRequest`,
`WorkshopInquiryRequest`, and `SelfOrganisedSubmission`.

This model also falls into `trainings` domain.

### `TrainingRequirement`
Represents a requirement that a prospect future instructor need to pass.

This model also falls into `trainings` domain.

### `TrainingProgress`
Intermediate table for M2M between persons and training requirements. Indicates "pass",
"fail", or "asked to repeat" progress of a person over a particular requirement.
Once all required requirements are passed, person can become an instructor.

### `Curriculum`
Represents a curriculum of a lesson taught at a workshop.

### `AcademicLevel`
Simple model to represent academic (education) level, e.g. "staff" or "post-doctorate".
Used in external requests / forms.

### `ComputingExperienceLevel`
Simple model to represent computer proficiency (novice / intermediate / proficient).
Used in external requests / forms.

### `InfoSource`
Simple model to represent source of information about The Carpentries.
Used in external requests / forms.

### `CommonRequest` - see mixins
A common ancestor for:

* [`WorkshopRequest`](#workshoprequest)
* [`WorkshopInquiryRequest`](#workshopinquiryrequest)
* [`SelfOrganisedSubmission`](#selforganisedsubmission)

Since all these requests are used in external forms, and are very similar to each other,
some common parts were extracted into `CommonRequest` abstract model (mixin).

### `WorkshopRequest`
Represents a request for teaching a Carpentries workshop.

This model falls into `external requests` domain.

----------------------------------------------------------------------------------------

## Fiscal application - `fiscal/models.py`

### `MembershipPersonRole`
Simple model, represents person role within a membership (see
[`Membership`](#membership) for more).

### `MembershipTask`
Similar to [`Task`](#task) model, but it's for a person task within a membership. Links
to `MembershipPersonRole`.

----------------------------------------------------------------------------------------

## External requests application - `extrequests/models.py`

### `DataVariant`
Simple model represents a variant of data (e.g. tabular data, images, nucleotide
sequence, unstructured text, etc.) that would be used in a workshop. The model
is used only by `WorkshopInquiryRequest`.

### `WorkshopInquiryRequest`
Represents an inquiry about teaching a Carpentries workshop.

This model falls into `external requests` domain.

### `SelfOrganisedSubmission`
Represents submission of a workshop that was self-organised (i.e. without help of The
Carpentries).

This model falls into `external requests` domain.

----------------------------------------------------------------------------------------

## Dashboard application - `dashboard/models.py`

### `Criterium`
Represents a combination of countries and email associated with them. Used to direct
emails to a specific admin (for example UK admin) mailbox.

### `Continent`
Represents a group of countries. Used in some internal forms, e.g. for filtering events.

----------------------------------------------------------------------------------------

## Recruitment application - `recruitment/models.py`

### `InstructorRecruitment`
Represents a recruitment of instructors for a given event ([`Event`](#event)).

### `InstructorRecruitmentSignup`
Represents an application of a single instructor for a given instructor recruitment
([`InstructorRecruitment`](#instructorrecruitment)).

----------------------------------------------------------------------------------------

## Consents application - `consents/models.py`

### `Term`
Represents a term people should give consent to.

### `TermOption`
Represents a response for a `Term` with custom text and boolean `agree` / `decline`
type.

### `Consent`
Represents a consent person gives (or not) to a given term. Intermediate table for M2M
between `Person` and `Term`, and `TermOption`.

----------------------------------------------------------------------------------------

## Community Roles application - `communityroles/models.py`

### `CommunityRoleConfig`
Stores configuration enforced when creating entries in `CommunityRole`. Determines what
"kind" of a role it is, for example "Instructor", or "Maintainer".

### `CommunityRoleInactivation`
Simple model represents reason for making a `CommunityRole` inactive.

### `CommunityRole`
Represents person's role in a community. It's an extension of `Task`, but instead of
events, it works for The Carpentries' community.

----------------------------------------------------------------------------------------

## Automated Emails application - `autoemails/models.py`

### `EmailTemplate`
Represents email template to be used by a triggered email action.

### `Trigger`
Simple model linking template with an email action. Email actions aren't models, so the
list of choices is maintained as `ACTION_CHOICES`.

### `RQJob`
Represents a [`python-rq`](https://python-rq.org/) job. This job is identified by UUID
and links to Redis entry maintained by RQ library.
