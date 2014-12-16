# Where original database lives (only on Software Carpentry administrator's machine).
DB_SRC = ~/s/admin/roster.db

# Database used by this application.
DB_APP = db.sqlite3

# Saved SQL for regenerating the database.
DB_SQL = db.sql

all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## test         : run all tests.
test :
	python manage.py test

## migrations   : create/apply migrations
migrations :
	python manage.py makemigrations
	python manage.py migrate

## import       : import and save legacy data
import :
	python migrater.py '2015-01-01' ${DB_SRC} ${DB_APP}
	sqlite3 ${DB_APP} .dump > ${DB_SQL}

## database     : re-make database using saved data
database :
	rm -f ${DB_APP}
	sqlite3 ${DB_APP} < ${DB_SQL}

## serve        : run a server
serve :
	python manage.py runserver

## clean        : clean up.
clean :
	rm -f \
	$$(find . -name '*~' -print) \
	$$(find . -name '*.pyc' -print) \
	${DB_APP}
