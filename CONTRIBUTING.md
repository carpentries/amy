Amy is an open source project, and we welcome contributions of all
kinds: new lessons, fixes to existing material, bug reports, and
reviews of proposed changes are all equally welcome.

By contributing, you are agreeing that Software Carpentry may
redistribute your work under [this license][license].  You also agree
to abide by our [contributor code of conduct][conduct].

If you would like to know what we need help with, please see the
[issues][issues] on GitHub.

## Getting Started

1.  Clone the repository:

    ~~~
    $ git clone https://github.com/swcarpentry/amy.git
    $ cd amy
    ~~~

2.  Install Django and other dependencies:

    ~~~
    $ python3 -m pip install --user -r requirements.txt
    ~~~

    If you're experienced Python programmer, feel free to create a
    Python3-compatible [virtualenv][virtualenv] for Amy and install
    dependencies from `requirements.txt`.

3.  Install [Bower][bower], the tool that manages Amy's JavaScript and CSS dependencies:

    ~~~
    $ sudo npm install -g bower
    ~~~

    You may need some additional dependencies to install [Bower][bower], such as [NodeJS][nodejs] and [npm][npm].

    **Note**: if you don't want to use `sudo`, you can install `bower`
    locally. You'll need to set up your `$PATH` correctly, though. Look
    [here][fixing-npm-permissions] for details.

4.  Setup your local database wit redacted (development-ready) data with:

    ~~~
    $ make database
    ~~~

5.  Create an administrator account:

    ~~~
    $ python3 manage.py createsuperuser
    ~~~

6.  Start a local Django development server by running:

    ~~~
    $ make serve
    ~~~

    **Note**:  this also installs front-end dependencies for Amy, such as jQuery or Bootstrap.

7.  Open <http://localhost:8000/workshops/> in your browser and start clicking.

    Use the administrator account that you created.

## Upgrading

1.  Update the code:

    1.  Get the list of changes:

        ~~~
        $ git fetch
        ~~~

    2.  Look for the newest tag:

        ~~~~
        $ git tag -n
        ~~~~

    3.  Get the code from the newest tag:

        ~~~~
        $ git checkout tags/<tag_name>
        ~~~~

2.  Update dependencies:

    ~~~
    $ python3 -m pip install --user --upgrade -r requirements.txt
    ~~~

    **Note**: front-end dependencies will be updated as soon as you run `make serve`.

3.  (Optional) make the development-ready database:

    ~~~
    $ make database
    ~~~

3.  Run database migrations:

    ~~~~
    $ python3 manage.py migrate
    ~~~~

4.  Enjoy your new version of Amy:

    ~~~
    $ make serve
    ~~~

## Coding Guidelines

*   Format all dates as YYYY-MM-DD.

[bower]: http://bower.io/
[conduct]: CONDUCT.md
[fixing-npm-permissions]: https://docs.npmjs.com/getting-started/fixing-npm-permissions#option-2-change-npm-s-default-directory-to-another-directory
[issues]: https://github.com/swcarpentry/amy/issues
[license]: LICENSE.md
[nodejs]: https://nodejs.org/
[npm]: https://www.npmjs.com/
[virtualenv]: https://virtualenv.pypa.io/en/latest/userguide.html
