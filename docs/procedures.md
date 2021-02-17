# Procedures

## On the End of Each Milestone

1.  Close milestone using [GitHub UI](https://github.com/carpentries/amy/milestones).

2.  Write down release notes and add it to the repository in `docs/releases` directory.
    Release notes should have two sections: new features and bugfixes, each one enumerating changes and mentioning their authors.
    Base your work on the list of all closed pull requests for given milestone, available on GitHub.

3.  Follow [Release Procedure](#release-procedure).

4.  Follow Deployment Procedure (either
    [manual method](#deployment-procedure---manual-method) or using
    [Ansible Playbook](#deployment-procedure-using-ansible)).

5.  Write to <amy@lists.carpentries.org> mailing list.
    The suggested subject of the new thread is "[AMY] New release v2.X.Y".

## Release Procedure

We assume that you want to release AMY v2.X.Y.

Execute the following commands on your local machine, not production.

1.  Move to AMY root directory (the one with `manage.py` file) using `cd` command.

2.  Make sure you have configured repositories:

    - `origin` for your repository on GitHub
    - `upstream` for [`carpentries/amy` repo on GitHub](https://github.com/carpentries/amy)

    For example, this is the correct configuration for `chrismedrela`:

        $ git remote -v
        origin	git@github.com:chrismedrela/amy.git (fetch)
        origin	git@github.com:chrismedrela/amy.git (push)
        upstream	git@github.com:carpentries/amy.git (fetch)
        upstream	git@github.com:carpentries/amy.git (push)

3.  Make sure your local `develop` and `main` branches are up to date:

        $ git checkout develop
        $ git pull upstream develop
        $ git push origin develop

        $ git checkout main
        $ git pull upstream main
        $ git push origin main

    Pushes to your `origin` remote are optional.

4.  Define which version you're going to release (replace X and Y with correct numbers):

        $ AMY_CURRENT=v2.X.Y-dev  # this needs to correspond to what you have in amy/workshops/__init__.py and package.json
        $ AMY_VERSION=v2.X.Y
        $ AMY_NEXT_VERSION=v2.X+1.0-dev

5.  Merge `develop` into `main` branch (be careful, as there are sometimes conflicts that need to be manually resolved):

        $ git checkout main
        $ git merge --no-ff develop

6.  Bump version on `main`:

        $ make bumpversion CURRENT=$AMY_CURRENT NEXT=$AMY_VERSION
        $ git add amy/workshops/__init__.py package.json
        $ git commit -m "Bumping version to $AMY_VERSION"

7.  Just to be safe, run tests:

        $ make test

8.  Tag a release.

        $ git tag -a "$AMY_VERSION" -s -m "AMY release $AMY_VERSION"

    Omit `-s` flag if you cannot create signed tags.
    See [Git documentation](https://git-scm.com/book/tr/v2/Git-Tools-Signing-Your-Work) for more info about signed tags.

9.  Push `main` and the new tag everywhere:

        $ git push origin main --tags
        $ git push upstream main --tags

10. Bump version on `develop`:

        $ git checkout develop
        $ make bumpversion CURRENT=$AMY_CURRENT NEXT=$AMY_NEXT_VERSION
        $ git add amy/workshops/__init__.py package.json
        $ git commit -m "Bumping version to $AMY_NEXT_VERSION"

    Skip this step if development version doesn't change, for example during
    minor version development cycle (`v2.X.0-dev`) you're releasing a patch
    (`v2.X-1.Y`).

11. And push it everywhere:

        $ git push upstream develop
        $ git push origin develop


## Deployment Procedure - manual method

1.  Log into production:

        $ ssh amy@amy.carpentries.org

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

7.  Create a compressed local database backup (through special backup function in SQLite client):

        $ sqlite3 db.sqlite3 ".backup DB_backups/backup-before-upgrade-to-v2.X.Y.sqlite3"
        $ gzip DB_backups/backup-before-upgrade-to-v2.X.Y.sqlite3

    Do not use `$AMY_VERSION` environment variable because it's not defined here.

8.  Fetch newer AMY source code:

        $ git fetch
        $ git checkout tags/v2.X.Y  # Python files updated

9.  Update dependencies:

        $ make upgrade

10. Test migrations:

        $ sqlite3 db.sqlite3 ".backup migration-test.sqlite3"
        $ DATABASE_URL=sqlite:///migration-test.sqlite3 ./manage.py migrate
        $ rm migration-test.sqlite3

11. Migrate production database (`db.sqlite3`):

        $ ./manage.py migrate

12. Update static files:

        $ ./manage.py collectstatic --noinput

13. Execute any additional stuff like one-off commands.
    If necessary, load environment variables before launching one-off commands.

        $ source ../uwsgi_env

14. Start server again:

        $ sudo start uwsgi-emperor

15. Make sure in your browser that AMY works by loading [admin dashboard](https://amy.software-carpentry.org/workshops/admin-dashboard/).

16. Log out production:

        $ exit


## Deployment procedure using Ansible

If you have access to Ansible playbook files for AMY, you can automate
deployment.

**CAUTION:** only use this method if you don't have to invoke any custom
methods when the server is off for upgrade.

1. Ensure you have `ansible-playbook` command available:

        $ ansible-playbook --version

2. Create an inventory file `production` containing production server address:

        [all:vars]
        env=production

        [webservers]
        amy.carpentries.org

    The first group `all:vars` sets `production` variable group. You can
    further tweak them in `env_vars/production.yml`.

3. Set correct git tag in `env_vars/production.yml`:

        ...
        #===> Git settings only for production
        fetch_git_tag: yes
        git_tag: tags/v2.4.0
        ...

    Replace `v2.4.0` with the version you want to fetch (e.g. `v2.5.0`).

4. Review other variables in `env_vars/production.yml` and update them if
   required.

5. Make sure your public SSH key is added to the `~/.ssh/authorized_keys` file
   on destination server `amy.carpentries.org`.

6. Optional: test provisioning on a local Vagrant machine

        $ vagrant up --provision

7. Run Ansible provisioning:

        $ ansible-playbook --inventory=production --user=amy -vv

    The last switch `-vv` enables verbosity, which helps in debugging if errors
    occur.

8. Check production website - it should be running, and there should be a
   version number (e.g. `v2.5.0`) in the footer.
