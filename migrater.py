import sys
import sqlite3

def fail(table, fields, exc):
    print >> sys.stderr, 'failing on', table, 'with', fields, 'because', str(e)
    sys.exit(1)

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
        fields = (i, site, fullname, country)
        new_crs.execute('insert into workshops_site values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('site', fields, e)
    i += 1
new_cnx.commit()

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
new_cnx.commit()

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
    try:
        fields = (i, personal, middle, family, email, gender, active, airport, github, twitter, url)
        new_crs.execute('insert into workshops_person values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('person', fields, e)
    i += 1
new_cnx.commit()

# Event
new_crs.execute('delete from workshops_event;')
old_crs.execute('select startdate, enddate, event, site, kind, eventbrite, attendance from event;')
event_lookup = {}
i = 1
for (startdate, enddate, event, site, kind, eventbrite, attendance) in old_crs.fetchall():
    event_lookup[event] = i
    try:
        fields = (i, startdate, event, kind, eventbrite, attendance, site_lookup[site], enddate)
        new_crs.execute('insert into workshops_event values(?, ?, ?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail(event, fields, e)
    i += 1
new_cnx.commit()

# Roles
new_crs.execute('delete from workshops_role;')
i = 1
role_lookup = {}
for role in 'helper instructor host learner tutor organizer'.split():
    role_lookup[role] = i
    try:
        fields = (i, role)
        new_crs.execute('insert into workshops_role values(?, ?);', fields)
    except Exception, e:
        fail('role', fields, e)
    i += 1

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
new_cnx.commit()

# Cohorts
new_crs.execute('delete from workshops_cohort;')
old_crs.execute('select startdate, cohort, active, venue from cohort;')
i = 1
cohort_lookup = {}
for (start, name, active, venue) in old_crs.fetchall():
    cohort_lookup[name] = i
    try:
        if venue == 'online':
            venue = None
        qualifies = name != 'live-01'
        fields = (i, start, name, active, venue, qualifies)
        new_crs.execute('insert into workshops_cohort values(?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        fail('cohort', fields, e)
    i += 1
new_cnx.commit()

# Trainees
new_crs.execute('delete from workshops_trainee;')
old_crs.execute('select person, cohort, status from trainee;')
i = 1
for (person, cohort, status) in old_crs.fetchall():
    if status in ('complete', 'learner'):
        complete = True
    elif status in ('incomplete', 'withdrew'):
        complete = False
    else:
        complete = None
    try:
        fields = (i, complete, cohort_lookup[cohort], person_lookup[person])
        new_crs.execute('insert into workshops_trainee values(?, ?, ?, ?);', fields)
    except Exception, e:
        fail('trainee', fields, e)
    i += 1
new_cnx.commit()

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
new_cnx.commit()

# Qualifications?
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
new_cnx.commit()
