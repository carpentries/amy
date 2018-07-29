Template hierarchy
==================

Here's a description of base templates, which almost all the other templates
inherit from.

## Base templates

All templates use [fluid container](https://getbootstrap.com/docs/4.1/layout/overview/)
from [Bootstrap 4.1](https://getbootstrap.com/docs/4.1/).

There are multiple types of views in AMY:
* wide (e.g. 'Dashboard') -- `base_nav.html`,
* wide with sidebar (e.g. 'All Events') -- `base_nav_sidebar.html`,
* wide with two content columns (e.g. `EventRequest` accept view, rarely used) -- `base_nav_twocolumn.html`.

These templates all inherit from `base.html`, which holds the HTML structure,
includes CSS styles and JS code, displays messages, footer, etc.

The `base_nav.html` is nothing more but `base.html` extended with a navigation.
Navigation changes depending on user - one navigation bar
(`navigation.html`) exists for admin users, a different one
(`navigation_trainee.html`) exists for trainees. A correct navigation bar is
being included in `base_nav.html`.

## Blocks available in base template

Django template blocks used in `base.html` template:

* `extrastyle` in `<head>`, when you need to load some additional CSS files or
  embed styles right into the page,
* `extrajs` in `<head>`, for loading additional JavaScript files / codes,
* `navbar` used in templates that include a navigation bar,
* `main` with all the main content in case someone really needs to change it
  (caution: quite a lot is going on in this block, make sure you don't brake
  it),
* `leftcolumn` for adding a sidebar or a column (used in
  `base_nav_sidebar.html` and `base_nav_twocolumn.html`),
* `maincolumn` for changing main content column grid,
* `logo` used in views that display AMY logo (login page, log out
  page, password reset, etc.),
* `title` to display `<h1>` tag with page title,
* `content` for displaying page content.

## Widgets

Additionally there were created widgets to support some of the tedious
components:
* `assignment.html` displays a dropdown to change filtering events assigned to
  specific person (user, unassigned, or no filtering),
* `assignment_modal.html` displays a modal "window" on the page; this window
  is used to select person assigned to specified object,
* `pagination.html` displays a neat button groups split with "..." to not show
  too much pages at once.
