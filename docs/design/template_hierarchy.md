# Templates

AMY uses [Django templating system](https://docs.djangoproject.com/en/4.1/topics/templates/)
and Django templating engine.

Templates in AMY are kept in `amy/templates/` directory, conveniently grouped by
application in subdirectories (`comments` - from `extcomments`, `communityroles`,
`consents`, `dashboard`, `forms` - from `extforms`, `fiscal`, `recruitment`, `reports`,
`requests` - from `extrequests`, `trainings`, `workshops`). There are also directories
not related to internal AMY applications:

* `account` - contains templates related to login/logout/password reset pages,
* `bootstrap4` - contains templates and/or includes for widgets used by
  [Django Crispy Forms](https://github.com/django-crispy-forms/django-crispy-forms),
* `includes` - contains a bunch of reusable "components" - Django HTML templates,
* `mailing` - contains templates used to generate emails automatically sent when users
  submit [external forms](./application_design.md#external-requests-forms),
* `markdownx` - contains some overridden templates for
  [django-markdown](https://neutronx.github.io/django-markdownx/) package.

Usually, unsless the template is an includable, one template corresponds to one view,
that's why they are grouped in per-application directories.

The rest of the files stored directly in `amy/templates/` directory are base templates.
Here's a description of them, which almost all the other templates inherit from.

## Base templates

All templates use [fluid container](https://getbootstrap.com/docs/4.6/layout/overview/)
from [Bootstrap 4](https://getbootstrap.com/docs/4.6/).

There are multiple types of views in AMY:

* wide (e.g. 'Dashboard') -- `base_nav.html`,
* wide with sidebar (e.g. 'All Events') -- `base_nav_sidebar.html`,
* wide with two content columns (e.g. `WorkshopRequest` accept view) --
  `base_nav_twocolumn.html`.

These templates all inherit from `base.html`, which holds the HTML structure,
includes CSS styles and JS code, displays messages, footer, etc.

The `base_nav.html` is nothing more but `base.html` extended with a navigation.
Navigation changes depending on user - one navigation bar
(`navigation.html`) exists for admin users, a different one
(`navigation_instructor_dashboard.html`) exists for instructors/trainees.
A correct navigation bar is being included in `base_nav.html` and every
instructor-enabled template (e.g. Auto Update Profile form, Upcoming Teaching
Opportunities page, etc.).

There are also these templates available at the top-level template directory:

* `base_forms.html` - base template for external forms (workshop request, workshop
  inquiry request, self-organised submission and training request),
* `generic_form.html` - a default form used by `AMYCreateView` and `AMYUpdateView`
  (base views for creating and updating entities),
* `generic_form_with_comments.html` - the same as `generic_form.html`, but additionally
  contains a section with comments provided by
  [extcomments application](./application_design.md#external-comments),
* `pagination.html` - displays a neat button groups split with "..." to not show
  too much pages at once.


## Blocks available in base template

Django template blocks used in `base.html` template:

* `extrastyle` in `<head>`, when you need to load some additional CSS files or
  embed styles right into the page,
* `extrajs` on bottom of `<body>`, for loading additional JavaScript files / codes,
* `navbar` used in templates that include a navigation bar,
* `main` with all the main content in case someone really needs to change it,
* `leftcolumn` for adding a sidebar or a column (used in `base_nav_sidebar.html`),
* `maincolumn` for changing main content column grid,
* `logo` used in views that display AMY logo (login page, log out page, password reset,
  etc.) - see `account` in [Templates](#templates),
* `title` to display `<h1>` tag with page title,
* `content` for displaying page content.

## Widgets

There are multiple reusable components available in `amy/templates/includes` directory:

* `assigned_to.html` - displays whom has the entity (event, workshop request, workshop
  inquiry request, self-organised submission) been assigned to; displays a form to
  change the assignee,
* `assignment_modal.html` - displays a modal "window" on the page; this window
  is used to select person assigned to specified entity (event, workshop request,
  workshop inquiry request, self-organised submission),
* `assignment.html` - displays a dropdown to change filtering events assigned to
  specific person (user, unassigned, or no filtering),
* `attendance_email_href.html` - renders a `mailto:` link with provided list of emails
  as recipients and predefined text in email body; used in event details view and in
  workshop issues report,
* `comments.html` - displays comments and form for adding comments for a given entity,
* `country_flag.html` - renders county name with this country's flag,
* `curriculum.html` - displays curriculum as
  a [Boostrap badge][bootstrap_badge],
* `event_details_table.html` - displays a table with event details,
* `event_import_update_from_url.html` - modal for importing event details from a given
  URL address,
* `instructor_profile_snapshot.html` - as name suggests, this is a snapshot of person's
  instructor profile used in
  [Instructor Selection](./projects/2021_instructor_selection.md) project, on instructor
  dashboard,
* `instructor_role_badge.html` - small component displaying information about active
  or inactive instructor badge on for a person,
* `instructor_selection_summary.html` - a summary of instructor selection for a given
  event; this is displayed in event's jumbo header,
* `instructorrecruitment.html` - a representation of single `InstructorRecruitment`
  model instance,
* `last_modified.html` - used by `last_modified` template tag to display audit log
  information (when entity was created, when it was last modified),
* `logo.html` - AMY logo, used by user-facing external forms,
* `merge_radio.html` - used to display HTML `radio` element in Person/Event merge views,
* `request_host_person.html` - used to display person from the database matching the
  person requesting a workshop,
* `request_institution.html` - used to display organisation from the database matching
  the institution of person requesting a workshop,
* `requests_bottom_action_btns.html` - displays a group of buttons for accepting,
  discarding, etc. workshop requests, workshop inquiry requests, and self-organised
  submissions,
* `selforganisedsubmission_details.html` - displays a table with self-organised
  submission details,
* `tag.html` - displays a [Boostrap badge][bootstrap_badge] of a tag,
* `teaching_opportunity.html` - displays details of instructor recruitment instance used
  in [Instructor Selection](./projects/2021_instructor_selection.md) project, on
  instructor dashboard,
* `template_response.html` - provides a dropdown with templates used for automatic reply
  to a workshop request,
* `tracker.html` - contains [Matomo](https://matomo.org/) tracker JavaScript code,
* `training_progresses_inline.html` - displays person's progress in training with
  various training requirements,
* `trainingrequest_details.html` - displays a table with training request details,
* `workshopinquiry_details.html` - displays a table with workshop inquiry request
  details,
* `workshoprequest_details.html` - displays a table with workshop request details.


[bootstrap_badge]: https://getbootstrap.com/docs/4.6/components/badge/
