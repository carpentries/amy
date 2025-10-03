# How to run Python.
PYTHON = python3

# How to run the management tool.
MANAGE = ${PYTHON} manage.py


all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## database     : create Postgres database in Docker
database:
	docker run --name amy-database -e POSTGRES_USER=amy -e POSTGRES_PASSWORD=amypostgresql -e POSTGRES_DB=amy -p 5432:5432 -d postgres

## test         : run all tests except migration tests.
test :
	${MANAGE} test --exclude-tag migration_test --exclude-tag autoemails ./amy

## test_migrations    : test database migrations only
test_migrations:
	${MANAGE} test --tag migration_test ./amy

## dev_database : re-make database using saved data
dev_database :
	${MANAGE} reset_db --close-sessions --no-input
	${MANAGE} migrate
	${MANAGE} runscript seed_badges
	${MANAGE} runscript seed_communityroles
	${MANAGE} runscript seed_training_requirements
	${MANAGE} runscript seed_involvements
	${MANAGE} runscript seed_emails
	${MANAGE} runscript seed_event_categories
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
		--workers=1 \
		--bind=127.0.0.1:8000 \
		--access-logfile - \
		--capture-output \
		--reload \
		--env DJANGO_SETTINGS_MODULE=config.settings \
		config.wsgi

## build_docs   : build static docs in `site`
build_docs :
	mkdocs build

## serve_docs   : serve docs at `localhost:8000`
serve_docs :
	mkdocs serve
