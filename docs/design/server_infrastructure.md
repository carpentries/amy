# Server infrastructure

AMY is hosted in [AWS](https://aws.amazon.com/) cloud. There are two AMY environments,
one for testing and one for production. They use very similar infrastructure so that testing
matches production. Additionally, both environments contain an email worker lambda function
that handles sending of automated emails.

---

## Email worker lambda function

The email worker lambda runs on schedule to send queued emails. The schedule is set up in EventBridge.

## AWS environments (testing and production)

### AWS services used

Server is hosted on [ECS](https://aws.amazon.com/ecs/) which allows for quick setup and robust scaling. AMY builds are
stored in [ECR](https://aws.amazon.com/ecr/) (Elastic Container Registry) and deployed to ECS through
[CloudFormation](https://aws.amazon.com/cloudformation/) templates defined in a separate repository using
[CDK](https://aws.amazon.com/cdk/) (Cloud Development Kit).

Database uses separate EC2 instance through [Relational Database Service (RDS)](https://aws.amazon.com/rds/).
Additionally [CloudFront](https://aws.amazon.com/cloudfront/) is used as CDN for assets (images,
CSS, JavaScript, including NPM dependencies).

A load balancer is used to distribute and direct traffic to ECS tasks. Domain is hosted in Route 53, which
additionally provides the TLS certificate for secure connections.

Service logs are stored in [CloudWatch](https://aws.amazon.com/cloudwatch/).

### Infrastructure as code

Infrastructure is defined in a separate repository as
a [Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/) project. It gets compiled
into CloudFormation template and deployed to AWS through Github Actions CI/CD pipeline.

### gunicorn

AMY, as a WSGI application, is run by [gunicorn](https://gunicorn.org/) on a separate
user/group. Gunicorn creates 4 (configurable value) workers for handling the incoming
requests.

### Backup

The database servers are regularly backed-up by AWS. For more details see
[database backups](./database_backups.md).

### Deployment

AMY is deployed with Github Actions CI/CD pipeline to ECS.

---

## Infrastructure shortcomings and future plans

> **Note 2025**: this section is no longer up to date. Both environments have been migrated to CI/CD pipeline
> with containerized deployments on ECS.

> **Note March 2023:** this section mostly applies to the production environment. Testing
stage has been revamped and most of the issues listed below have been resolved.

There are couple of issues with current approach to deployment:

1. Redis is on the same server as the application
2. Application server runs `certbot` to refresh TLS certificate
3. RQ worker and scheduler are on the same server as the application
4. Application requires a SSH-enabled server and is not immutable
5. There's no CI/CD pipeline set up - deployment is manual
6. There's downtime during deployment
7. It's not scalable
8. It requires custom deployment scripts (Ansible).
9. There's multiple log outputs from various services in one server (two or three from
   AMY, one  from `rqworker`, one from `rqscheduler`, one from `gunicorn`, one from
   a cronjob, two from nginx)

Below are propositions how to resolve each problem individually.

### Migrate Redis

Redis should be on a separate machine. [AWS offers](https://aws.amazon.com/redis/)
multiple services for hosted Redis solutions, but they may not be needed. Perhaps
a small EC2 sever dedicated to Redis could work, too?

### Replace `certbot` with AWS services

There is better and also free alternative to `certbot`. It's
[Route 53](https://aws.amazon.com/route53/) for keeping domain records, and
[Certificate Manager](https://aws.amazon.com/certificate-manager/) for generating free
TLS certificates.

Finally, Route 53 also works with Elastic Load Balancing, which should be used to
resolve issues like lack of scalability or CI/CD.

### Decouple RQ worker and scheduler from application

Unfortunately this is not easy.
[RQ worker and scheduler](https://python-rq.org/docs/scheduling/) are tightly coupled
with the application because they use objects from application's memory pickled and
stored in Redis database. This means that RQ worker and scheduler require access to the
same source code.

It would be the best to completely decouple RQ jobs from AMY source code. Even better if
the jobs themselves became JSON configuration files, and code to run them could be run
on a [Lambda](https://aws.amazon.com/lambda/).

These are all pretty big changes to the application, because Redis and RQ are used in
automated emails feature.

### Containerize the application to make it immutable

AMY should be containerized. It's already possible to build a Docker image with AMY,
but it probably should run migrations automatically (it doesn't yet).

Containerization is also required to run AMY in a scalable manner on ECS / EKS.

### Build CI/CD pipeline

Probably using GitHub Actions (see [docs](https://docs.github.com/en/actions/deployment/deploying-to-your-cloud-provider/deploying-to-amazon-elastic-container-service)).

### Use ECS for blue/green deployments and load balancing

[ECS](https://aws.amazon.com/ecs/) should be used to deploy AMY. Blue/green deployment
strategy should be used, and a load balancer (which helps resolve multiple issues
mentioned above).

### Deployment

AMY should be deployed using IaC (Infrastructure as Code) solution, for example.
[Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/infrastructure-as-code)
or [Cloud Formation](https://aws.amazon.com/cloudformation/).

### Simplified logs

Once AMY resides on a single VM (for example ECS task instance), it should produce one
stream of logs; these logs should be stored in
[CloudWatch](https://aws.amazon.com/cloudwatch/features/).
