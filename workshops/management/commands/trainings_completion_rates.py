import csv

from django.core.management.base import BaseCommand

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
        fields = [
            'start', 'slug', 'online', 'badge', 'learners',
            'completed this', 'completed this [%]',
            'completed other', 'completed other [%]',
            'no badge', 'no badge [%]',
        ]
        writer = csv.DictWriter(self.stdout, fieldnames=fields)
        writer.writeheader()

        for training in self.trainings():
            badge = self.badge_type(training.tags.all())
            learners = self.learners(training)
            learners_len = learners.count()
            completed_len = learners.filter(badges=badge,
                                            award__event=training).count()
            completed_other_len = learners.filter(badges=badge) \
                                          .exclude(award__event=training) \
                                          .count()
            no_badge_len = learners.exclude(badges=badge).count()

            record = {
                fields[0]: universal_date_format(training.start),
                fields[1]: training.slug,
                fields[2]: int(self.online_tag in training.tags.all()),
                fields[3]: badge.title,
                fields[4]: learners_len,
                fields[5]: completed_len,
                fields[6]: self.percent(completed_len, learners_len),
                fields[7]: completed_other_len,
                fields[8]: self.percent(completed_other_len, learners_len),
                fields[9]: no_badge_len,
                fields[10]: self.percent(no_badge_len, learners_len),
            }
            writer.writerow(record)
