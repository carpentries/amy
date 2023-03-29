# CI/CD

CI stands for "Continuous Integration" and CD stands for "Continuous Deployment".

The goal of CI/CD is to have a fully automated process of deploying new versions of AMY
to a server. Currently it is only working for testing stage, but could be extended to
production at some point, too.

During CI stage, the following happens:

1. Code is pushed to GitHub.
2. GitHub Actions runs tests.
1. If tests pass, then a new Docker image is built and pushed to
[AWS Elastic Container Registry (ECR)](https://aws.amazon.com/ecr/).

Then CD stage starts:

1. A new version of AMY is deployed to testing stage.


The CI/CD pipeline is run by [GitHub Actions](https://github.com/features/actions). It
is defined in `.github/workflows/cicd_develop.yml` (for `develop` branch) file.

Note that there is another workflow `.github/workflows/cicd_main.yml` that is run only
for the `main` branch, but it doesn't contain any other steps (stages) than `test`.

## Stage details

### Test

There is a separate `test` stage for CI/CD defined in `.github/workflows/test.yml` file
and included in the main `cicd_develop.yml` file. It installs all the dependencies,
sets up database and runs tests.

### Build

The `build` stage is defined in `.github/workflows/cicd_develop.yml` file. After logging
in to AWS ECR, it builds a Docker image and pushes it to AWS ECR with last commit hash
as a image tag.

### Deploy

The `deploy` stage is defined in `.github/workflows/cicd_develop.yml` file. It is **only
run** when GitHub Actions is triggered by a push to `develop` branch, either through
a PR merge or direct push.

Deployment uses an [AWS Elastic Container Service (ECS)](https://aws.amazon.com/ecs/)
task definition downloaded to a GitHub agent. Then this file has the image tag updated
to the one that was built in the `build` stage. Then the task definition is uploaded to
AWS ECS and a new task is started.
