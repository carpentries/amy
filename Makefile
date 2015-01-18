# Where original data lives.
SRC_DIR = ~/s/admin

# Where original database lives (only on Software Carpentry administrator's machine).
SRC_DB = ~/s/admin/roster.db

# Database used by this application.
APP_DB = db.sqlite3

# Saved SQL for regenerating the database.
APP_SQL = db.sql

# Where event notes live.
SRC_EVENTS = ${SRC_DIR}/bootcamp-notes/archive

# Where site notes live.
SRC_SITES = ${SRC_DIR}/bootcamp-notes/negotiating

# Run a SQL query.
QUERY = sqlite3 ${APP_DB}
QUERY_CSV = sqlite3 -csv ${APP_DB}

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
	${QUERY} .schema > schema.sql

## import       : import and save legacy data
import :
	python migrater.py ${SRC_DB} ${APP_DB}
	${QUERY} .dump > ${APP_SQL}

## database     : re-make database using saved data
database :
	rm -f ${APP_DB}
	${QUERY} < ${APP_SQL}

## notes        : load old notes
notes :
	python notes-importer.py ${APP_DB} ${SRC_EVENTS} ${SRC_SITES}

## serve        : run a server
serve :
	python manage.py runserver

## clean        : clean up.
clean :
	rm -rf \
	$$(find . -name '*~' -print) \
	$$(find . -name '*.pyc' -print) \
	htmlerror \
	${APP_DB}

## members      : who qualifies as a SCF member?
# FIXME: should be able to do this as a union to eliminate duplicates
members : ${APP_DB}
	@${QUERY} "select name from (select p.id as pid, p.personal || ' ' || p.family || ' <' || p.email || '>' as name, count(*) as num from workshops_person p join workshops_task t join workshops_role r join workshops_event e on (p.id=t.person_id and t.role_id=r.id and r.name='instructor' and t.event_id=e.id) where (e.start>='2013-01-01') group by p.id) where num>=2;"
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_person p join workshops_award a join workshops_badge b on p.id=a.person_id and a.badge_id=b.id and b.name='member';"

## report       : run statistical reports on database.
report : ${APP_DB}
	@echo "Reported workshop enrolment per workshop"
	@echo "workshop,reported,identified"
	@${QUERY_CSV} "select e.slug, e.attendance, count(*) from workshops_event e join workshops_task t join workshops_role r on (e.id=t.event_id and t.role_id=r.id and r.name='learner') group by e.slug;"
	@echo ""
	@echo "Cumulative workshops by date"
	@echo "date,total"
	@${QUERY_CSV} "select start, max(num) from (select e1.start as start, count(e2.start) as num from workshops_event e1 join workshops_event e2 where (e1.start||e1.id)>=(e2.start||e2.id) group by e1.start, e1.id order by e1.start, e1.id) group by start;"
	@echo ""
	@echo "Total number of workshops taught by instructor"
	@echo "count,person"
	@${QUERY_CSV} "select count(*), p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_person p join workshops_task t join workshops_role r on (p.id=t.person_id and t.role_id=r.id and r.name='instructor') group by p.id order by count(*) desc;"
	@echo ""
	@echo "Number of instructors who have taught number of times"
	@echo "count,number"
	@${QUERY_CSV} "select c, count(*) from (select count(*) as c, p.id from workshops_person p join workshops_task t join workshops_role r on (p.id=t.person_id and t.role_id=r.id and r.name='instructor') group by p.id) group by c order by c desc;"
	@echo ""
	@echo "Instructors who have never taught"
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_person p join workshops_award a join workshops_badge b on (p.id=a.person_id and a.badge_id=b.id and b.name='instructor') where p.id not in (select distinct t.person_id from workshops_task t join workshops_role r on (t.role_id=r.id and r.name='instructor'));"
	@echo ""
	@echo "Number of instrutors who have never taught"
	@${QUERY} "select count(*) from workshops_person p join workshops_award a join workshops_badge b on (p.id=a.person_id and a.badge_id=b.id and b.name='instructor') where p.id not in (select distinct t.person_id from workshops_task t join workshops_role r on (t.role_id=r.id and r.name='instructor'));"
	@echo ""
	@echo "Number of trainees per cohort by status"
	@echo "cohort,status,number"
	@${QUERY_CSV} "select c.name, ts.name, count(*) from workshops_cohort c join workshops_trainee t join workshops_traineestatus ts on (c.id=t.cohort_id and t.status_id=ts.id) group by c.id, ts.id order by c.start, ts.name;"

## check        : run sanity checks on database.
check : ${APP_DB}
	@echo "Checking for unused people..."
	@${QUERY} "select id || ': ' || personal || ' ' || family from workshops_person where id not in (select distinct person_id from workshops_task union select distinct person_id from workshops_trainee union select distinct person_id from workshops_award);"
	@echo ""
	@echo "Checking for spaces in person slugs..."
	@${QUERY} "select id || ': ' || personal || ' ' || family from workshops_person where slug like '% %';"
	@echo ""
	@echo "Checking for spaces in event identifiers..."
	@${QUERY} "select id || ' ' || slug from workshops_event where slug like '% %';"
	@echo ""
	@echo "Checking for all-lowercase names..."
	@${QUERY} "select id || ' ' || personal || ' ' || family from workshops_person where personal=lower(personal) or (family != '' and family=lower(family));"
	@echo ""
	@echo "Checking for unknown enrolment..."
	@${QUERY}
