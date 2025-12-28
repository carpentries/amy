# Procedures

## Specifying a milestone (version)

AMY follows [Semantic Versioning](https://semver.org/) when possible; however, since this
is a web application and not a library, we have come up with these rules to bumping versions:

* hotfix or a fix release: bump patch version
* normal release: bump minor version
* major changes (e.g. big project gets merged): bump major version.

**Milestone name should indicate the release version**. For example, if next release is
`v3.15.0`, then the milestone collecting issues and PRs should be named `v3.15` or `v3.15.0`.

## Feature development

Developers are encouraged to use
[feature flags](https://launchdarkly.com/blog/what-are-feature-flags/) for development
of new features in case they would have to be released to production
[in dark](https://www.flagship.io/glossary/dark-launch/).

## On the End of Each Milestone

1. Close milestone using [GitHub UI](https://github.com/carpentries/amy/milestones).

2. Run `python docs/generate_changelog.py MILESTONE_NAME` to generate changelog for given
   release; paste command's output to the top of `CHANGELOG.md` file.

3. Follow [Release Procedure](#release-procedure).

4. Consider manual steps to do **before** the release: [manual deployment steps](./manual_deployment_steps.md).

5. Follow [Deployment Procedure](#deployment-procedure-using-ansible).

6. Consider manual steps to do **after** the release: [manual deployment steps](./manual_deployment_steps.md).

7. Write user-friendly release notes and share them in release announcements on Slack - use `#core-team` for admin-only changes and `#general` for community-facing changes.

## Release Procedure

We assume that you want to release AMY v2.X.Y.

Execute the following commands on your local machine, not production.

1.  Move to AMY root directory (the one with `manage.py` file) using `cd` command.

2.  Make sure you have configured repositories:

    - `origin` for [`carpentries/amy` repo on GitHub](https://github.com/carpentries/amy)

    For example, this is the correct configuration:

        $ git remote -v
        origin	git@github.com:carpentries/amy.git (fetch)
        origin	git@github.com:carpentries/amy.git (push)

3.  Make sure your local `develop` and `main` branches are up to date:

        $ git checkout develop
        $ git pull origin develop

        $ git checkout main
        $ git pull origin main

4. Create a release branch `release/vX.Y.Z`. Major/minor release branches should be based on the `HEAD` of `develop`, but bugfix releases may be based on older commits, such as the previous release branch or `main`, to avoid including features intended for the next major/minor release. For more details on managing branches, see https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow.

5. *Bugfix releases only:* Cherry-pick commits from `develop` to `release/vX.Y.Z` as required to fix bugs. Skip any commits that add new features.

6.  Merge `release/vX.Y.Z` into `main` branch (be careful, as there are sometimes conflicts that need to be manually resolved):

        $ git checkout main
        $ git merge --no-ff release/vX.Y.Z

7.  Bump version on `main` (non-dev version corresponding to the milestone):

        $ # manually edit version in `pyproject.toml` and `package.json`
        $ # use non-dev version string, e.g. `"v3.3.0"`
        $ git add pyproject.toml package.json
        $ git commit -m "Bumping version to vX.Y.0"

8.  Just to be safe, run tests:

        $ make test

9.  Tag a release.

        $ git tag -a "vX.Y.0" -s -m "AMY release vX.Y.0"

    Omit `-s` flag if you cannot create signed tags.
    See [Git documentation](https://git-scm.com/book/tr/v2/Git-Tools-Signing-Your-Work) for more info about signed tags.

10. Complete any [Manual Deployment Steps](./manual_deployment_steps.md) noted for before deployment of this release.

11. Push `main` and the new tag everywhere:

        $ git push origin main --tags

    **Note:** this will trigger deployment to production environment.
    A manual confirmation is required in Github Actions UI to proceed.

12. Complete any [Manual Deployment Steps](./manual_deployment_steps.md) noted for after deployment of this release.

13. Bump version on `develop` (dev version corresponding to the milestone):

        $ git checkout develop
        $ # manually edit version in `pyproject.toml` and `package.json`
        $ # use dev version string, e.g. `"v3.4.0-dev"`
        $ git add pyproject.toml package.json
        $ git commit -m "Bumping version to vX.Y.0-dev"

    This step is only needed if next development cycle begins (ie. no hotfix release was done).

14. And push it everywhere:

        $ git push origin develop

    **Note:** this will trigger deployment to testing environment.
