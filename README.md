![](workshops/static/amy-logo.png)

![](https://travis-ci.org/swcarpentry/amy.svg?branch=master)

[Software Carpentry](http://software-carpentry.org) is running three events
a week.  The number could double by the end of 2015, but only if we can
[streamline setup and organization](http://software-carpentry.org/blog/2014/12/plans-for-2015-workshop-organization.html).
The goal of this project is to build a web-based workshop administration
application using Django.  It is not intended to be visible to the
general public, or even to instructors (at least initially — we may add that
later).  Instead, the target audience is administrators, most of whon are
non-programmers, who need to keep track of what workshops are being arranged,
when they're supposed to occur, who's teaching what, and so on.

# Getting started

1. Clone the repository:

    ~~~
    $ git clone https://github.com/swcarpentry/amy.git
    $ cd amy
    ~~~

2. Install Django and other dependencies:

    ~~~
    $ python3 -m pip install --user -r requirements.txt
    ~~~

    If you're experienced Python programmer, feel free to create a Python3-compatible [virtualenv](https://virtualenv.pypa.io/en/latest/userguide.html) for Amy and install dependencies from `requirements.txt`.

3. Install [Bower](http://bower.io/) — the tool that manages Amy's JavaScript and CSS dependencies:

    ~~~
    $ sudo npm install -g bower
    ~~~

    You may need some additional dependencies to install [Bower](http://bower.io/), such as [NodeJS](https://nodejs.org/) and [npm](https://www.npmjs.com/).

    **Note**: if you don't want to use `sudo`, you can install `bower` locally. You'll need to set up your `$PATH` correctly, though. Look [here](https://docs.npmjs.com/getting-started/fixing-npm-permissions#option-2-change-npm-s-default-directory-to-another-directory) for details.

4. Setup your local database.  There are two ways you can do this:

    1. If you have access to the legacy data:

        1. Create an empty database by running:

            ~~~
            $ make migrations
            ~~~

        2. Fill that database by running:

            ~~~
            $ make import
            ~~~

    2. Otherwise set up the redacted (development-ready) data with:

        ~~~
        $ make database
        ~~~

5. Create an administrator account:

    ~~~
    $ python3 manage.py createsuperuser
    ~~~

6. Start a local Django development server by running:

    ~~~
    $ make serve
    ~~~

    **Note**:  this also installs front-end dependencies for Amy, such as jQuery or Bootstrap.

7. Open [http://localhost:8000/workshops/](http://localhost:8000/workshops/) in your browser and start clicking.

    Use the administrator account that you created.

# Upgrading

1. Update the code:

    1. Get the list of changes:

        ~~~
        $ git fetch
        ~~~

    2. Look for the newest tag:

        ~~~~
        $ git tag -n
        ~~~~

    3. Get the code from the newest tag:

        ~~~~
        $ git checkout tags/<tag_name>
        ~~~~

2. Update dependencies:

    ~~~
    $ python3 -m pip install --user --upgrade -r requirements.txt
    ~~~

    **Note**: front-end dependencies will be updated as soon as you run `make serve`.

3. (Optional) use newer development-ready database:

    ~~~
    $ make database
    ~~~

3. Run database migrations:

    ~~~~
    $ python3 manage.py migrate
    ~~~~

4. Enjoy your new version of Amy:

    ~~~
    $ make serve
    ~~~

# Contact

Please [check with us](mailto:gvwilson@software-carpentry.org) or open
a [discussion issue](https://github.com/swcarpentry/amy/labels/discussion)
before adding any new features.

A few things have to get built in order to meet present demand, and they
should take precedence over everything else.
