![](workshops/static/amy-logo.png)

[Software Carpentry](http://software-carpentry.org) is now running three events a week.
That number could double by the end of 2015
but only if we can
[streamline setup and organization](http://software-carpentry.org/blog/2014/12/plans-for-2015-workshop-organization.html).
The goal of this project is to build
a web-based workshop administration application using Django to do that.
It is not intended to be visible to the general public,
or even to instructors (at least initially --- we may add that later).
Instead,
the target audience is administrators,
most of whom are non-programmers,
who need to keep track of
what workshops are being arranged,
when they're supposed to occur,
who's teaching what,
and so on.

To get started:

1.  Install Django and its dependencies.

    ~~~
    $ sudo python -m pip install -r requirements.txt
    ~~~

2.  Setup your local database.  There are two ways you can do this.

    1. If you have access to the legacy data:

        1. Create an empty database by running:

           ~~~
           $ make migrations
           ~~~

        2. Fill that database by running:

           ~~~
           $ make import
           ~~~

    2. Otherwise set up the redacted data with:

       ~~~
       $ make database
       ~~~

3.  Create a administrator account.

    ~~~
    $ python manage.py createsuperuser
    ~~~

4.  Start a local Django development server by running:

    ~~~
    $ python manage.py runserver
    ~~~

5.  Open [http://localhost:8000/workshops/](http://localhost:8000/workshops/) in your browser and start clicking.

    Use the administrator account that you created.

**Note**: please [check with us](mailto:gvwilson@software-carpentry.org)
or open a [discussion issue](https://github.com/swcarpentry/amy/labels/discussion)
before adding any new features.
A few things have to get built in order to meet present demand,
and they should take precedence over everything else.
