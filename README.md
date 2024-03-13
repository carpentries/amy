![](amy/static/amy-logo.png)

![develop branch](https://github.com/carpentries/amy/actions/workflows/python-test.yml/badge.svg?branch=develop)
[![](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![](https://img.shields.io/badge/django-2.2+-blue.svg)](https://www.djangoproject.com/)
[![](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE.md)

AMY is a web-based workshop administration application for [The Carpentries][tc]
and related projects.  Its target audience is workshop
coordinators, most of whom are non-programmers, who need to keep track
of what workshops are being arranged, when they're supposed to occur,
who's teaching what, and so on.

AMY is built using [Django][django] with Python 3, with a bit of Javascript and
other things thrown in.  If you would like to help, please read:

* the setup instructions below,

* the [contributor guidelines](.github/CONTRIBUTING.md), and

* our [contributor code of conduct](.github/CODE_OF_CONDUCT.md).

Please [check with us][contact-address] or open an [issue][issues]
before starting work on new features.

## Getting Started

1. Clone the repository:

    ~~~
    git clone https://github.com/carpentries/amy.git
    cd amy
    ~~~

1. Configure git to automatically ignore revisions in the `.git-blame-ignore-revs`:

    ~~~
    git config blame.ignoreRevsFile .git-blame-ignore-revs
    ~~~

1. Install [Pipenv](https://pipenv.pypa.io/en/latest/):

    ~~~
    python -m pip install --user pipenv
    ~~~

1. Install Python dependencies:

    ~~~
    pipenv sync --dev
    ~~~

    **Note:**
    Pipenv will create a new virtual environment for this installation, so you don't
    have to create one yourself.
    The `--dev` flag installs development dependencies, required e.g. for testing.

1. Install [node][nodejs] for front-end packages management.

1. Install CSS, JS dependencies with (`npm` was installed in previous step when you
    installed `node`):

    ~~~
    npm install
    ~~~

1. Start running a local instance of Postgres and Redis. This requires Docker to be installed locally.  Redis is required to have certain features (like creating a new person and viewing a workshop request) work correctly.

    ~~~
    docker compose -f docker/docker-compose.yml -p amy up -d database redis
    ~~~

1. Set up your local database with fake (development-ready) data.  This will create a superuser with "admin" as both the username and password.

    ~~~
    pipenv run make dev_database
    ~~~

1. Start a local Django development server by running:

    ~~~
    pipenv run make serve
    ~~~

    **Note**:  this also installs front-end dependencies for AMY, including [jQuery][jquery] and [Bootstrap][bootstrap] ([full list here](https://github.com/carpentries/amy/blob/develop/package.json)).

1. Open <http://127.0.0.1:8000/workshops/> in your browser and start clicking. Use the default "admin" as username and password.

1. Shut down the local server by typing `Ctrl-C`.  Shut down the Docker Redis instance with:

    ~~~
    docker compose -f docker/docker-compose.yml -p amy down
    ~~~

## How to build the docker image?

```shell
LAST_COMMIT=`git rev-parse --short HEAD`
docker build -t amy:latest -t amy:${LAST_COMMIT} --label commit=${LAST_COMMIT} -f docker/Dockerfile .
```

First command sets `LAST_COMMIT` environment variable to short commit hash of the
last commit in the repository.

Second command builds `docker/Dockerfile` in `.` as a context (should be your repository
directory) with tags `amy:latest` and `amy:LAST_COMMIT`.

## Upgrading

1. Update the code:

    1. Get the list of changes:

        ~~~
        git fetch
        ~~~

    1. Look for the newest tag:

        ~~~~
        git tag -n
        ~~~~

    1. Get the code from the newest tag:

        ~~~~
        git checkout tags/<tag_name>
        ~~~~

1. Update dependencies front-end and back-end dependencies:

    ~~~
    pipenv run make upgrade
    ~~~

1. (Optional) make fresh development-ready database:

    ~~~
    pipenv run make dev_database
    ~~~

1. Run database migrations:

    ~~~~
    pipenv run python manage.py migrate
    ~~~~

1. Enjoy your new version of AMY:

    ~~~
    pipenv run make serve
    ~~~

## Start hacking on email automation

1. Make sure you have Redis running. See instructions above.

1. Create dev database (it will add a super user and predefined database entries, too!):

    ```shell
    pipenv run make dev_database
    ```

1. Run the server:

    ```shell
    pipenv run python manage.py runserver
    ```

1. Run the RQ worker and scheduler (use separate terminals or processes for each
   command):

    ```shell
    pipenv run python manage.py rqworker
    pipenv run python manage.py rqscheduler
    ```

## Run accessibility tests locally

Accessibility tests are run with [Pa11y](https://pa11y.org) and optionally [Google Lighthouse](https://github.com/GoogleChrome/lighthouse) as part of the CI process. It's sometimes helpful to run these programs locally to debug or test changes. For more information on the tests, see the [accessibility tests documentation](docs/accessibility_testing.md)

For both Lighthouse and pa11y tests, Google Chrome or Chromium must be installed. On Ubuntu:

```shell
sudo apt install google-chrome-stable
```

### Lighthouse

Uses [lighthouse-ci](https://github.com/GoogleChrome/lighthouse-ci) with configuration defined in [lighthouserc.js](./lighthouserc.js).

Ensure Chrome is on the path by setting the `CHROME_PATH` environment variable.

```shell
npm install -g @lhci/cli@0.12.x puppeteer
export CHROME_PATH=/path/to/chrome
lhci autorun
```

Lighthouse will exit with a failure code if accessibility failures are found. Reports are stored in the `lighthouse-ci-report/` folder.

### Pa11y

Uses [pa11y-ci](https://github.com/pa11y/pa11y-ci) with configuration defined in [.pa11yci](./.pa11yci).

Change `executablePath` in .pa11yci to point to your Chrome installation.

```shell
npm install -g pa11y-ci pa11y-ci-reporter-html
pa11y-ci
```

Pa11y will exit with a failure code if accessibility failures are found. Reports are stored in the `pa11y-ci-report/` folder.

## Edit the CSS theme

The AMY theme is primarily based on Bootstrap 4.

To update the custom CSS that sits on top of the Bootstrap theme, edit `amy/static/css/amy.css`.

To override Bootstrap 4 defaults such as colors, edit the [Sass](https://sass-lang.com/) file `amy/static/scss/custom_bootstrap.scss` as required, then compile it to CSS:

```shell
npx sass amy/static/scss/custom_bootstrap.scss amy/static/css/custom_bootstrap.min.css --style compressed
```

See the [Bootstrap documentation](https://getbootstrap.com/docs/4.0/getting-started/theming/) for more guidance on overriding Bootstrap defaults.

[bootstrap]: https://getbootstrap.com/
[contact-address]: mailto:team@carpentries.org
[django]: https://www.djangoproject.com
[jquery]: https://jquery.com/
[issues]: https://github.com/carpentries/amy/issues
[tc]: https://carpentries.org/
[nodejs]: https://nodejs.org/en/
