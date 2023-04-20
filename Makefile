# How to run Python.
PYTHON = python3

# How to run the management tool.
MANAGE = ${PYTHON} manage.py


all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## test         : run all tests.
test :
	${MANAGE} test

## fast_test    : run all tests really fast.
fast_test:
	${MANAGE} test --keepdb --parallel

## fast_test_fail	: run all tests really fast, fails as soon as any test fails.
fast_test_fail:
	${MANAGE} test --keepdb --parallel --failfast

## dev_database : re-make database using saved data
dev_database :
	${MANAGE} reset_db
	${MANAGE} migrate
	${MANAGE} runscript seed_badges
	${MANAGE} runscript seed_autoemails
	${MANAGE} runscript seed_communityroles
	${MANAGE} runscript seed_training_requirements
	${MANAGE} runscript seed_groups
	${MANAGE} create_superuser
	${MANAGE} fake_database
	${MANAGE} createinitialrevisions
	${MANAGE} createcachetable

## node_modules : install front-end dependencies
node_modules : package.json
	npm install
	touch node_modules

## serve        : run a server
serve :
	gunicorn \
		--workers=4 \
		--bind=127.0.0.1:8000 \
		--access-logfile - \
		--capture-output \
		--reload \
		--env DJANGO_SETTINGS_MODULE=config.settings \
		config.wsgi

## outdated     : show outdated dependencies
outdated :
	-${PYTHON} -m pip list --outdated
	-npm outdated

## clean        : clean up.
clean :
	rm -rf \
		$$(find . -name '*~' -print) \
		$$(find . -name '*.pyc' -print) \
		$$(find . -name '__pycache__' -print) \
		htmlerror \
		$$(find . -name 'test_db*.sqlite3*' -print) \

## build_docs   : build static docs in `site`
build_docs :
	mkdocs build

## serve_docs   : serve docs at `localhost:8000`
serve_docs :
	mkdocs serve
