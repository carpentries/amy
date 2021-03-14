# Database models

This document describes and summarizes roles of database models used in AMY
(`workshops/models.py`).

## Mixins

Following classes are used to extend Django models with the same features:

* `PermissionsMixin`: Django mechanism for extending custom user classes,
see [documentation](https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#custom-users-and-permissions).
* `AssignmentMixin`: adds `assigned_to` field to the model.
* `ActiveMixin`: adds `active` boolean field to the model.
* `CreatedUpdatedMixin`: adds `created_at` and `last_updated_at` datetime
fields to the model.

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
### `Person` and `PersonManager`
### `Event`
### `Role`
### `Task` and `TaskManager`
### `Lesson`
### `Qualification`
### `Badge`
### `Award`
### `KnowledgeDomain`
### `Tag`
### `Language`

## Requests and form-models
### `EventRequest`
### `EventSubmission`
### `DCSelfOrganizedEventRequest`
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
