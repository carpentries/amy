import sys
import sqlite3

cnx = sqlite3.connect(sys.argv[1])
crs = cnx.cursor()

print 'delete from workshops_site;'
crs.execute('select site, fullname, country from site;')
i = 1
for (site, fullname, country) in crs.fetchall():
    print 'insert into workshops_site values({0}, "{1}", "{2}", "{3}");'.format(i, site, fullname, country)
    i += 1

print 'delete from workshops_airport;'
crs.execute('select fullname, country, latitude, longitude, iata from airport;')
i = 1
for (fullname, country, lat, long, iata) in crs.fetchall():
    print 'insert into workshops_airport values({0}, "{1}", "{2}", {3}, {4}, "{5}");'.format(i, fullname, country, lat, long, iata)
    i += 1
