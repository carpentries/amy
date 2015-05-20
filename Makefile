# How to run Python.
PYTHON = python3

# Database used by this application.
APP_DB = db.sqlite3

# Saved SQL for regenerating the database.
APP_SQL = db.sql

# Run a SQL query.
QUERY = sqlite3 ${APP_DB}
QUERY_CSV = sqlite3 -csv ${APP_DB}

.PHONY: workshops/git_version.py

all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## test         : run all tests.
test :
	${PYTHON} manage.py test

## migrations   : create/apply migrations
migrations :
	${PYTHON} manage.py makemigrations
	${PYTHON} manage.py migrate

## database     : re-make database using saved data
database :
	rm -f ${APP_DB}
	${QUERY} < ${APP_SQL}

## superuser    : make a super-user in the database
superuser :
	@${PYTHON} manage.py create_superuser

## airports     : display YAML for airports
airports :
	@${PYTHON} manage.py export_airports

## badges       : display YAML for badges
badges :
	@${PYTHON} manage.py export_badges

## schema       : display the database schema
schema :
	${QUERY} .schema

## bower_components : install front-end dependencies using Bower
bower_components : bower.json
	bower install
	touch bower_components

## git_version  : store details about the current commit and tree state.
workshops/git_version.py :
	@if test -d .git; \
	then \
		git log -1 --date=short --format="HASH = '%H'%nSHORT_HASH = '%h'%nDATE = '%cd'%n" >$@; \
		if (git describe --dirty 2>/dev/null | grep dirty >/dev/null); \
		then \
			echo 'DIRTY = True' >>$@; \
		else \
			echo 'DIRTY = False' >>$@; \
		fi \
	fi

## serve        : run a server
serve : bower_components workshops/git_version.py
	${PYTHON} manage.py runserver

## clean        : clean up.
clean :
	rm -rf \
	$$(find . -name '*~' -print) \
	$$(find . -name '*.pyc' -print) \
	htmlerror \
	bower_components \
	${APP_DB}
