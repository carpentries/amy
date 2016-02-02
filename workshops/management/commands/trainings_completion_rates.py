import csv

from django.core.management.base import BaseCommand
from django.template.loader import get_template

from workshops.models import Badge, Event, Tag, Person, Role
from workshops.util import universal_date_format


class Command(BaseCommand):
    help = 'Report completion rates for new training participants.'

    learner = Role.objects.get(name='learner')
    dc_badge = Badge.objects.get(name='dc-instructor')
    swc_badge = Badge.objects.get(name='swc-instructor')
    dc_tag = Tag.objects.get(name='DC')
    swc_tag = Tag.objects.get(name='SWC')
    online_tag = Tag.objects.get(name='online')

    def trainings(self):
        """Create list of trainings."""
        return Event.objects.filter(tags=Tag.objects.get(name='TTT')) \
                            .prefetch_related('tags', 'task_set') \
                            .order_by('start')

    def badge_type(self, tags):
        """Return badge of the same type as event tags.

        If no SWC or DC tag is present, SWC badge is assumed."""
        if self.swc_tag in tags:
            return self.swc_badge
        elif self.dc_tag in tags:
            return self.dc_badge
        else:
            return self.swc_badge

    def learners(self, event):
        """Return list of learners at specific training event."""
        return Person.objects.filter(task__event=event,
                                     task__role=self.learner)

    def percent(self, numerator, denominator):
        """Return percentage if non-zero denominator else 0.0"""
        if denominator:
            return round((100. * numerator) / denominator, 1)
        return 0.0

    def handle(self, *args, **options):
        records = [['start', 'slug', 'online', 'badge', 'learners',
                    'completed this', 'completed this %age',
                    'completed other', 'completed other %age',
                    'no badge', 'no badge %']]
        for training in self.trainings():
            badge = self.badge_type(training.tags.all())
            learners = self.learners(training)
            learners_len = learners.count()
            completed_len = \
                learners.filter(badges=badge, award__event=training).count()
            completed_other_len = \
                learners.filter(badges=badge).exclude(award__event=training).count()
            no_badge_len = \
                learners.exclude(badges=badge).count()
            records.append([universal_date_format(training.start),
                            training.slug,
                            int(self.online_tag in training.tags.all()),
                            badge.title,
                            learners_len,
                            completed_len,
                            self.percent(completed_len, learners_len),
                            completed_other_len,
                            self.percent(completed_other_len, learners_len),
                            no_badge_len,
                            self.percent(no_badge_len, learners_len)])
        csv.writer(self.stdout).writerows(records)
