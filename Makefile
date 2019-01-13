# How to run Python.
PYTHON = python3

# How to run the management tool.
MANAGE = ${PYTHON} manage.py

# Database used by this application.
APP_DB = db.sqlite3

# Run a SQL query.
QUERY = sqlite3 ${APP_DB}

# Error messages.
E_CERT_PATH = "error: must set CERT_PATH before running command"

.PHONY: workshops/git_version.py

all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## test         : run all tests.
test :
	${MANAGE} test

## fast test	: run all tests really fast.
fast_test:
	${MANAGE} test --keepdb --parallel

## dev_database : re-make database using saved data
dev_database :
	rm -f ${APP_DB}
	${MANAGE} migrate
	${MANAGE} fake_database
	${MANAGE} createinitialrevisions

## superuser    : make a super-user in the database
superuser :
	@${MANAGE} create_superuser

## airports     : display YAML for airports
airports :
	@${MANAGE} export_airports

## check-certs : check that all instructor certificates have been set (must set CERT_PATH to run)
check-certs :
	@if [ -z "${CERT_PATH}" ]; then echo ${E_CERT_PATH}; else ${MANAGE} check_certificates ${CERT_PATH}; fi

## schema       : display the database schema
schema :
	${QUERY} .schema

## node_modules : install front-end dependencies using Yarn
node_modules : package.json
	yarn install --frozen-lockfile
	touch node_modules

## git_version  : store details about the current commit and tree state.
amy/workshops/git_version.py :
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
serve : node_modules workshops/git_version.py
	${MANAGE} runserver

## serve_now    : run a server now
serve_now :
	${MANAGE} runserver

## outdated		: show outdated dependencies
outdated :
	-pip list --outdated
	-yarn outdated

## upgrade      : force package upgrade using pip
upgrade :
	pip install --upgrade -r requirements.txt
	yarn upgrade

## clean        : clean up.
clean :
	rm -rf \
		$$(find . -name '*~' -print) \
		$$(find . -name '*.pyc' -print) \
		htmlerror \
		$$(find . -name 'test_db*.sqlite3' -print) \

## coverage     : run tests and generate HTML coverage
coverage :
	coverage --source=amy manage.py test
	coverage html
