# Server infrastructure

AMY is hosted in [AWS](https://aws.amazon.com/) cloud.

## AWS services used

Server is hosted on [EC2](https://aws.amazon.com/ec2/) instance. Database uses separate
EC2 instance through [RDS service](https://aws.amazon.com/rds/). Additionally
[CloudFront](https://aws.amazon.com/cloudfront/) is used as CDN for assets (images,
CSS, JavaScript, including NPM dependencies).

## Environments / stages

Currently there are two stages:

* test,
* production.

## WWW server

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

## gunicorn

AMY, as a WSGI application, is run by [gunicorn](https://gunicorn.org/) on a separate
user/group. Gunicorn creates 3 (configurable value) workers for handling the incoming
requests. Logs are located in `/webapps/{domain}/logs/gunicorn_supervisor.log` and
rotated.

## TLS certificate

[Certbot](https://certbot.eff.org/) is used to acquire the TLS domain certificate.

## Application directory

AMY directory is located on the server under `/webapps/{domain}`. It contains:

* `DB_backups` - directory with old regular DB backups and backups created before every
  deployment,
* `logs` - directory with logs from various components,
* `repo` - directory with application source code and virtual environment,
* `maintenance_off.html` - file used for entering maintenance mode (when renamed to
  `maintenance_on.html`).

### Virtual environment

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

## Redis

Redis is installed and served from the application server itself. There is no special
configuration used for it, and it's not exposed.

## Backup

The database servers are regularly backed-up by AWS.

Additional backups are created before starting any deployment with `pg_dump`.

## Deployment

AMY is deployed with [Ansible](https://docs.ansible.com/) scripts. The standard
deployment procedure is documented in a file in separate repository containing these
scripts.
