# Migration from SQLite to PostgreSQL

Clear PostgreSQL database with drop/create commands or with `manage.py`:

```postgresql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
or
```shell
$ DATABASE_URL=postgresql://amy:...@.../amy python manage.py reset_db
```

Migrate the new server with latest migrations:

```shell
$ DATABASE_URL=postgresql://amy:...@.../amy python manage.py migrate
```

Some of the migrations have data migrations, and create entries in the database. The same data will be included in the database dump from SQLite, so one way to work around this issue is to flush the database (remove existing data):

```shell
$ DATABASE_URL=postgresql://amy:...@.../amy python manage.py flush
```

Flushing doesn't affect installed permissions, content types and sites. They need to be cleaned individually:

```postgresql
TRUNCATE auth_permission CASCADE;
TRUNCATE django_site CASCADE;
TRUNCATE django_content_type CASCADE;
```

All these three will be brought back with separate dump.

**WARNING!** Don't remove migration data from `django_migration` table.

Make latest backup of SQLite database:

```shell
$ cd /webapps/amy.carpentries.org/repo/ && sqlite3 db.sqlite3  ".backup newest_backup.sqlite3"
```

Prepare data dump with Django:

```shell
$ DATABASE_URL=sqlite:///newest_backup.sqlite3 python manage.py dumpdata contenttypes auth.permissions sites --indent 1 > data_others.json
$ DATABASE_URL=sqlite:///newest_backup.sqlite3 python manage.py dumpdata -e contenttypes -e auth.permissions -e sites --indent 1 > data.json
```

Load the first dump into PostgreSQL:

```shell
$ DATABASE_URL=postgresql://amy:...@.../amy python manage.py loaddata data_others.json
```

**Verify the number of objects installed: 311.**

Load the second dump into PostgreSQL:

```shell
$ DATABASE_URL=postgresql://amy:...@.../amy python manage.py loaddata data_others.json
```

**Verify the number of objects installed: 353514 (or more).**
