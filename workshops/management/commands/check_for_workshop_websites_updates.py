from collections.abc import Iterable
import datetime
from functools import partial
import json
import socket
import sys

from django.core.management.base import BaseCommand
from github import Github
from github.GithubException import GithubException
import requests
from rest_framework.utils.encoders import JSONEncoder

from workshops.models import Event
from workshops.util import (
    fetch_event_metadata,
    parse_metadata_from_event_website,
    WrongWorkshopURL,
)


def datetime_match(string):
    """Convert string date/datetime/time to date/datetime/time."""
    formats = (
        # date
        ('%Y-%m-%d', 'date'),

        # datetime (no microseconds, timezone unaware)
        ('%Y-%m-%dT%H:%M:%S', None),

        # datetime (w/ microseconds, timezone unaware)
        ('%Y-%m-%dT%H:%M:%S.%f', None),

        # time (no microseconds, timezone unaware)
        ('%H:%M:%S', 'time'),

        # try parsing time (w/ microseconds, timezone unaware)
        ('%H:%M:%S.%f', 'time'),
    )
    for format_, method in formats:
        try:
            v = datetime.datetime.strptime(string, format_)
            if method is not None:
                return getattr(v, method)()
            return v
        except ValueError:
            pass

    # TODO: Implement timezone-aware datetime parsing (currently
    #       not available because datetime.datetime.strptime
    #       doesn't support "+HH:MM" format [only "+HHMM"]; nor
    #       does it support "Z" at the end)

    return string


def datetime_decode(obj):
    """Recursively call for each iterable, and try to decode each string."""
    iterator = None
    if isinstance(obj, dict):
        iterator = obj.items
    elif isinstance(obj, list):
        iterator = partial(enumerate, obj)

    if iterator:
        for k, item in iterator():
            if isinstance(item, str):
                obj[k] = datetime_match(item)

            elif isinstance(item, Iterable):
                # recursive call
                obj[k] = datetime_decode(item)

        return obj

    elif isinstance(obj, str):
        return datetime_match(obj)

    else:
        return obj


class Command(BaseCommand):
    help = 'Check if events have had their metadata updated.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-t', '--token', help='GitHub API token', required=True,
        )
        parser.add_argument(
            '-s', '--slug', help='Use only this specific event slug',
        )
        parser.add_argument(
            '--init', action='store_true', help='Run for the first time.',
        )
        parser.add_argument(
            '--cutoff-days', default=180, type=int,
            help='Age (in days) of the oldest events that can be checked.  '
                 'Default: 180'
        )

    def get_events(self, cutoff_days=180):
        """Get all active events.

        This method is used for getting all events that should be checked
        against up-to-date data."""
        events = Event.objects.active().filter(url__isnull=False)

        # events as old as 2014 are still marked as active, so we impose age
        # limit of half a year
        half_a_year = datetime.timedelta(days=cutoff_days)
        events = events.filter(start__gte=datetime.date.today() - half_a_year)
        return events

    def parse_github_url(self, url):
        """Parse GitHub's repository URL into repository owner and repository
        name."""
        regex = Event.REPO_REGEX
        mo = regex.match(url)
        if mo:
            groups = mo.groupdict()
            return groups['name'], groups['repo']
        raise WrongWorkshopURL()

    def get_event_metadata(self, event_url):
        """Get metadata from event (location, instructors, helpers, etc.)."""
        metadata = fetch_event_metadata(event_url)
        # normalize the metadata
        metadata = parse_metadata_from_event_website(metadata)
        return metadata

    def empty_metadata(self):
        """Prepare basic, empty metadata."""
        return parse_metadata_from_event_website({})

    def serialize(self, obj):
        """Serialize object to be put in the database."""
        return json.dumps(obj, cls=JSONEncoder)

    def deserialize(self, obj):
        """Deserialize object from the database."""
        objs = json.loads(obj)
        # convert strings to datetimes (if they match format)
        return datetime_decode(objs)

    def load_from_github(self, github, repo_url, default_branch='gh-pages'):
        """Fetch repository data from GitHub API."""
        owner, repo_name = self.parse_github_url(repo_url)
        repo = github.get_repo("{}/{}".format(owner, repo_name))
        branch = repo.get_branch('gh-pages')
        return branch

    def detect_changes(self, branch, event, save_metadata=False):
        """Detect changes made to event's metadata."""
        changes = []

        # compare commit hashes
        if branch.commit.sha != event.repository_last_commit_hash:
            # Hashes differ? Update commit hash and compare stored metadata
            event.repository_last_commit_hash = branch.commit.sha

            metadata_new = self.get_event_metadata(event.url)

            try:
                metadata_old = self.deserialize(event.repository_metadata)
            except json.decoder.JSONDecodeError:
                # this means that the value in DB is pretty much useless
                # so let's set it to the default value
                metadata_old = self.empty_metadata()

            metadata_to_check = (
                ('instructors', 'Instructors changed'),
                ('helpers', 'Helpers changed'),
                ('start', 'Start date changed'),
                ('end', 'End date changed'),
                ('country', 'Country changed'),
                ('venue', 'Venue changed'),
                ('address', 'Address changed'),
                ('latitude', 'Latitude changed'),
                ('longitude', 'Longitude changed'),
                ('contact', 'Contact details changed'),
                ('reg_key', 'Eventbrite key changed'),
            )

            changed = False
            # look for changed metadata
            for key, reason in metadata_to_check:
                if metadata_new[key] != metadata_old[key]:
                    changes.append(reason)
                    changed = True

            if changed:
                if save_metadata:
                    # we may not want to update the metadata
                    event.repository_metadata = self.serialize(metadata_new)

                event.metadata_all_changes = "\n".join(changes)
                event.metadata_changed = True

            event.save()

        return changes

    def init(self, branch, event):
        """Load initial data into event's repository and metadata information."""
        event.repository_last_commit_hash = branch.commit.sha
        metadata = self.get_event_metadata(event.url)
        event.repository_metadata = self.serialize(metadata)
        event.metadata_all_changes = ''
        event.metadata_changed = False
        event.save()

    def handle(self, *args, **options):
        """Run."""
        token = options['token']
        initial_run = options['init']
        slug = options['slug']
        cutoff_days = options['cutoff_days']

        g = Github(token)

        # get all events
        events = self.get_events(cutoff_days)

        if slug:
            events = events.filter(slug=slug)

        # dict of events with changes that will be updated in
        # the separate loop
        events_for_update = dict()

        # go through all events
        for event in events:
            try:
                if initial_run:
                    branch = self.load_from_github(g, event.repository_url)
                    self.init(branch, event)
                    print('Initialized {}'.format(event.slug))
                else:
                    branch = self.load_from_github(g, event.repository_url)
                    changes = self.detect_changes(branch, event)
                    if changes:
                        events_for_update[event.slug] = changes
                        print('Detected changes in {}'.format(event.slug))

            except GithubException:
                print('GitHub error when accessing {} repo'.format(event.slug),
                      file=sys.stderr)

            except socket.timeout:
                print('Timeout when accessing {} repo'.format(event.slug),
                      file=sys.stderr)

            except WrongWorkshopURL:
                print('Wrong URL for {}'.format(event.slug), file=sys.stderr)

            except requests.exceptions.RequestException:
                print('Network error when accessing {}'.format(event.slug),
                      file=sys.stderr)

            except Exception as e:
                print('Unknown error ({}): {}'.format(event.slug, e),
                      file=sys.stderr)
