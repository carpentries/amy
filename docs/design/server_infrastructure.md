# Server infrastructure

AMY is hosted in [AWS](https://aws.amazon.com/) cloud. There are two AMY environments,
one for testing and one for production. They use separate setups.

---

## Production

### AWS services used

Server is hosted on [Elastic Compute Cloud (EC2)](https://aws.amazon.com/ec2/) instance.
Database uses separate EC2 instance through
[Relational Database Service (RDS)](https://aws.amazon.com/rds/). Additionally
[CloudFront](https://aws.amazon.com/cloudfront/) is used as CDN for assets (images,
CSS, JavaScript, including NPM dependencies).

### WWW server

AMY is hosted by [Nginx](https://www.nginx.com/) and has 4 roles:

1. handles TLS,
2. serves a [Django](https://djangoproject.com/) application through
   [gunicorn](https://gunicorn.org/) (working as a proxy),
3. serves a maintenance page when upstream proxy is not available, for
   example during upgrade.

Nginx configuration is similar to vhost-like Apache configuration.
The web server was installed through Ubuntu repositories and should
start automatically with system's boot.

Nginx is configured to check for existence of `maintenance_on.html` file in
`/webapps/{domain}`. If it's there, then `503 Service Unavailable` is served with that
HTML file on all requests.

### gunicorn

AMY, as a WSGI application, is run by [gunicorn](https://gunicorn.org/) on a separate
user/group. Gunicorn creates 3 (configurable value) workers for handling the incoming
requests. Logs are located in `/webapps/{domain}/logs/gunicorn_supervisor.log` and
rotated.

### TLS certificate

[Certbot](https://certbot.eff.org/) is used to acquire the TLS domain certificate.

### Application directory

AMY directory is located on the server under `/webapps/{domain}`. It contains:

* `DB_backups` - directory with old regular DB backups and backups created before every
  deployment,
* `logs` - directory with logs from various components,
* `repo` - directory with application source code and virtual environment,
* `maintenance_off.html` - file used for entering maintenance mode (when renamed to
  `maintenance_on.html`).

#### Virtual environment

To get into AMY's virtual environment, issue:

```shell
$ source /webapps/{domain}/repo/.venv/bin/activate
```

You may need to do this from root's (superuser) privilege level.

It's also important to activate environment variables used by the project. You can do
that with:

```shell
$ source /webapps/{domain}/repo/.venv/bin/postactivate
```

### Redis

Redis is installed and served from the application server itself. There is no special
configuration used for it, and it's not exposed.

### Backup

The database servers are regularly backed-up by AWS. For more details see
[database backups](./database_backups.md).

Additional backups are created before starting any deployment with `pg_dump`.

### Deployment

AMY is deployed with [Ansible](https://docs.ansible.com/) scripts. The standard
deployment procedure is documented in a file in separate repository containing these
scripts.

---

## Testing

Testing stage has recently been updated to fix many of the shortcomings listed below in
[Infrastructure shortcomings and future plans](#infrastructure-shortcomings-and-future-plans).

### AWS services used

* [Elastic Container Service (ECS)](https://aws.amazon.com/ecs/) - for running
  a container with AMY with a load balancer
* [Relational Database Service (RDS)](https://aws.amazon.com/rds/) - for database
  (serverless PostgreSQL-flavored Aurora)
* [CloudFront](https://aws.amazon.com/cloudfront/) is used as CDN for assets
* [Route 53](https://aws.amazon.com/route53/) for keeping domain records and managing
  TLS certificates
* [Elastic Container Registry (ECR)](https://aws.amazon.com/ecr/) - for storing Docker images
* [CloudWatch](https://aws.amazon.com/cloudwatch/) - for log keeping
* [CloudFormation](https://aws.amazon.com/cloudformation/) - for infrastructure as code
  and deployment of the infrastructure.

There is no Redis instance as it's not needed right now on the testing stage.

### Infrastructure as code

Infrastructure is defined in a separate repository as
a [Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/) project. It gets compiled
into CloudFormation template.

### Deployment

AMY is deployed to the testing stage with CI/CD pipeline on GitHub Actions.

---

## Infrastructure shortcomings and future plans

> **Note March 2023:** this section mostly applies to the production environment. Testing
stage has been revamped and most of the issues listed below have been resolved.
>
> A note has been added to every item that has been resolved in testing.

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

> **Note March 2023 [testing stage]:** does not apply; there is no Redis required.

### Replace `certbot` with AWS services

There is better and also free alternative to `certbot`. It's
[Route 53](https://aws.amazon.com/route53/) for keeping domain records, and
[Certificate Manager](https://aws.amazon.com/certificate-manager/) for generating free
TLS certificates.

Finally, Route 53 also works with Elastic Load Balancing, which should be used to
resolve issues like lack of scalability or CI/CD.

> **Note March 2023 [testing stage]:** TLS and domain is managed by AWS (Route 53
> service).

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

> **Note March 2023:** this was not achieved, and is required for migrating production
> to containerized (cloud native) solution.

### Containerize the application to make it immutable

AMY should be containerized. It's already possible to build a Docker image with AMY,
but it probably should run migrations automatically (it doesn't yet).

Containerization is also required to run AMY in a scalable manner on ECS / EKS.

> **Note March 2023 [testing stage]:** AMY is containerized and runs on ECS.

### Build CI/CD pipeline

Probably using GitHub Actions (see [docs](https://docs.github.com/en/actions/deployment/deploying-to-your-cloud-provider/deploying-to-amazon-elastic-container-service)).

> **Note March 2023 [testing stage]:** CI/CD pipeline is set up using GitHub Actions.

### Use ECS for blue/green deployments and load balancing

[ECS](https://aws.amazon.com/ecs/) should be used to deploy AMY. Blue/green deployment
strategy should be used, and a load balancer (which helps resolve multiple issues
mentioned above).

> **Note March 2023 [testing stage]:** ECS is used for deployment and load balancing.

### Deployment

AMY should be deployed using IaC (Infrastructure as Code) solution, for example.
[Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/infrastructure-as-code)
or [Cloud Formation](https://aws.amazon.com/cloudformation/).

> **Note March 2023 [testing stage]:** AMY infrastructure is deployed using CDK and
> CloudFormation.

### Simplified logs

Once AMY resides on a single VM (for example ECS task instance), it should produce one
stream of logs; these logs should be stored in
[CloudWatch](https://aws.amazon.com/cloudwatch/features/).

> **Note March 2023 [testing stage]:** logs are stored in CloudWatch.
