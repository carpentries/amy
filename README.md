<img src="https://raw.githubusercontent.com/gvwilson/amy/master/logo.png" />

A web-based workshop administration application built using Django.
To get started:

1.  Install Django and its dependencies.

2.  Create an empty database by running:

    ~~~
    make migrations
    ~~~

3.  Fill that database by running:

    ~~~
    make import
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

A.  Landing page
    *   List of provisional upcoming events (that need instructors)
    *   List of confirmed upcoming events
    *   Navigation links for other pages

B.  Site Index
    *   Table showing:
        *   Domain name (link to domain)
        *   Site name (link to Site Details for that site)
        *   Number of past events
        *   Number of future events
    *   Link to Add Site Form

C.  Site Details
    *   Summary (domain name, site name)
    *   Lat/long
        *   Problematic: some sites don't have one, and others may have many
    *   List of links to past events
    *   List of links to future events
    *   (Optional) some way to show instructors whose airport is within XXX km of that location
    *   Wiki page for notes about site
        *   Contact person, location, etc., can change from workshop to workshop, so use a free-form wiki page

D.  Add Site Form
    *   Domain name
    *   Site name
    *   ...submission sends to Site Details page for site

E.  Event Index
    *   Table showing:
        *   Site name (link to Site Details page)
        *   Event slug (link to Event Details page)
        *   Instructor names (each links to Person Details page)
    *   Paginated
    *   Link to Add Event Form

F.  Event Details
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

G.  Add Event Form
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

H.  Person Index
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

I.  Add Person Form
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

J.  Upload Person Form
    *   Text box to enter CSV data
    *   Choose File button to select CSV file
    *   Pulldown to select Event (optional)
    *   ...submission creates populated Add Person Form
    *   ...if Event selected, all Roles in Add Person Form initialized to "learner"

K.  Person Details
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

L.  Cohort Index
    *   Table showing:
        *   Cohort name
        *   Start date
        *   End date
        *   Number enrolled
        *   Number complete
        *   Number incomplete
        *   Link to Cohort Details page
    *   Link to Add Cohort Form

M.  Cohort Details
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

N.  Badge Index
    *   Table showing:
        *   Badge name (editable)
        *   Badge title (editable)
        *   Criteria (editable)
        *   Link to Badge Details page
    *   Add Row button
    *   Submit button
    *   ...submission returns to Badge Index

O.  Badge Details
    *   Badge name (link to Badge Index page)
    *   Table showing:
        *   Recipient (link to Person Details page)
        *   Date of award (calendar)
    *   Add Row button
    *   Submit button
    *   ...submission returns to Badge Details

P.  Airport Index
    *   Table showing:
        *   IATA code
        *   Airport name (editable)
        *   Latitude (editable)
        *   Longitude (editable)
    *   Add Row button
    *   Submit button
    *   (Optional) some way to show instructors within XXX km of that location
    *   ...submission returns to Airport Index page

Z.  Admin
    *   Add accounts, password re-set, etc.
