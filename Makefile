# Where original database lives (only on Software Carpentry administrator's machine).
DB_SRC = ~/s/admin/roster.db

# Database used by this application.
DB_APP = db.sqlite3

# Saved SQL for regenerating the database.
DB_SQL = db.sql

# Run a SQL query.
QUERY = sqlite3 ${DB_APP}
QUERY_CSV = sqlite3 -csv ${DB_APP}

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
	${QUERY} .dump > ${DB_SQL}

## database     : re-make database using saved data
database :
	rm -f ${DB_APP}
	${QUERY} < ${DB_SQL}

## serve        : run a server
serve :
	python manage.py runserver

## clean        : clean up.
clean :
	rm -f \
	$$(find . -name '*~' -print) \
	$$(find . -name '*.pyc' -print) \
	${DB_APP}

## members      : who qualifies as a SCF member?
# FIXME: should be able to do this as a union to eliminate duplicates
members : ${DB_APP}
	@${QUERY} "select name from (select p.id as pid, p.personal || ' ' || p.family || ' <' || p.email || '>' as name, count(*) as num from workshops_person p join workshops_task t join workshops_role r join workshops_event e on (p.id=t.person_id and t.role_id=r.id and r.name='instructor' and t.event_id=e.id) where (e.start>='2013-01-01') group by p.id) where num>=2;"
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_person p join workshops_award a join workshops_badge b on p.id=a.person_id and a.badge_id=b.id and b.name='member';"

## report       : run statistical reports on database.
report : ${DB_APP}
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
check : ${DB_APP}
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
	@${QUERY} "select e.slug from workshops_event e where e.attendance is null and e.start<date('now');"
	@echo ""
	@echo "Checking for learners who were simultaneously instructors or helpers..."
	@${QUERY} "select event_a.slug, person_a.id || ': ' || person_a.personal || ' ' || person_a.family, role_a.name, role_b.name from workshops_event event_a join workshops_event event_b join workshops_person person_a join workshops_person person_b join workshops_role role_a join workshops_role role_b join workshops_task task_a join workshops_task task_b on ((event_a.id=task_a.event_id) and (event_b.id=task_b.event_id) and (person_a.id=task_a.person_id) and (person_b.id=task_b.person_id) and (role_a.id=task_a.role_id) and (role_b.id=task_b.role_id) and (event_a.id=event_b.id) and (person_a.id=person_b.id)) where (role_a.name='learner') and (role_b.name in ('instructor', 'helper'));"
	@echo ""
	@echo "Checking for workshops without instructors..."
	@${QUERY} "select distinct slug from workshops_event where id not in (select distinct event_id from workshops_task where role_id=(select id from workshops_role where name='instructor'));"
	@echo ""
	@echo "Checking for people who have completed training but are not yet badged..."
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>'from workshops_person p join workshops_trainee t join workshops_traineestatus ts on ((p.id=t.person_id) and (t.status_id=ts.id) and (ts.name='complete')) where p.id not in (select a.person_id from workshops_award a join workshops_badge b on (a.badge_id=b.id) where (b.name='instructor'));"
	@echo ""
	@echo "Checking for people who have badges but are still in training..."
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>: ' || c.name from workshops_person p join workshops_award a join workshops_badge b join workshops_cohort c join workshops_trainee t join workshops_traineestatus ts on (p.id=a.person_id and a.badge_id=b.id and t.person_id=p.id and c.id=t.cohort_id and t.status_id=ts.id) where (b.name='instructor' and ts.name='in_progress');"
	@echo ""
	@echo "Checking for people who are still incomplete for completed training rounds..."
	@${QUERY} "select c.name || ': ' || p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_cohort c join workshops_person p join workshops_trainee t join workshops_traineestatus ts on (c.id=t.cohort_id and t.person_id=p.id and t.status_id=ts.id) where ((not c.active) and (ts.name in ('registered', 'incomplete'))) order by c.start;"
	@echo ""
	@echo "Checking for instructors whose skills we don't know..."
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_person p join workshops_award a join workshops_badge b on (p.id=a.person_id and a.badge_id=b.id and b.name='instructor') where p.id not in (select distinct person_id from workshops_qualification);"
	@echo ""
	@echo "Checking for instructors whose location we don't know..."
	@${QUERY} "select p.personal || ' ' || p.family || ' <' || p.email || '>' from workshops_person p join workshops_award a join workshops_badge b on (p.id=a.person_id and a.badge_id=b.id and b.name='instructor') where p.airport_id is null;"
