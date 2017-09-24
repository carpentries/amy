# Server infrastructure

AMY is hosted by the
[Software Carpentry Foundation](https://software-carpentry.org/scf/)
on [Rackspace](http://rackspace.com/) server.

## WWW server

AMY is hosted by [Nginx](https://www.nginx.com/) and has 4 roles:

1. handles TLS
2. handles static files at `/static`
3. serves a [Django](https://djangoproject.com/) application through
   [uWSGI](http://uwsgi-docs.readthedocs.org/) (working as a proxy)
4. serves a maintenance page when upstream proxy is not available, for
   example during upgrade.

Nginx configuration is similar to vhost-like Apache configuration.
The web server was installed through Ubuntu repositories and should
start automatically with system's boot.

With `service nginx` it's possible to control the server's behavior.
All configuration is stored in `/etc/nginx`, but AMY-related config files
(for example a site/vhost configuration file) are symlinked.

All Nginx AMY-related configuration is stored in AMY catalog.

Both Nginx and uWSGI run as separate users and separate groups.

Nginx logs are located in `/var/log/nginx/`.

### uWSGI

AMY, as a WSGI application, is run by uWSGI in an
[emperor-mode](http://uwsgi-docs.readthedocs.io/en/latest/Emperor.html).

In this mode, uWSGI creates a fixed number of AMY processes based on
a configuration file `amy_uwsgi.ini`. Additionally it watches this file,
and upon detecting any changes, it automatically reloads the whole
application, which makes it easy to bring changes to the production.

There's a special script, `/etc/init/uwsgi-emperor.conf`, that helps
manage uWSGI with `initctl` manager. It provides for example these commands:

* `start uwsgi-emperor`
* `stop uwsgi-emperor`

All the uWSGI configuration is stored in AMY catalog.

uWSGI logs are located in `/etc/uwsgi/emperor.log` and in AMY catalog.

### AMY catalog

In `amy_site` (AMY catalog) there are stored:

* `amy` - application source from Git
* `amy.log.gz` - compressed log file
* `amy_nginx.conf` - Nginx site configuration for AMY
* `amy.pid`, `amy.sock` - uWSGI-generated files
* `amy_uwsgi.ini` - uWSGI configuration file
* `static_html` - a maintenace page catalog
* `uwsgi_env` - file with all environment variables required to run
  AMY (one variable per line); this file is read in by uWSGI
* `venv` - a Python
[virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/)
catalog.

### Virtual environment

To get into AMY's virtual environment, issue
`source ~/amy_site/venv/bin/activate`. You should now be able to control
installed Python packages.

The standard deployment procedure is documented in a separate file.

## Database server

## Backup
