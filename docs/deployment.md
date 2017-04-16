# On the End of Each Milestone

1.  Close milestone using [GitHub UI](https://github.com/swcarpentry/amy/milestones).

2.  Write down release notes and add it to the repository in `docs/releases` directory.
    Release notes should have two sections: new features and bugfixes, each one enumerating changes and mentioning their authors.
    Base your work on the list of all closed pull requests for given milestone, available on GitHub.

3.  Follow Release Procedure (see below).

4.  Follow Deployment Procedure (see below).

5.  Write to <amy@lists.software-carpentry.org> mailing list.
    The suggested subject of the new thread is "[Amy] New release v1.X.Y".

# Release Procedure

We assume that you want to release AMY v1.X.Y.

Execute the following commands on your local machine, not production.

1.  Move to AMY root directory (the one with `manage.py` file) using `cd` command.

2.  Make sure you have configured repositories:

    - `origin` for your repository on GitHub
    - `upstream` for [`swcarpentry/amy` repo on GitHub](https://github.com/swcarpentry/amy)

    For example, this is the correct configuration for `chrismedrela`:

        $ git remote -v
        origin	git@github.com:chrismedrela/amy.git (fetch)
        origin	git@github.com:chrismedrela/amy.git (push)
        upstream	git@github.com:swcarpentry/amy.git (fetch)
        upstream	git@github.com:swcarpentry/amy.git (push)

3.  Make sure your local `develop` and `master` branches are up to date:

        $ git checkout develop
        $ git pull upstream develop
        $ git push origin develop

        $ git checkout master
        $ git pull upstream master
        $ git push origin master

    Pushes to your `origin` repository are optional.

4.  Define which version you're going to release (replace X and Y with correct numbers):

        $ AMY_VERSION=v1.X.Y

5.  Merge `develop` into `master` branch:

        $ git checkout master
        $ git merge --no-ff develop  # sometimes there are conflicts in files with release version, but most often we need to edit them and commit

6.  Bump version on `master`:

        $ echo "__version__ = '$AMY_VERSION'" > workshop/__init__.py  # change version to 1.X.Y
        $ vim bower.json  # change 'version' to 1.X.Y
        $ git add workshops/__init__.py bower.json
        $ git commit -m "Bumping version to $AMY_VERSION"

7.  Just to be safe, run tests:

        $ make test

8.  Tag a release.

        $ git tag -a "$AMY_VERSION" -s -m "AMY release $AMY_VERSION"

    Omit `-s` flag if you cannot create signed tags.
    See [Git documentation](https://git-scm.com/book/tr/v2/Git-Tools-Signing-Your-Work) for more info about signed tags.

9.  Push `master` and the new tag everywhere:

        $ git push origin master --tags
        $ git push upstream master --tags

10. Bump version on `develop`:

        $ git checkout develop
        $ vim bower.json  # change version to the next one after 1.X.Y (i.e. 1.X+1.0-dev)
        $ vim workshop/__init__.py  # change version to the next one
        $ git add workshops/__init__.py bower.json
        $ git commit -m "Bumping version to v1.X+1.0-dev"

    Skip this step if you're releasing minor AMY version (that is, when you increment Y, not X).

11. And push it everywhere:

        $ git push upstream develop
        $ git push origin develop

# Deployment Procedure

1.  Log into production:

        $ ssh amy@amy.software-carpentry.org

    All the following commands will be executed on production, not your local machine.

2.  Activate virtualenv:

        $ source ~/amy_site/venv/bin/activate

3.  Go to project directory:

        $ cd amy_site/amy

4.  Check environment variables:

        $ cat ../uwsgi_env

    Update them if necessary:

        $ vi ../uwsgi_env

5.  Stop server for maintenance:

        $ sudo stop uwsgi-emperor

6.  Go to [admin dashboard](https://amy.software-carpentry.org/workshops/admin-dashboard/) and make sure that maintenance page is displayed.

7.  Create local database backup:

        $ cp db.sqlite3 db.sqlite3.bak

8.  Fetch newer AMY source code:

        $ git fetch
        $ git checkout tags/v1.X.Y  # Python files updated

9.  Update dependencies:

        $ make upgrade

10. Test migrations:

        $ cp db.sqlite3 migration-test.sqlite3
        $ AMY_DB_FILENAME=migration-test.sqlite3 ./manage.py migrate
        $ rm migration-test.sqlite3

11. Migrate production database (`db.sqlite3`):

        $ ./manage.py migrate

12. Regenerate version number in the footer:

        $ make serve

    This launches local server on 8000 port. Quit it with Ctrl+C.

13. Update static files:

        $ ./manage.py collectstatic --noinput

14. Execute any additional stuff like one-off commands.
    If necessary, load environment variables before launching one-off commands.

        $ source ../uwsgi_env

15. Start server again:

        $ sudo start uwsgi-emperor

16. Make sure in your browser that AMY works by loading [admin dashboard](https://amy.software-carpentry.org/workshops/admin-dashboard/).

17. Log out production:

        $ exit
