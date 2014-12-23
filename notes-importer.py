#!/usr/bin/env python

'''Import old notes about sites and events, reporting mis-matches.'''

import sys
import os
import sqlite3

def esc(text):
    '''Escape quotes'''
    return text.replace('"', r'""').replace("'", r"''")

def get_all(cursor, query):
    '''Get a list of single elements from a query.'''
    cursor.execute(query)
    return [str(x[0]) for x in cursor.fetchall()]

def get_files(path):
    '''Get all .txt files in a directory.'''
    return [(x.rstrip('.txt'), x) for x in os.listdir(path) if x.endswith('.txt')]

def report(title, items):
    '''Display items with title.'''
    print
    print title
    print '\n'.join(items)

def update(base_dir, slugs_and_filenames, slugs, query_template):
    '''Look for matches and mis-matches, updating notes along the way.'''
    unused = set()
    for (slug, filename) in slugs_and_filenames:
        if slug in slugs:
            with open(os.path.join(base_dir, filename)) as reader:
                data = reader.read()
            stmt = query_template.format(esc(data), slug)
            cursor.execute(stmt)
        else:
            unused.add(filename)
    return unused

# Parameters.
assert len(sys.argv) == 4, 'Usage: notes-importer.py db_path events_dir sites_dir'
db_path, events_dir, sites_dir = sys.argv[1:]

# Hook up.
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

# Clear existing entries.
cursor.execute('update workshops_event set notes="";')
cursor.execute('update workshops_site set notes="";')

# Raw data for events.
event_slugs = set(get_all(cursor, 'select slug from workshops_event;'))
event_files = get_files(events_dir)

# Iterate.
unused_files = update(events_dir, event_files, event_slugs, 'update workshops_event set notes="{0}" where slug="{1}";')

# Report.
report('matched events', get_all(cursor, 'select slug from workshops_event where notes!="";'))
report('unmatched events', get_all(cursor, 'select slug from workshops_event where notes="";'))
report('unmatched event files', unused_files)

# Raw data for sites.
site_domains = set(get_all(cursor, 'select domain from workshops_site;'))
site_files = get_files(sites_dir)

# Iterate.
unused_files = update(sites_dir, site_files, site_domains, 'update workshops_site set notes="{0}" where domain="{1}";')

# Report.
report('matched sites', get_all(cursor, 'select domain from workshops_site where notes!="";'))
report('unmatched sites', get_all(cursor, 'select domain from workshops_site where notes="";'))
report('unmatched site files', unused_files)

# Commit changes.
connection.commit()
