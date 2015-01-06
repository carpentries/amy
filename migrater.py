import datetime
import logging
import sqlite3
import sys

# Faking data?
FAKE = True

def fail(table, fields, exc):
    '''Report failure.'''
    logging.error("Failing on {table} with {fields} because {error}".format(
            table=table, fields=fields, error=e))
    sys.exit(1)


def info(table):
    '''Report successful migration of given table.'''
    logging.info("Successfully migrated '{table}' table".format(table=table))


def fake(i, slug, personal, middle, family, email, gender, github, twitter, url):
    '''Redact personal identifying information.'''
    if not FAKE:
        return slug, personal, middle, family, email, gender, github, twitter, url
    where = 'I{0}.edu'.format(i)
    return 'S{0}'.format(i), \
           'F{0}'.format(i), \
           'M{0}'.format(i), \
           'L{0}'.format(i), \
           '{0}@{1}'.format(i, where), \
           ('M', 'F', 'O')[i % 3], \
           'U_{0}'.format(i), \
           '@U{0}'.format(i), \
           'http://{0}/U_{1}'.format(where, i)

assert len(sys.argv) == 3, 'Usage: migrater.py /path/to/src.db /path/to/dst.db'

old_cnx = sqlite3.connect(sys.argv[1])
old_crs = old_cnx.cursor()
new_cnx = sqlite3.connect(sys.argv[2])
new_crs = new_cnx.cursor()

# Site
new_crs.execute('delete from workshops_site;')
old_crs.execute('select site, fullname, country from site;')
site_lookup = {}
i = 1
for (site, fullname, country) in old_crs.fetchall():
    site_lookup[site] = i
    try:
        fields = (i, site, fullname, country, '')
        new_crs.execute('insert into workshops_site values(?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('site', fields, e)
    i += 1

info('site')

# Airport
new_crs.execute('delete from workshops_airport;')
old_crs.execute('select fullname, country, latitude, longitude, iata from airport;')
airport_lookup = {}
i = 1
for (fullname, country, lat, long, iata) in old_crs.fetchall():
    airport_lookup[iata] = i
    try:
        fields = (i, fullname, country, lat, long, iata)
        new_crs.execute('insert into workshops_airport values(?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('airport', fields, e)
    i += 1

info('airport')

# load Facts for lookup in Person
old_crs.execute('select person, gender, active, airport, github, twitter, site from facts;')
facts_lookup = {}
for record in old_crs.fetchall():
    person = record[0]
    facts_lookup[person] = record[1:]

# Person
new_crs.execute('delete from workshops_person;')
old_crs.execute('select person, personal, middle, family, email from person;')
person_lookup = {}
i = 1
for (person, personal, middle, family, email) in old_crs.fetchall():
    person_lookup[person] = i
    if person in facts_lookup:
        gender, active, airport, github, twitter, url = facts_lookup[person]
    else:
        gender, active, airport, github, twitter, url = None, None, None, None, None, None

    person, personal, middle, family, email, gender, github, twitter, url = \
        fake(i, person, personal, middle, family, email, gender, github, twitter, url)
    if airport is not None:
        airport = airport_lookup[airport]

    try:
        fields = (i, personal, middle, family, email, active, airport, github, twitter, url, person, gender)
        new_crs.execute('insert into workshops_person values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('person', fields, e)
    i += 1

info('person')

# Project (kinds of event)
new_crs.execute('delete from workshops_project;')
i = 1
project_lookup = {}
for (slug, name, details) in (('SWC', 'Software Carpentry', 'General Software Carpentry workshop'),
                              ('DC',  'Data Carpentry', 'General Data Carpentry workshop'),
                              ('LC',  'Library Carpentry', 'Workshop for librarians'),
                              ('WiSE', 'Women in Science & Engineering', 'Women-only events')):
    project_lookup[slug] = i
    try:
        fields = (i, slug, name, details)
        new_crs.execute('insert into workshops_project values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('project', fields, e)
    i += 1

info('project')

# Event
new_crs.execute('delete from workshops_event;')
old_crs.execute('select startdate, enddate, event, site, kind, eventbrite, attendance, url from event;')
event_lookup = {}
i = 1
for (startdate, enddate, event, site, kind, eventbrite, attendance, url) in old_crs.fetchall():
    event_lookup[event] = i
    try:
        fields = (i, startdate, enddate, eventbrite, attendance, site_lookup[site], project_lookup[kind], url, None, 0.0, "", True, event)
        new_crs.execute('insert into workshops_event values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('event', fields, e)
    i += 1

info('event')

# Add some unpublished events for testing purposes.
new_crs.execute('select * from workshops_event where (id>=?) and (id<=?);', ((i-10), (i-5)))
records = new_crs.fetchall()
for r in records:
    try:
        r = list(r)
        r[0] = i # new ID
        r[1] = None # no start date
        r[2] = None # no end date
        r[3] = None # no registration key
        r[4] = None # no attendance
        r[7] = None # no URL
        r[11] = False # not published - this is the whole point of these entries
        r[12] = None # no slug
        new_crs.execute('insert into workshops_event values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', r)
    except Exception, e:
        fail('event', fields, e)
    i += 1

# Roles
new_crs.execute('delete from workshops_role;')
i = 1
role_lookup = {}
for role in 'helper instructor host learner organizer tutor'.split():
    role_lookup[role] = i
    try:
        fields = (i, role)
        new_crs.execute('insert into workshops_role values(?, ?);', fields)
    except Exception, e:
        fail('role', fields, e)
    i += 1

info('roles')

# Tasks
new_crs.execute('delete from workshops_task;')
old_crs.execute('select event, person, task from task;')
i = 1
for (event, person, task) in old_crs.fetchall():
    try:
        fields = (i, event_lookup[event], person_lookup[person], role_lookup[task])
        new_crs.execute('insert into workshops_task values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('task', fields, e)
    i += 1

info('task')

# Cohorts
new_crs.execute('delete from workshops_cohort;')
old_crs.execute('select startdate, cohort, active, venue from cohort;')
i = 1
cohort_lookup = {}
cohort_start = {}
for (start, name, active, venue) in old_crs.fetchall():
    cohort_lookup[name] = i
    cohort_start[name] = start
    try:
        if venue == 'online':
            venue = None
        qualifies = name != 'live-01'
        if venue is not None:
            venue = site_lookup[venue]
        fields = (i, start, name, active, venue, qualifies)
        new_crs.execute('insert into workshops_cohort values(?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('cohort', fields, e)
    i += 1

info('cohort')

# Trainee statuses (statii?)
new_crs.execute('delete from workshops_traineestatus;')
i = 1
traineestatus_lookup = {}
for traineestatus in 'registered in_progress complete incomplete'.split():
    traineestatus_lookup[traineestatus] = i
    try:
        fields = (i, traineestatus)
        new_crs.execute('insert into workshops_traineestatus values(?, ?);', fields)
    except Exception, e:
        fail('traineestatus', fields, e)
    i += 1

info('traineestatus')

# Trainees
new_crs.execute('delete from workshops_trainee;')
old_crs.execute('select person, cohort, status from trainee;')
i = 1
today = datetime.date.today().isoformat()
for (person, cohort, status) in old_crs.fetchall():
    if status in ('complete', 'learner'):
        status = traineestatus_lookup['complete']
    elif status in ('incomplete', 'withdrew'):
        status = traineestatus_lookup['incomplete']
    elif cohort_start[cohort] >= today:
        status = traineestatus_lookup['registered']
    else:
        status = traineestatus_lookup['in_progress']
    try:
        fields = (i, cohort_lookup[cohort], person_lookup[person], status)
        new_crs.execute('insert into workshops_trainee values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('trainee', fields, e)
    i += 1

info('trainee')

# Skills
new_crs.execute('delete from workshops_skill;')
old_crs.execute('select distinct skill from skills;')
i = 1
skill_lookup = {}
for (skill,) in old_crs.fetchall():
    skill_lookup[skill] = i
    try:
        fields = (i, skill)
        new_crs.execute('insert into workshops_skill values(?, ?);', fields)
    except Exception, e:
        fail('skill', fields, e)
    i += 1

info('skill')

# Qualifications
new_crs.execute('delete from workshops_qualification;')
old_crs.execute('select person, skill from skills;')
i = 1
for (person, skill) in old_crs.fetchall():
    try:
        fields = (i, person_lookup[person], skill_lookup[skill])
        new_crs.execute('insert into workshops_qualification values(?, ?, ?);', fields)
    except Exception, e:
        fail('qualification', fields, e)
    i += 1

info('qualification')

# Badges
new_crs.execute('delete from workshops_badge;')
old_crs.execute('select badge, title, criteria from badges;')
i = 1
badge_lookup = {}
for (badge, title, criteria) in old_crs.fetchall():
    badge_lookup[badge] = i
    try:
        fields = (i, badge, title, criteria)
        new_crs.execute('insert into workshops_badge values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('badge', fields, e)
    i += 1

info('badge')

# Awards
new_crs.execute('delete from workshops_award;')
old_crs.execute('select person, badge, awarded from awards;')
i = 1
for (person, badge, awarded) in old_crs.fetchall():
    try:
        fields = (i, awarded, badge_lookup[badge], person_lookup[person])
        new_crs.execute('insert into workshops_award values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('award', fields, e)
    i += 1

info('award')

# Finish
new_cnx.commit()
