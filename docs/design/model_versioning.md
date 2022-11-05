# Model versioning

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

Not all models have versioning system enabled. Those that don't were moved to
corresponding applications.

Go to [application design](./application_design.md) for more details on how the
applications are set up.

## List of versioned models

Below you'll find list of models with versioning enabled.

* `recruitment`:
    * `InstructorRecruitment`,
    * `InstructorRecruitmentSignup`,
* `workshops`:
    * `Organization`,
    * `Membership`,
    * `Airport`,
    * `Person`,
    * `Event`,
    * `Task`.
    * `TrainingRequest`,
    * `TrainingRequirement`,
    * `TrainingProgress`,
    * `WorkshopRequest`.
