# Models hierarchy according to application and versioning system

For a long time, AMY was almost single-application project: most of the logic,
models and views was contained in `workshops` application; there was also `api`
application and `pydata` for PyData integration, and `extforms` for showing
forms to the external users.

In the meantime, `workshops` grew to a massive size and needed splitting into
smaller applications. However, some previous design decisions made the split
complicated. Namely versioning system, provided by [django-reversion][], due
to [model instance serialization][], is not flexible when it comes to data
migration, and very hard when it comes to underlying model move to another app.

Not all models have versioning system enabled. Those that don't were moved to
corresponding applications.

The new application structure contains:
* `api` - as previously for API,
* `dashboard` - for admin and trainee dashboard views,
* `extforms` - as previously for forms available externally, ie. for
  unauthenticated users,
* `extrequests` - for all `*Request` objects (`EventRequest`,
`EventSubmission`, `DCSelfOrganizedEventRequest`, `ProfileUpdateRequest`, by
the way all these models are deprecated and to be removed in future,
`InvoiceRequest`, `WorkshopRequest`, and `TrainingRequest`),
* `fiscal` - for organizations, memberships, and sponsorships,
* `pydata` - as previously for PyData integration,
* `reports` - for reports,
* `trainings` - for managing trainees and trainings,
* `workshops` - for persons and workshops management, including tasks and
badges.

`workshops` application still takes a lead in many areas, and for now should be
considered "core" application. For example it defines many reusable classes,
like `TestBase` for base test case, or multiple model mixins.

## Versioned models

Below you'll find list of models with versioning enabled; they were originally
in the `workshops` application and stayed there. Their logical belonging is
indicated in this tree below.

* `extrequests`:
    * `TrainingRequest`,
    * `InvoiceRequest`,
    * `WorkshopRequest`,
    * non-versioned, but their removal causes huge problems with migration,
      since they're referenced by `WorkshopRequest`:
        * `AcademicLevel`,
        * `ComputingExperienceLevel`,
* `fiscal`:
    * `Membership`,
    * `Organization`,
    * non-versioned, but it's used in M2M relationship as `through` table, and
      therefore is difficult to move it around:
        * `Sponsorship`,
* `trainings`:
    * `TrainingRequirement`,
    * `TrainingProgress`,
* `workshops`:
    * `Airport`,
    * `Person`,
    * `Event`,
    * `Task`.

## Non-versioned models

Below you'll find list of models without versioning system; they were
originally created in the `workshops` application, but were moved to the
corresponding apps.

* `extrequests`:
    * `DataAnalysisLevel`,
    * `DCWorkshopTopic`,
    * `DCWorkshopDomain`,
    * `ProfileUpdateRequest`,
    * `EventRequest`,
    * `EventSubmission`,
    * `DCSelfOrganizedEventRequest`,
* `fiscal`:
    * -
* `trainings`:
    * -
* `workshops`:
    * `Language`,
    * `Lesson`,
    * `Qualification`,
    * `Badge`,
    * `Award`,
    * `Curriculum`,
    * `Role`,
    * `Tag`,
    * `KnowledgeDomain`.
