import sys
import sqlite3

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
        print >> sys.stderr, 'failing on site with', fields, 'because', str(e)
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
        print >> sys.stderr, 'failing on airport with', fields, 'because', str(e)
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
        print >> sys.stderr, 'failing on person with', fields, 'because', str(e)
    i += 1
new_cnx.commit()

# Event
new_crs.execute('delete from workshops_event;')
old_crs.execute('select startdate, enddate, event, site, kind, eventbrite, attendance from event;')
i = 1
for (startdate, enddate, event, site, kind, eventbrite, attendance) in old_crs.fetchall():
    try:
        fields = (i, startdate, event, kind, eventbrite, attendance, site_lookup[site], enddate)
        new_crs.execute('insert into workshops_event values(?, ?, ?, ?, ?, ?, ?, ?);', fields)
    except Exception, e:
        print >> sys.stderr, 'failing on event with', fields, 'because', str(e)
    i += 1
new_cnx.commit()
