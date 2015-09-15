# How to run Python.
PYTHON = python3

# How to run the management tool.
MANAGE = ${PYTHON} manage.py

# Database used by this application.
APP_DB = db.sqlite3

# Saved SQL for regenerating the database.
APP_SQL = db.sql

# Run a SQL query.
QUERY = sqlite3 ${APP_DB}
QUERY_CSV = sqlite3 -csv ${APP_DB}

# Error messages.
E_SITE_PATH = "error: must set SITE_PATH before running command"
E_CERT_PATH = "error: must set CERT_PATH before running command"

.PHONY: workshops/git_version.py

all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## test         : run all tests.
test :
	${MANAGE} test

## migrations   : create/apply migrations
migrations :
	${MANAGE} makemigrations
	${MANAGE} migrate

## database     : re-make database using saved data
database :
	rm -f ${APP_DB}
	${QUERY} < ${APP_SQL}

## superuser    : make a super-user in the database
superuser :
	@${MANAGE} create_superuser

## airports     : display YAML for airports
airports :
	@${MANAGE} export_airports

## badges       : display YAML for badges
badges :
	@${MANAGE} export_badges

## check-urls   : check workshop URLs (must set SITE_PATH to run)
check-urls :
	@if [ -z "${SITE_PATH}" ]; then echo ${E_SITE_PATH}; else ${MANAGE} check_workshop_urls ${SITE_PATH}; fi

## check-badges : check that all badges have been awarded (must set SITE_PATH to run)
check-badges :
	@if [ -z "${SITE_PATH}" ]; then echo ${E_SITE_PATH}; else ${MANAGE} check_badges ${SITE_PATH}; fi

## check-certs : check that all instructor certificates have been set (must set CERT_PATH to run)
check-certs :
	@if [ -z "${CERT_PATH}" ]; then echo ${E_CERT_PATH}; else ${MANAGE} check_certificates ${CERT_PATH}; fi

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

## all-activity : report all instructor activity
all-activity :
	@${MANAGE} report_all_instructor_activity

## invoicing    : report financial activity related to invoicing
invoicing :
	@${MANAGE} report_invoicing

## incomplete   : report instructors who started training in the past year but haven't completed
incomplete :
	@${MANAGE} report_incomplete_instructors

## published    : report all published events
published :
	@${MANAGE} report_published_events

## serve        : run a server
serve : bower_components workshops/git_version.py
	${MANAGE} runserver

## upgrade      : force package upgrade using pip
upgrade :
	@pip install --upgrade -r requirements.txt
	@bower update

## clean        : clean up.
clean :
	rm -rf \
	$$(find . -name '*~' -print) \
	$$(find . -name '*.pyc' -print) \
	htmlerror \
	bower_components \
	${APP_DB}
