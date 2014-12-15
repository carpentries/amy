<img src="https://raw.githubusercontent.com/gvwilson/amy/master/amy-logo.png" />

[Software Carpentry](http://software-carpentry.org) is now running three events a week,
and that number could double by the end of 2015 ---
*if* we can
[streamline setup and organization](http://software-carpentry.org/blog/2014/12/plans-for-2015-workshop-organization.html).
The goal of this project is to build
a web-based workshop administration application using Django.
It is not intended to be visible to the general public,
but rather to be used by administrators to keep track of
what workshops are being arranged,
when they're supposed to occur,
who's teaching what,
and so on.

To get started:

1.  Install Django and its dependencies.

2.  Setup your local database.  There are two ways you can do this.

    1. If you have access to the secret data:

        1. Create an empty database by running:

           ~~~
           make migrations
           ~~~

        2. Fill that database by running:

           ~~~
           make import
           ~~~

    2. Otherwise setup the redacted data with:

       ~~~
       make database
       ~~~

4.  Start a local Django development server by running:

    ~~~
    python manage.py runserver
    ~~~

5.  Open [http://localhost:8000/workshops/](http://localhost:8000/workshops/) in your browser and start clicking.

Amy's data model is mostly done.
What it needs now is views and controllers
so that workshop organizers can inspect, add, and correct data.
If you'd like to help,
please fork this repository and send a pull request,
or contact [Greg Wilson](gvwilson@software-carpentry.org).

----

Pages for Admin Tool

*  Landing page
    *   List of provisional upcoming events (that need instructors)
    *   List of confirmed upcoming events
    *   Navigation links for other pages

*  Site Index
    *   Table showing:
        *   Domain name (link to domain)
        *   Site name (link to Site Details for that site)
        *   Number of past events
        *   Number of future events
    *   Link to Add Site Form

*  Site Details
    *   Summary (domain name, site name)
    *   Lat/long
        *   Problematic: some sites don't have one, and others may have many
    *   List of links to past events
    *   List of links to future events
    *   (Optional) some way to show instructors whose airport is within XXX km of that location
    *   Wiki page for notes about site
        *   Contact person, location, etc., can change from workshop to workshop, so use a free-form wiki page

*  Add Site Form
    *   Domain name
    *   Site name
    *   ...submission sends to Site Details page for site

*  Event Index
    *   Table showing:
        *   Site name (link to Site Details page)
        *   Event slug (link to Event Details page)
        *   Instructor names (each links to Person Details page)
    *   Paginated
    *   Link to Add Event Form

*  Event Details
    *   Site name (link to Site Details page)
    *   Slug
    *   GitHub website repository URL (editable)
    *   GitHub pages website (inferred)
    *   Kind (pulldown for "SWC", "DC", "WiSE", etc.)
    *   Host contact name and email (hopefully from the Person table)
    *   Instructor names (each links to Person Details page)
    *   Add instructors (multi-selection pulldown)
    *   Helper names (each links to Person Details page)
    *   Add helpers (multi-selection pulldown)
    *   Start date (calendar)
    *   End date (calendar)
    *   Eventbrite ID (editable, links to Eventbrite page)
    *   Links to pre- and post-assessment forms (if they exist)
    *   Link to instructor post-assessment forms (if they exist)
    *   Link to Google spreadsheet checklist (if it exists)
    *   Buttons to create pre- and post-assessment forms and checklist (if they don't exist)
    *   Note: we'll no longer try to track restricted vs. unrestricted enrolment (since there are too many variations)

*  Add Event Form
    *   Site name (link to Site Details page)
    *   Slug (editable right up until the moment we commit to dates)
    *   GitHub website repository URL (editable)
    *   GitHub pages website (inferred)
    *   Kind (pulldown for SWC, DC, WiSE, etc.)
    *   Instructor names (each links to Person Details page)
        *   Some way to distinguish lead instructor from others
    *   Add instructors (multi-selection pulldown)
    *   Helper names (each links to Person Details page)
    *   Add helpers (multi-selection pulldown)
    *   Start date (calendar)
    *   End date (calendar)
    *   *Or* provisional dates (while we're still trying to book things)
    *   Tick box for "Eventbrite registration" vs. "local registration"
    *   Wiki page (for free-form text notes)
    *   ...submission sends to Event Details page for event
    *   ...and creates slug@software-carpentry.org email address (?)

*  Person Index
    *   Table showing:
        *   Personal name (editable)
        *   Middle name (editable)
        *   Last name (editable)
        *   Email address (editable)
        *   Instructor or not (and if so, how many times have they taught?)
        *   Link to Person Details page
        *   Submit button (per person, so only one editable at a time)
    *   Paginated
    *   Alphabetical index (jump to...) on last name
    *   Link to Add Person Form
    *   Link to Upload Person Form

*  Add Person Form
    *   Table allowing entry of:
        *   Personal name (editable)
        *   Middle name (editable)
        *   Last name (editable)
        *   Email address (editable)
        *   Event (editable, optional)
        *   Role (pulldown, required if Event provided)
    *   Add Row button
    *   Submit button
    *   ...submission returns to Add Person Form with message about people added

*  Upload Person Form
    *   Text box to enter CSV data
    *   Choose File button to select CSV file
    *   Pulldown to select Event (optional)
    *   ...submission creates populated Add Person Form
    *   ...if Event selected, all Roles in Add Person Form initialized to "learner"

*  Person Details
    *   Personal name (editable)
    *   Middle name (editable)
    *   Family name (editable)
    *   Email address (editable)
    *   Instructor or not (and if so, how many times have they taught)
    *   Gender (pulldown of "male", "female", "other", "prefer not to say")
    *   Active (checkbox)
    *   Airport (pulldown)
        *   Note: this is just to give us an idea of where the person lives
    *   GitHub ID (editable)
    *   Twitter ID (editable)
    *   Website URL (editable)
    *   Checkboxes for:
        *   Shell
        *   Python
        *   R
        *   MATLAB
        *   Git
        *   Mercurial
        *   SQL
    *   Submit button
    *   ...submission returns to Person Details page

*  Cohort Index
    *   Table showing:
        *   Cohort name
        *   Start date
        *   End date
        *   Number enrolled
        *   Number complete
        *   Number incomplete
        *   Link to Cohort Details page
    *   Link to Add Cohort Form

*  Cohort Details
    *   Cohort name
    *   Start date
    *   End date
    *   Number enrolled
    *   Number complete
    *   Number incomplete
    *   Table showing:
        *   Trainee name (link to Person Details page)
        *   Trainee status (pulldown)
    *   Add trainees (multi-select pulldown)

*  Badge Index
    *   Table showing:
        *   Badge name (editable)
        *   Badge title (editable)
        *   Criteria (editable)
        *   Link to Badge Details page
    *   Add Row button
    *   Submit button
    *   ...submission returns to Badge Index

*  Badge Details
    *   Badge name (link to Badge Index page)
    *   Table showing:
        *   Recipient (link to Person Details page)
        *   Date of award (calendar)
    *   Add Row button
    *   Submit button
    *   ...submission returns to Badge Details

*  Airport Index
    *   Table showing:
        *   IATA code
        *   Airport name (editable)
        *   Latitude (editable)
        *   Longitude (editable)
    *   Add Row button
    *   Submit button
    *   (Optional) some way to show instructors within XXX km of that location
    *   ...submission returns to Airport Index page

*  Admin
    *   Add accounts, password re-set, etc.
