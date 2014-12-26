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
	python migrater.py ${DB_SRC} ${DB_APP}
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

## check        : run sanity checks on database.
check : ${DB_APP}
	@echo "Checking for unused people..."
	@sqlite3 ${DB_APP} "select id || ': ' || personal || ' ' || family from workshops_person where id not in (select distinct person_id from workshops_task union select distinct person_id from workshops_trainee union select distinct person_id from workshops_award);"
	@echo "Checking for spaces in person slugs..."
	@sqlite3 ${DB_APP} "select id || ': ' || personal || ' ' || family from workshops_person where slug like '% %';"
	@echo "Checking for spaces in event identifiers..."
	@sqlite3 ${DB_APP} "select id || ' ' || slug from workshops_event where slug like '% %';"
	@echo "Checking for lowercase names..."
	@sqlite3 ${DB_APP} "select id || ' ' || personal || ' ' || family from workshops_person where personal=lower(personal) or (family != '' and family=lower(family));"
	@echo "Checking for learners who were simultaneously instructors or helpers..."
	@sqlite3 ${DB_APP} "select event_a.slug, person_a.id || ': ' || person_a.personal || ' ' || person_a.family, role_a.name, role_b.name from workshops_event event_a join workshops_event event_b join workshops_person person_a join workshops_person person_b join workshops_role role_a join workshops_role role_b join workshops_task task_a join workshops_task task_b on (event_a.id=task_a.event_id) and (event_b.id=task_b.event_id) and (person_a.id=task_a.person_id) and (person_b.id=task_b.person_id) and (role_a.id=task_a.role_id) and (role_b.id=task_b.role_id) and (event_a.id=event_b.id) and (person_a.id=person_b.id) and (role_a.name='learner') and (role_b.name in ('instructor', 'helper'));"
	@echo "Checking for workshops without instructors..."
	@sqlite3 ${DB_APP} "select distinct slug from workshops_event where id not in (select distinct event_id from workshops_task where role_id=(select id from workshops_role where name='instructor'));"
	@echo "Checking for people who have completed training but are not yet badged..."
	@sqlite3 ${DB_APP} "select p.id || ' ' || p.personal || ' ' || p.family from workshops_person p join workshops_trainee t join workshops_traineestatus ts on (p.id=t.person_id) and (t.status_id=ts.id) and (ts.name='complete') where p.id not in (select a.person_id from workshops_award a join workshops_badge b on (a.badge_id=b.id) where (b.name='instructor'));"
