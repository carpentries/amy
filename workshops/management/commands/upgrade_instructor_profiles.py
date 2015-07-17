import re
import csv

from django.core.management.base import BaseCommand, CommandError

from workshops.models import (
    Person, Airport, Lesson, KnowledgeDomain, Qualification, Badge
)

TXLATE_HEADERS = {
    'Timestamp': 'timestamp',
    'Personal (first) name': 'personal',
    'Family (last) name': 'family',
    'Email address': 'email',
    'Nearest major airport': 'airport',
    'GitHub username': 'github',
    'Twitter username': 'twitter',
    'Personal website': 'url',
    'Gender': 'gender',
    'Areas of expertise': 'domains',
    'Software Carpentry topics you are comfortable teaching':
        'software-carpentry',
    'ORCID ID': 'orcid',
    'Data Carpentry lessons you are comfortable teaching':
        'data-carpentry',
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
        ('Programming with Python', 'swcarpentry',
         'python-novice-inflammation', 'swc/python'),
        ('Programming with R', 'swcarpentry', 'r-novice-inflammation',
         'swc/r'),
        ('Programming with MATLAB', 'swcarpentry',
         'matlab-novice-inflammation', 'swc/matlab'),
        ('Data Organization in Spreadsheets', 'datacarpentry', 'excel-ecology',
         'dc/spreadsheets'),
        ('The Unix Shell', 'datacarpentry', 'shell-ecology', 'dc/shell'),
        ('Data Analysis and Visualization in R', 'datacarpentry', 'R-ecology',
         'dc/r'),
        ('Data Analysis and Visualization in Python', 'datacarpentry',
         'python-ecology', 'dc/python'),
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


class Command(BaseCommand):
    help = 'Update profiles for instructors'

    _cache = dict()

    def add_arguments(self, parser):
        parser.add_argument(
            'filename', help='CSV file with instructor profile survey results',
        )

        parser.add_argument(
            '--force', action='store_true', default=False,
            help='Upgrade all correct instructor entries',
        )

    def handle(self, *args, **options):
        filename = options['filename']
        force = options['force']

        upgrade_all = True
        upgrade_ready = list()
        with open(filename, 'r') as f:
            if force:
                self.stdout.write('Upgrading all entries that are correct.')

            i = 1
            for entry in self.process(f):
                correct, errors, warnings = self.check_entry(entry)
                if correct and force:
                    self.update(entry)
                elif correct and not force:
                    upgrade_ready.append(entry)
                elif not correct:
                    upgrade_all = False

                if errors:
                    try:
                        for error in errors:
                            self.stderr.write(
                                'ERROR: {} {} <{}> (row {}): {}'
                                .format(
                                    entry['personal'], entry['family'],
                                    entry['email'], i, error
                                )
                            )
                    except KeyError:
                        self.stderr.write(
                            'ERROR: (row {}) missing fields: '
                            'personal/family/email'.format(i)
                        )
                if warnings:
                    for warning in warnings:
                        self.stdout.write(
                            'WARNING: {} {} <{}> (row {}): {}'
                            .format(
                                entry['personal'], entry['family'],
                                entry['email'], i, warning
                            )
                        )
                i += 1

        if not force:
            if upgrade_all:
                self.stdout.write('All entries are correct, upgrading...')
                for entry in upgrade_ready:
                    self.update(entry)
            else:
                self.stderr.write('Not all entries are correct, cannot'
                                  ' upgrade.')

    def process(self, csv_file):
        '''Read data into list of dictionaries with well-defined keys.'''
        reader = csv.DictReader(csv_file)
        for record in reader:
            yield self.translate(record)
        return

    def translate(self, record):
        '''Translate single record into dictionary.'''
        # translate human-readable field names to normalized database-ready
        # field names
        new_record = dict()
        try:
            for old_field, new_field in TXLATE_HEADERS.items():
                new_record[new_field] = record[old_field]

            # normalize gender
            new_record['gender'] = self.translate_gender(new_record['gender'])

            # normalize airport (upper-case whole thing)
            new_record['airport'] = new_record['airport'].upper()

            # turn string of domains into a list of domains
            new_record['domains'] = self.translate_domains(
                new_record['domains']
            )

            # translate human-readable lessons to normalized lesson names that
            # we keep in AMY
            new_record['teaching'] = list()
            for name in LIST_FIELDS:
                new_record['teaching'] += self.translate_lessons(
                    new_record[name]
                )
                del new_record[name]
        except KeyError:
            # probably some fields are missing in the CSV
            pass
        finally:
            return new_record

    def translate_gender(self, gender):
        """Return database-ready gender."""
        if not gender:
            return None
        elif gender == 'Male':
            return Person.MALE
        elif gender == 'Female':
            return Person.FEMALE
        else:
            return Person.OTHER

    def translate_domains(self, domains):
        """Extract areas of expertise AKA knowledge domains from the entry."""
        # The trick is that every entry in the line starts with an uppercase.
        # For example "Space sciences, Genetics, genomics" is
        # only composed of 2 entries: "Space sciences" and "Genetics, …".

        # from example: ['Space sciences, ', 'Genetics, genomics']
        domains = re.findall('([A-Z][^A-Z]+)', domains)

        # from example: ['Space sciences', 'Genetics, genomics']
        domains = [domain.rstrip(', ') for domain in domains]
        return domains

    def translate_lessons(self, raw):
        """Convert descriptive lesson names into short slugs we keep in AMY."""
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
            else:
                # in case someone adds a lesson missing in TXLATE_LESSON
                # just add it to the result and handle error/warning later
                result.append(f.strip().lower())
        return result

    def check_entry(self, entry):
        """Check validity of an entry.

        Check existence of corresponding database objects (ie. users, lessons,
        airports).
        Check correctness of data (no missing fields, etc.)"""
        try:
            correct = True
            errors = list()
            warnings = list()

            # check if all required fields are present
            left = set(entry.keys()) - set(['teaching'])
            right = set(TXLATE_HEADERS.values()) - set(LIST_FIELDS)
            if not left == right:
                correct = False
                errors.append('Missing fields: {0}'
                              .format(list(right - left)))

            # check if all required fields aren't empty
            for field in Person.REQUIRED_FIELDS:
                if not entry[field]:
                    correct = False
                    errors.append('Required field "{0}" is empty'
                                  .format(field))

            # check if user exists (match by email)
            person = None
            try:
                person = Person.objects.get(email=entry['email'])
            except Person.DoesNotExist:
                try:
                    person = Person.objects.get(personal=entry['personal'],
                                                family=entry['family'])
                except Person.MultipleObjectsReturned:
                    correct = False
                    errors.append('There are multiple users with this name '
                                  '("{0} {1}")'
                                  .format(entry['personal'], entry['family']))
                except Person.DoesNotExist:
                    correct = False
                    errors.append('User with either this email ("{0}") or '
                                  'this name ("{1} {2}") does not exist'
                                  .format(entry['email'], entry['personal'],
                                          entry['family']))

            # check if the person really is an instructor
            instructor_badge = Badge.objects.get(name='instructor')
            if person and instructor_badge not in person.badges.all():
                # it's not an error, because we want to have that person in the
                # database even though they aren't certified instructor
                warnings.append('This person does not have an instructor'
                                ' badge')

            # cache airport IATA codes
            if 'airports' not in self._cache:
                self._cache['airports'] = Airport.objects.values_list(
                    'iata', flat=True,
                )

            # check if airport exists
            if entry['airport'] not in self._cache['airports']:
                correct = False
                errors.append('Airport "{0}" does not exist'
                              .format(entry['airport']))

            # Don't check if domains exist.
            # There are occasions when instructors add domains we don't have in
            # the database.  This should be no-op.

            # cache domains
            if 'domains' not in self._cache:
                self._cache['domains'] = KnowledgeDomain.objects \
                                                        .values_list('name',
                                                                     flat=True)

            # show domains not in our database, but don't error-out
            for domain in entry['domains']:
                if domain not in self._cache['domains']:
                    warnings.append('Domain "{0}" does not exist'
                                    .format(domain))

            # cache lesson names
            if 'lessons' not in self._cache:
                self._cache['lessons'] = Lesson.objects.values_list('name',
                                                                    flat=True)

            # check if lessons exist
            for lesson in entry['teaching']:
                if lesson not in self._cache['lessons']:
                    correct = False
                    errors.append('Lesson "{0}" does not exist'
                                  .format(lesson))

            return correct, errors, warnings

        except KeyError as e:
            correct = False
            errors.append("Missing fields: {}".format(e))
            return correct, errors, warnings

    def update(self, entry):
        """Update instructor profile in the database."""
        try:
            person = Person.objects.get(email=entry['email'])
        except Person.DoesNotExist:
            person = Person.objects.get(personal=entry['personal'],
                                        family=entry['family'])

        # update personal details
        fields = ['personal', 'family', 'email', 'gender', 'github', 'twitter',
                  'url', 'affiliation']
        for field in fields:
            setattr(person, field, entry[field])

        # update related fields
        person.airport = Airport.objects.get(iata=entry['airport'])

        person.domains = KnowledgeDomain.objects.filter(
            name__in=entry['domains']
        )

        person.save()

        # The easiest syntax person.lessons = [] doesn't work because we're
        # using intermediate M2M model Qualifications
        Qualification.objects.filter(person=person).delete()
        lessons = Lesson.objects.filter(name__in=entry['teaching'])
        for lesson in lessons:
            Qualification.objects.create(person=person, lesson=lesson)
