![](amy/static/amy-logo.png)

![](https://travis-ci.org/carpentries/amy.svg?branch=master)
[![](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![](https://img.shields.io/badge/django-2.2+-blue.svg)](https://www.djangoproject.com/)
[![](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE.md)

AMY is a web-based workshop administration application for [The Carpentries][tc]
and related projects.  Its target audience is workshop
coordinators, most of whom are non-programmers, who need to keep track
of what workshops are being arranged, when they're supposed to occur,
who's teaching what, and so on.

AMY is built using [Django][django] with Python 3, with a bit of Javascript and
other things thrown in.  If you would like to help, please read:

*   the setup instructions below,

*   the [contributor guidelines](CONTRIBUTING.md), and

*   our [contributor code of conduct](CODE_OF_CONDUCT.md).

Please [check with us][contact-address] or open an [issue][issues]
before starting work on new features.

## Getting Started

1.  Clone the repository:

    ~~~
    $ git clone https://github.com/swcarpentry/amy.git
    $ cd amy
    ~~~

1.  Install Django and other dependencies:

    ~~~
    $ python -m pip install --user -r requirements.txt
    ~~~

    **Recommended:**
    If you're experienced Python programmer, feel free to create a
    Python3-compatible [virtualenv][virtualenv] / [venv][venv] for AMY and install
    dependencies from `requirements.txt`.

1.  Install [yarn][yarn], the tool that manages AMY's JavaScript and CSS dependencies. [You can install it here][yarn].

1.  Set up your local database with fake (development-ready) data with:

    ~~~
    $ make dev_database
    ~~~

1. Create cache tables for use with the database cache backend.

    ~~~
    $ python manage.py createcachetable
    ~~~

1.  Create an administrator account:

    ~~~
    $ python manage.py createsuperuser
    ~~~

1.  Start a local Django development server by running:

    ~~~
    $ make serve
    ~~~

    **Note**:  this also installs front-end dependencies for AMY, including [jQuery][jquery] and [Bootstrap][bootstrap] ([full list here](https://github.com/swcarpentry/amy/blob/develop/package.json)).

1.  Open <http://127.0.0.1:8000/workshops/> in your browser and start clicking.

    Use the administrator account that you created.

## Upgrading

1.  Update the code:

    1.  Get the list of changes:

        ~~~
        $ git fetch
        ~~~

    1.  Look for the newest tag:

        ~~~~
        $ git tag -n
        ~~~~

    1.  Get the code from the newest tag:

        ~~~~
        $ git checkout tags/<tag_name>
        ~~~~

1.  Update dependencies front-end and back-end dependencies:

    ~~~
    $ make upgrade
    ~~~

1.  (Optional) make fresh development-ready database:

    ~~~
    $ make dev_database
    ~~~

    **Note**:  this command requires removing (by hand) the old database file.

1.  Run database migrations:

    ~~~~
    $ python manage.py migrate
    ~~~~

1.  Enjoy your new version of AMY:

    ~~~
    $ make serve
    ~~~

[bootstrap]: https://getbootstrap.com/
[contact-address]: mailto:team@carpentries.org
[django]: https://www.djangoproject.com
[jquery]: https://jquery.com/
[fixing-npm-permissions]: https://docs.npmjs.com/getting-started/fixing-npm-permissions#option-2-change-npm-s-default-directory-to-another-directory
[issues]: https://github.com/swcarpentry/amy/issues
[tc]: https://carpentries.org/
[virtualenv]: https://virtualenv.pypa.io/en/latest/userguide.html
[venv]: https://docs.python.org/3/library/venv.html
[yarn]: https://yarnpkg.com/lang/en/docs/install
