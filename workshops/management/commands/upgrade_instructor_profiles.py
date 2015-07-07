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
        ('Programming with Python', 'swcarpentry',
         'python-novice-inflammation', 'swc/python'),
        ('Programming with R', 'swcarpentry', 'r-novice-inflammation',
         'swc/r'),
        ('Programming with MATLAB', 'swcarpentry',
         'matlab-novice-inflammation', 'swc/matlab'),
        ('Data Organization in Spreadsheets', 'datacarpentry', 'excel-ecology',
         'dc/spreadsheet'),
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
    args = 'filename'
    help = 'Update profiles for instructors'

    _cache = dict()

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('No CSV filename specified')

        filename = args[0]

        invalid = list()
        with open(filename, 'r') as f:
            for entry in self.process(f):
                correct, reasons = self.check_entry(entry)
                if correct:
                    self.update(entry)
                else:
                    invalid.append((entry, reasons))

        for entry, reasons in invalid:
            print('{0} {1} <{2}>'.format(entry['personal'], entry['family'],
                                         entry['email']))
            print('Reasons: \n- {0}'.format("\n- ".join(reasons)))

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

            # normalize airport (just use first 3 letters of the input, all
            # upper-case)
            new_record['airport'] = new_record['airport'][0:3].upper()

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
        return result

    def check_entry(self, entry):
        """Check validity of an entry.

        Check existence of corresponding database objects (ie. users, lessons,
        airports).
        Check correctness of data (no missing fields, etc.)"""
        try:
            correct = True
            reasons = list()

            # check if all required fields are present
            left = set(entry.keys()) - set(['teaching'])
            right = set(TXLATE_HEADERS.values()) - set(LIST_FIELDS)
            if not left == right:
                correct = False
                reasons.append('Missing fields: {0}'
                               .format(list(right - left)))

            # check if all required fields aren't empty
            for field in Person.REQUIRED_FIELDS:
                if not entry[field]:
                    correct = False
                    reasons.append('Required field "{0}" is empty'
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
                    reasons.append('There are multiple users with this name '
                                   '("{0} {1}")'
                                   .format(entry['personal'], entry['family']))
                except Person.DoesNotExist:
                    correct = False
                    reasons.append('User with either this email ("{0}") or '
                                   'this name ("{1} {2}") does not exist'
                                   .format(entry['email'], entry['personal'],
                                           entry['family']))

            # check if the person really is an instructor
            instructor_badge = Badge.objects.get(name='instructor')
            if person and instructor_badge not in person.badges.all():
                correct = False
                reasons.append('This person does not have an instructor badge')

            # cache airport IATA codes
            if 'airports' not in self._cache:
                self._cache['airports'] = Airport.objects.values_list(
                    'iata', flat=True,
                )

            # check if airport exists
            if entry['airport'] not in self._cache['airports']:
                correct = False
                reasons.append('Airport with this IATA code "{0}" does not '
                               'exist'.format(entry['airport']))

            # Don't check if domains exist.
            # There are occasions when instructors add domains we don't have in
            # the database.  This should be no-op.

            # cache lesson names
            if 'lessons' not in self._cache:
                self._cache['lessons'] = Lesson.objects.values_list('name',
                                                                    flat=True)

            # check if lessons exist
            for lesson in entry['teaching']:
                if lesson not in self._cache['lessons']:
                    correct = False
                    reasons.append('Lesson "{0}" does not exist'
                                   .format(lesson))

            return correct, reasons

        except KeyError as e:
            correct = False
            reasons.append("Missing fields: {}".format(e))
            return correct, reasons

    def update(self, entry):
        """Update instructor profile in the database."""
        try:
            person = Person.objects.get(email=entry['email'])
        except Person.DoesNotExist:
            person = Person.objects.get(personal=entry['personal'],
                                        family=entry['family'])

        # update personal details
        fields = ['personal', 'family', 'email', 'gender', 'github', 'twitter',
                  'url']
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
