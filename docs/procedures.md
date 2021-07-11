# Procedures

## Specifying a milestone (version)

AMY follows [Semantic Versioning](https://semver.org/) when possible; however, since this
is a web application and not a library, we have come up with these rules to bumping versions:

* hotfix or a fix release: bump patch version
* normal release: bump minor version
* major changes (e.g. big project gets merged): bump major version.

In future, once CI/CD is implemented, we may consider switching to [commitizen](https://github.com/commitizen/cz-cli)
which will help with generating changelogs and bumping versions accordingly.

**Milestone name should indicate the release version**. For example, if next release is
`v3.15.0`, then the milestone collecting issues and PRs should be named `v3.15` or `v3.15.0`.

## On the End of Each Milestone

1.  Close milestone using [GitHub UI](https://github.com/carpentries/amy/milestones).

2.  Write down release notes and add it to the repository in `docs/releases` directory.
    Release notes should have two sections: new features and bugfixes, each one enumerating changes and mentioning their authors.
    Base your work on the list of all closed pull requests for given milestone, available on GitHub.

3.  Follow [Release Procedure](#release-procedure).

4.  Follow [Deployment Procedure](#deployment-procedure-using-ansible).

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

4.  Merge `develop` into `main` branch (be careful, as there are sometimes conflicts that need to be manually resolved):

        $ git checkout main
        $ git merge --no-ff develop

5.  Bump version on `main` (non-dev version corresponding to the milestone):

        $ # manually edit version in `amy/__init__.py` and `package.json`
        $ # use non-dev version string, e.g. `"v3.3.0"`
        $ git add amy/__init__.py package.json
        $ git commit -m "Bumping version to vX.Y.0"

7.  Just to be safe, run tests:

        $ make test

8.  Tag a release.

        $ git tag -a "vX.Y.0" -s -m "AMY release vX.Y.0"

    Omit `-s` flag if you cannot create signed tags.
    See [Git documentation](https://git-scm.com/book/tr/v2/Git-Tools-Signing-Your-Work) for more info about signed tags.

9.  Push `main` and the new tag everywhere:

        $ git push origin main --tags
        $ git push upstream main --tags

10. Bump version on `develop` (dev version corresponding to the milestone):

        $ git checkout develop
        $ # manually edit version in `amy/__init__.py` and `package.json`
        $ # use dev version string, e.g. `"v3.4.0-dev"`
        $ git add amy/__init__.py package.json
        $ git commit -m "Bumping version to vX.Y.0-dev"

    This step is only needed if next development cycle begins (ie. no hotfix release was done).

11. And push it everywhere:

        $ git push upstream develop
        $ git push origin develop


## Deployment procedure using Ansible

Moved to relevant repository `README.md`.
