import datetime
import json

from django.core.management.base import BaseCommand
from github import Github
import requests
from rest_framework.utils.encoders import JSONEncoder

from workshops.models import Event
from workshops.util import (
    fetch_event_tags,
    parse_tags_from_event_website,
    WrongWorkshopURL,
)


class JSONDecoder(json.JSONDecoder):
    def decode(self, obj):
        try:
            # try parsing date
            v = datetime.datetime.strptime(obj, '%Y-%m-%d')
            v = v.date()
        except ValueError:
            pass

        try:
            # try parsing datetime (no microseconds, timezone unaware)
            v = datetime.datetime.strptime(obj, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            pass

        try:
            # try parsing datetime (w/ microseconds, timezone unaware)
            v = datetime.datetime.strptime(obj, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            pass

        # TODO: Implement timezone-aware datetime parsing (currently not
        #       available because datetime.datetime.strptime doesn't support
        #       "+HH:MM" format [only "+HHMM"]; nor does it support "Z" at the
        #       end)

        try:
            # try parsing time (no microseconds, timezone unaware)
            v = datetime.datetime.strptime(obj, '%H:%M:%S')
            v = v.time()
        except ValueError:
            pass

        try:
            # try parsing time (w/ microseconds, timezone unaware)
            v = datetime.datetime.strptime(obj, '%H:%M:%S.%f')
            v = v.time()
        except ValueError:
            pass


class Command(BaseCommand):
    help = ''

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

    def get_events(self):
        """Get all active events.

        This method is used for getting all events that should be checked
        against up-to-date data."""
        events = Event.objects.active().filter(url__isnull=False)
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

    def get_event_tags(self, event_url):
        """Get metadata from event (location, instructors, helpers, etc.)."""
        tags = fetch_event_tags(event_url)
        # normalize the tags
        tags = parse_tags_from_event_website(tags)
        return tags

    def serialize(self, obj):
        """Serialize object to be put in the database."""
        return json.dumps(obj, cls=JSONEncoder)

    def deserialize(self, obj):
        """Deserialize object from the database."""
        return json.loads(obj, cls=JSONDecoder)

    def load_from_github(self, github, repo_url, default_branch='gh-pages'):
        """Fetch repository data from GitHub API."""
        owner, repo_name = self.parse_github_url(repo_url)
        repo = github.get_repo("{}/{}".format(owner, repo_name))
        branch = repo.get_branch('gh-pages')
        return branch

    def detect_changes(self, github, event, save_tags=False):
        """Detect changes made to event's meta tags."""
        changes = []

        # load from API
        branch = self.load_from_github(github, event.repository_url)

        # compare commit hashes
        if branch.commit.sha != event.repository_last_commit_hash:
            # Hashes differ? Update commit hash and compare stored tags
            event.repository_last_commit_hash = branch.commit.sha

            tags_new = self.get_event_tags(event.url)

            tags_old = self.deserialize(event.repository_tags)

            tags_to_check = (
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
            )

            changed = False
            # look for changed tags
            for tag, reason in tags_to_check:
                if tags_new[tag] != tags_old[tag]:
                    changes.append(reason)
                    changed = True

            if save_tags:
                event.repository_tags = self.serialize(tags_new)
            if changed:
                event.tag_changes_detected = "\n".join(changes)
                event.tags_changed = True
            event.save()

        return changes

    def init(self, github, event):
        """Load initial data into event's repository and tag information."""
        # load from API
        branch = self.load_from_github(github, event.repository_url)

        event.repository_last_commit_hash = branch.commit.sha
        tags = self.get_event_tags(event.url)
        event.repository_tags = self.serialize(tags)
        event.tag_changes_detected = ''
        event.tags_changed = False
        event.save()

    def handle(self, *args, **options):
        """Run."""
        token = options['token']
        initial_run = options['init']
        slug = options['slug']

        g = Github(token)

        # get all events
        events = self.get_events()

        if slug:
            events = events.filter(slug=slug)

        # dict of events with changes that will be updated in
        # the separate loop
        events_for_update = dict()

        # go through all events
        for event in events:
            try:
                if initial_run:
                    self.init(g, event)
                    print('Initialized {}'.format(event.slug))
                else:
                    changes = self.detect_changes(g, event)
                    if changes:
                        events_for_update[event.slug] = changes
                        print('Detected changes in {}'.format(event.slug))

            except WrongWorkshopURL:
                print('Wrong URL for {}'.format(event.slug))

            except requests.exceptions.RequestException:
                print('Network error when accessing {}'.format(event.slug))
