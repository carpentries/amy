#!/usr/bin/env python

'''
Mail people to check their activity based on YAML dump of Amy
database.  This is a stand-alone script rather than built into the
management command report_all_instructor_activity because it needs to
run on our server (so that the mail messages come from the right
machine).  The workflow is:

1. Get a local copy of the AMY database.

2. make all-activity > activity.yml.

3. Copy this script and activity.yml to the server.

4. python this-script < activity.yml to test.

5. python this-script --real < activity.yml to send email.
'''

import sys
import os
import yaml
import time


USAGE = 'Usage: mail-all-activity [-r|--real] [filename]'

SUBJECT = 'Updating your Software Carpentry information'

BODY = '''Hi,

The next election for the Software Carpentry Foundation Steering
Committee [1] is going to be held in February 2016 [2], and to
prepare, we'd like to make sure our records are up to date.  If your
location, email, or location are out of date in the information below,
please update them using:

  https://amy.software-carpentry.org/workshops/update_profile/

Please also check the information about workshops you've been involved
in -- if any details are missing or incorrect, please mail
admin@software-carpentry.org.  And if you have taught any self
organized workshops, we'd like to add them to your records as well, so
please send the date, location, instructors, number of attendees, and
workshop website to the same address.

If you would rather not receive mail from us in future, please mail
admin@software-carpentry.org and we will remove you from our contact
list.

Thanks for all you've done for Software Carpentry - you're the ones
who make what we do possible, and we look forward to continuing
working with you.

[1] http://software-carpentry.org/scf/

[2] http://software-carpentry.org/blog/2015/12/call-for-candidates-elections-2016.html

----------------------------------------

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
    first = True
    count = 0
    for record in info:
        address, subject, body = make_message(record)
        sender(first, address, subject, body)
        first = False
        count += 1
        print(count, address, file=sys.stderr)
        time.sleep(1)

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

    return '{0} at {1} with {2}'.format(
        task['role'],
        task['slug'],
        ', '.join(task['others']))


def display(first, address, subject, body):
    '''Display a message that is not being sent.'''

    if not first:
        print('-' * 40)
        print('')
    print('To:', address)
    print('Subject:', subject)
    print(body)
    print()


def send(first, address, subject, body):
    '''Send email.'''

    sender = 'admin@software-carpentry.org'
    command = 'mail -s "{0}" -r {1} {2}'.format(subject, sender, address)
    writer = os.popen(command, 'w')
    writer.write(body)
    writer.close()

def fail(msg):
    '''Halt and catch fire.'''

    print(msg, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main(sys.argv)
