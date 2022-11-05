# Application design

## History

For a long time, AMY was almost single-application project: most of the logic,
models and views was contained in `workshops` application; there was also `api`
application and `extforms` for showing forms to the external users.

`workshops` grew to a massive size and needed splitting into smaller applications.
However, some previous design decisions made the split complicated. Namely versioning
system, provided by
[django-reversion](https://django-reversion.readthedocs.io/en/stable/), due to
model instance serialization, was not flexible when it came to data migration, and
very difficult when it came to move the underlying model to another app.

## Application structure

The new application structure contains:

* `api` - for CRUD API interface provided by [DRF](https://www.django-rest-framework.org/),
* `autoemails` - for automated emails application,
* `communityroles` - for community roles project application,
* `consents` - for consents project application,
* `dashboard` - for admin and instructor dashboard views,
* `extcomments` - for overriding some functions from
  [`django-contrib-comments`](https://django-contrib-comments.readthedocs.io/en/latest/quickstart.html)
  third party application for comments,
* `extforms` - for forms available externally, ie. for unauthenticated users; these
  forms are quite complex, and they represent models:
    * [`TrainingRequest`](./database_models.md#trainingrequest),
    * [`WorkshopRequest`](./database_models.md#workshoprequest),
    * [`WorkshopInquiryRequest`](./database_models.md#workshopinquiryrequest),
    * [`SelfOrganisedSubmission`](./database_models.md#selforganisedsubmission);
* `extrequests` - for all `*Request` objects (logic related to `WorkshopRequest` and
  `TrainingRequest`, but here's also where `WorkshopInquiryRequest` and
  `SelfOrganisedSubmission` models are defined),
* `fiscal` - for organisations and memberships (although most of the models are defined
  in `workshops` application; here is logic related to them),
* `recruitment` - for instructor selection project application,
* `reports` - for reports,
* `trainings` - for managing trainees and trainings,
* `workshops` - for persons and workshops management, including tasks and badges.

`workshops` application still takes a lead in many areas, and for now should be
considered "core" application. For example it defines many reusable classes,
like `TestBase` for base test case, or multiple model mixins. Globally used template
tags and utilities are also defined there.


### API
Application with CRUD-like views using
[Django Rest Framework](https://www.django-rest-framework.org/). It's not heavily used,
mostly for single cases when we need to provide async experience to the user via
JavaScript.

### Automated emails
A big project from 2019-2020. Contains actions that trigger sending emails on
specific time after the action has taken place.

TODO: document design

### Community Roles
2021-2022 Project to implement badge-like mechanism for assigning roles to people in
The Carpentries community.

### Consents
2021+ Project for providing more configurable and more descriptive consents for AMY
users.
2021+ Project for archiving person profile.

TODO: document design

### Dashboard
Contains generic views for admins, and logic for instructor dashboard.

### (External) Comments
Contains small extensions or changes applied to
[`django-contrib-comments`](https://django-contrib-comments.readthedocs.io/en/latest/quickstart.html)
application.

### External Requests, Forms
Applications together provide logic for forms non-AMY users fill out (`extforms`,
external forms). `extforms` provides forms, while `extrequests` provides admin views
and models (except for the models defined in `workshops` application).

Many of the views defined in `extrequests` contain logic for triggering automated
emails.

### Fiscal
Admin application for managing organisations and memberships.
Since 2021 Memberships project, handling memberships was extended and adjusted to The
Carpentries' needs.

### Recruitment
2021-2022 Instructor Selection project. Enables instructors to apply for teaching at
workshops directly with AMY, instead of using old techniques (a spreadsheet).

### Reports
Contains multiple admin views for, for example, listing issues with workshops or
duplicate persons.

### Trainings
Application for managing trainees (people in training) and trainings.

### Workshops
Core application for managing persons, events, badges, tasks, and roles.
