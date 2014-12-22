# Where original data lives.
SRC_DIR = ~/s/admin

# Where original database lives (only on Software Carpentry administrator's machine).
SRC_DB = ${SRC_DIR}/roster.db

# Where event notes live.
SRC_EVENTS = ${SRC_DIR}/bootcamp-notes/archive

# Where site notes live.
SRC_SITES = ${SRC_DIR}/bootcamp-notes/negotiating

# Database used by this application.
APP_DB = db.sqlite3

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
	python migrater.py ${SRC_DB} ${APP_DB}
	sqlite3 ${APP_DB} .dump > ${DB_SQL}

## database     : re-make database using saved data
database :
	rm -f ${APP_DB}
	sqlite3 ${APP_DB} < ${DB_SQL}

## notes        : load old notes
notes :
	python notes-importer.py ${APP_DB} ${SRC_EVENTS} ${SRC_SITES}

## serve        : run a server
serve :
	python manage.py runserver

## clean        : clean up.
clean :
	rm -f \
	$$(find . -name '*~' -print) \
	$$(find . -name '*.pyc' -print) \
	${APP_DB}
