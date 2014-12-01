import sys
import sqlite3

old_cnx = sqlite3.connect(sys.argv[1])
old_crs = old_cnx.cursor()
new_cnx = sqlite3.connect(sys.argv[2])
new_crs = new_cnx.cursor()

new_crs.execute('delete from workshops_site;')
old_crs.execute('select site, fullname, country from site;')
site_lookup = {}
i = 1
for (site, fullname, country) in old_crs.fetchall():
    site_lookup[site] = i
    try:
        new_crs.execute('insert into workshops_site values(?, ?, ?, ?);', \
                        (i, site, fullname, country))
    except Exception, e:
        print >> sys.stderr, 'failing on site with', (site, fullname, country), 'because', str(e)
    i += 1
new_cnx.commit()

new_crs.execute('delete from workshops_event;')
old_crs.execute('select startdate, enddate, event, site, kind, eventbrite, attendance from event;')
i = 1
for (startdate, enddate, event, site, kind, eventbrite, attendance) in old_crs.fetchall():
    try:
        new_crs.execute('insert into workshops_event values(?, ?, ?, ?, ?, ?, ?, ?);', \
                        (i, startdate, event, kind, eventbrite, attendance, site_lookup[site], enddate))
    except Exception, e:
        print >> sys.stderr, 'failing on event with', (i, site, startdate, enddate, event, kind, eventbrite, attendance), 'because', str(e)
    i += 1
new_cnx.commit()

new_crs.execute('delete from workshops_airport;')
old_crs.execute('select fullname, country, latitude, longitude, iata from airport;')
i = 1
for (fullname, country, lat, long, iata) in old_crs.fetchall():
    try:
        new_crs.execute('insert into workshops_airport values(?, ?, ?, ?, ?, ?);', \
                        (i, fullname, country, lat, long, iata))
    except Exception, e:
        print >> sys.stderr, 'failing on airport with', (i, fullname, country, lat, long, iata), 'because', str(e)
    i += 1
new_cnx.commit()
