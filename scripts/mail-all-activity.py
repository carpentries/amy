#!/usr/bin/env python

'''Mail people to check their activity based on YAML dump of Amy database.'''

import sys
import os
import yaml


USAGE = 'Usage: mail-all-activity [-r|--real] [filename]'

SUBJECT = 'Updating your Software Carpentry information'

BODY = '''We are changing the way we track the lessons that people are
comfortable teaching, and would also like to update our list of where
people are and what they've taught.  We would therefore be grateful if
you could take ninety seconds to fill in:

  https://docs.google.com/forms/d/1NA2z3mXnrz4ZfEV02rk6vwdK4M180_sYpVjUQBt-yMc/viewform

If you would rather not receive mail from us in future, please reply
to this message and we'll remove you from our contact list.

name: {name}
preferred email: {email}
became instructor: {became_instructor}
{optional}
{can_teach}
{tasks}'''


def main(argv):
    '''Main driver.'''

    # Setup.
    sender = display
    prog_name, args = argv[0], argv[1:]

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

    record['optional'] = '\n'.join(
        [format_optional(record, key) for key in ('airport', 'twitter', 'github')])

    record['can_teach'] = format_can_teach(record['can_teach'])

    record['tasks'] = '\n'.join(
        [format_task(t) for t in record['tasks']])

    body = BODY.format(**record)
    return address, SUBJECT, body


def format_optional(record, key):
    '''Format an optional entry for inclusion in the message body.'''

    if record.get(key, None):
        return 'Your {0} is "{1}"'.format(key, record[key])
    else:
        return 'Your {0} is unknown'.format(key)


def format_can_teach(can_teach):
    '''Format zero or more skills for inclusion in the message body.'''

    if can_teach:
        return 'You can teach: {0}'.format(', '.join(can_teach))
    return ''


def format_task(task):
    '''Format tasks and collaborators for inclusion in the message body.'''

    return 'You were a {0} at {1} with {2}'.format(
        task['role'],
        task['slug'],
        ', '.join(task['others']))


def display(address, subject, body):
    '''Display a message that is not being sent.'''

    print('To:', address)
    print('Subject:', subject)
    print(body)
    print()


def send(address, subject, body):
    '''Send email.'''

    sender = 'admin@software-carpentry.org'
    command = 'mail -s "{0}" -r {1} {2}'.format(subject, sender, address)
    writer = os.popen(command, 'w')
    writer.write(body)
    writer.close()
    print(address, file=sys.stderr)

def fail(msg):
    '''Halt and catch fire.'''

    print(msg, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main(sys.argv)
