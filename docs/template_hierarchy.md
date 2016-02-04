Template hierarchy
==================

Here's a description of base templates, which almost all the other templates
inherit from.

## Base templates

There are multiple types of views in AMY:
* wide (e.g. 'Dashboard')
* wide with sidebar (e.g. 'All Events')
* narrow (e.g. event details)
* narrow without navigation bar (e.g. login page)

The base templates that correspond to them:
* `base_nonav_fixed.html`: for narrow (fixed-width) pages without navigation
  bar
* `base_nav_fixed.html`: for narrow (fixed-width) pages with navigation bar
  (ie. for logged in users)
* `base_nav_fluid.html`: for wide (fluid-width) pages with navigation bar and
  no sidebar
* `base_nav_fluid_sidebar.html`: for wide (fluid-width) pages with navigation
  bar and sidebar.

## Blocks available in base template

Django template blocks used across base templates:

* `extrastyle`: in `<head>`, when you need to load some additional CSS files or
  embed styles right into the page,
* `logo`: used in views that display AMY logo (dashboard, login page, log out
  page, password reset, etc.),
* `navbar`: used in templates that include navbar to… add a navbar,
* `main`: block that formats page header (`title` below) and page content
  (`content` below); `main` is redefined in `base_nav_fluid_sidebar.html` to
  include a `sidebar` block as well,
* `title`: by default, a `<h1>` with `{{ title}}` (don't confuse template block
  `title` with template variable `title`)
* `content`: for displaying page content,
* `extrajs`: for loading additional JavaScript files / codes; it's on the
  bottom of the page,
* `fluid-content`, `fluid-footer`, `fluid-navbar` (in `navigation_fixed.html`):
  blocks used for adding classes that change fixed-width behavior to
  fluid-width behavior; their content is specified in fluid templates.
