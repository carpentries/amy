#!/usr/bin/env python

'''Load instructor information spreadsheet.'''

import sys
import csv
import re
import getopt

TXLATE_HEADERS = {
    'Timestamp': 'timestamp',
    'Personal (first) name': 'personal',
    'Family (last) name': 'family',
    'Email address': 'email',
    'Nearest major airport': 'airport',
    'GitHub username': 'github',
    'Twitter username': 'twitter',
    'Personal website': 'website',
    'Gender': 'gender',
    'Areas of expertise': 'domain',
    'Software Carpentry topics you are comfortable teaching': 'software-carpentry',
    'ORCID ID': 'orcid',
    'Data Carpentry lessons you are comfortable teaching': 'data-carpentry',
    'Affiliation': 'affiliation',
    'What is your current occupation/career stage?': 'position'
}

TXLATE_LESSON = [
    (re.compile('{0}.+{1}.+{2}'.format(title, org, slug)), label)
    for (title, org, slug, label) in
    [
        ('Unix Shell', 'swcarpentry', 'shell-novice', 'swc/shell'),
        ('Git', 'swcarpentry', 'git-novice', 'swc/git'),
        ('Mercurial', 'swcarpentry', 'hg-novice', 'swc/hg'),
        ('Databases and SQL', 'swcarpentry', 'sql-novice-survey', 'swc/sql'),
        ('Programming with Python', 'swcarpentry', 'python-novice-inflammation', 'swc/python'),
        ('Programming with R', 'swcarpentry', 'r-novice-inflammation', 'swc/r'),
        ('Programming with MATLAB', 'swcarpentry', 'matlab-novice-inflammation', 'swc/matlab'),
        ('Data Organization in Spreadsheets', 'datacarpentry', 'excel-ecology', 'dc/spreadsheets'),
        ('The Unix Shell', 'datacarpentry', 'shell-ecology', 'dc/shell'),
        ('Data Analysis and Visualization in R', 'datacarpentry', 'R-ecology', 'dc/r'),
        ('Data Analysis and Visualization in Python', 'datacarpentry', 'python-ecology', 'dc/python'),
        ('Databases and SQL', 'datacarpentry', 'sql-ecology', 'dc/sql'),
        ('Cloud Computing', 'datacarpentry', 'cloud-genomics', 'dc/cloud')
    ]
] + [
    (re.compile(r'The Shell for Ecologists'), 'dc/shell'),
    (re.compile(r'Python for Ecologists'), 'dc/python'),
    (re.compile(r'SQL for Ecologists'), 'dc/sql'),
    (re.compile(r'regular expression', re.IGNORECASE), 'swc/regexp'),
    (re.compile(r'make', re.IGNORECASE), 'swc/make')
]

LIST_FIELDS = ('software-carpentry', 'data-carpentry')


def main(argv):
    '''Main driver.'''

    settings = parse_args(argv)
    if settings['filename']:
        with open(settings['filename'], 'r') as reader:
            data = process(settings, reader)
    else:
        data = process(settings, sys.stdin)
    display(settings, data)


def parse_args(args):
    '''Parse command-line arguments.'''

    settings = {'filename': None,
                'report_unknown': True}

    options, extras = getopt.getopt(sys.argv[1:], 'u')
    for (opt, arg) in options:
        if opt == '-u':
            settings['report_unknown'] = False

    if extras:
        assert len(extras) == 1, \
            'Can only parse one file'
        settings['filename'] = extras[0]

    return settings


def process(settings, raw):
    '''Read data into list of dictionaries with well-defined keys.'''

    cooked = csv.reader(raw)
    columns = None
    data = []
    for record in cooked:
        if columns is None:
            columns = get_columns(settings, record)
        else:
            data.append(translate(settings, columns, record))
    return data


def get_columns(settings, headers):
    '''Construct mapping from column titles to field names.'''

    result = [None] * len(headers)
    for (i, actual) in enumerate(headers):
        assert actual in TXLATE_HEADERS, \
            'Actual header "{0}" not found in translation table'.format(actual)
        result[i] = TXLATE_HEADERS[actual]
    assert not any([x is None for x in result]), \
        'Field or fields not filled in for headers'
    return result


def translate(settings, columns, record):
    '''Translate single record into dictionary.'''

    info = {}
    for (i, field) in enumerate(record):
        info[columns[i]] = field

    info['teaching'] = []
    for name in LIST_FIELDS:
        info['teaching'] += txlate_list(settings, name, info[name])
        del info[name]

    return info


def txlate_list(settings, name, raw):
    if not raw:
        return []
    fields = [x.strip() for x in raw.replace('e.g.,', '').split(',')]
    result = []
    for f in fields:
        found = None
        for (pattern, label) in TXLATE_LESSON:
            if pattern.search(f):
                found = label
                break
        if found:
            result.append(found)
        elif settings['report_unknown']:
            print('unknown lesson "{0}" for "{1}"'.format(f, name), file=sys.stderr)
    return result


def display(settings, data):
    '''Show data as text.'''

    for record in data:
        print(record)


if __name__ == '__main__':
   main(sys.argv)
