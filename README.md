![](amy.png)

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

5.  Open http://localhost:8000/workshops/ in your browser and start clicking.

Amy's data model is mostly done.
What it needs now is views and controllers
so that workshop organizers can inspect, add, and correct data.
If you'd like to help,
please fork this repository and send a pull request,
or contact [Greg Wilson](gvwilson@software-carpentry.org).
