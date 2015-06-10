#!/usr/bin/env python

'''Mail people to check their activity based on YAML dump of Amy database.'''

import sys
import yaml


USAGE = 'Usage: mail-all-activity [-r|--real] [filename]'

SUBJECT = 'Checking your Software Carpentry information'

BODY = '''We would like to bring our records up to date, and would be grateful
if you could check the information below and send us corrections or additions
by filling in the form at:

    https://docs.google.com/forms/d/1NA2z3mXnrz4ZfEV02rk6vwdK4M180_sYpVjUQBt-yMc/viewform

If the topics you're comfortable teaching aren't listed, or are incorrect,
please also fill in the form.  And if you would rather not receive mail from
us in future, please reply to this message and we'll remove you from our
list.

name: {name}
preferred email: {email}
became instructor: {became_instructor}
{optional}
{can_teach}
{tasks}'''


def main(argv):
    '''Main driver.'''

    # Setup.
    prog_name, args = argv[0], argv[1:]
    sender = display

    # Default is dummy run - only actually send mail if told to.
    if args and (args[0] in ('-r', '--real')):
        sender = send
        args = args[1:]

    # If no filename provided, use stdin.
    if len(args) == 0:
        process(sender, sys.stdin)
    elif len(args) == 1:
        with open(args[0], 'r') as reader:
            process(sender, reader)
    else:
        fail(USAGE)


def process(sender, reader):
    '''Process the YAML data loaded through reader.'''
    info = yaml.load(reader)
    for record in info:
        address, subject, body = make_message(record)
        sender(address, subject, body)


def make_message(record):
    '''Construct address, subject, and body of message.'''

    assert 'optional' not in record, \
           'Keyword "optional" should not be a key in records'

    address = record['email']

    record['optional'] = ''
    for key in ('airport', 'twitter', 'github'):
        record['optional'] += format_optional(record, key)

    record['can_teach'] = format_can_teach(record['can_teach'])

    record['tasks'] = format_tasks(record['tasks'])

    body = BODY.format(**record)
    return address, SUBJECT, body


def format_optional(record, key):
    '''Format an optional entry for inclusion in the message body.'''

    if record.get(key, None):
        return 'Your {0} is "{1}"\n'.format(key, record[key])
    else:
        return 'Your {0} is unknown\n'.format(key)


def format_can_teach(can_teach):
    '''Format zero or more skills for inclusion in the message body.'''

    if can_teach:
        return 'You can teach: {0}\n'.format(', '.join(can_teach))
    else:
        return ''


def format_tasks(tasks):
    '''Format tasks and collaborators for inclusion in the message body.'''

    result = ''
    for t in tasks:
        entry = 'You were a {0} at {1} with {2}\n'.format(
            t['role'],
            t['slug'],
            ', '.join(t['others']))
        result += entry
    return result


def display(address, subject, body):
    '''Display a message that is not being sent.'''
    print('To:', address)
    print('Subject:', subject)
    print(body)


def send(address, subject, body):
    '''Send email.'''
    fail('Not yet able to send')


def fail(msg):
    '''Halt and catch fire.'''
    print(msg, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main(sys.argv)
