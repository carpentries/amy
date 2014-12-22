#!/usr/bin/env python

'''Import old notes about sites and events.'''

import sys
import sqlite3
import os

def esc(text):
    '''Escape quotes'''
    return text.replace('"', r'""').replace("'", r"''")

# Parameters.
db_path = sys.argv[1]
events_dir = sys.argv[2]
sites_dir = sys.argv[3]

# Hook up.
connection = sqlite3.connect(db_path)
cursor = connection.cursor()
cursor.execute('update workshops_event set notes="";')

# Events in database.
cursor.execute('select slug from workshops_event;')
event_slugs = set([str(x[0]) for x in cursor.fetchall()])

# Events in files.
event_files = [(x.rstrip('.txt'), x) for x in os.listdir(events_dir) if x.endswith('.txt')]

# Iterate.
unused_files = set()
for (slug, filename) in event_files:
    if slug in event_slugs:
        with open(os.path.join(events_dir, filename)) as reader:
            data = reader.read()
        stmt = 'update workshops_event set notes="{0}" where slug="{1}";'.format(esc(data), slug)
        cursor.execute(stmt)
    else:
        unused_files.add(filename)

print
print 'unused files:', unused_files

cursor.execute('select slug from workshops_event where notes="";')
unused_slugs = [str(x[0]) for x in cursor.fetchall()]
print
print 'unused slugs:', unused_slugs

cursor.execute('select slug from workshops_event where notes!="";')
used_slugs = [str(x[0]) for x in cursor.fetchall()]
print
print 'used slugs:', used_slugs

connection.commit()
