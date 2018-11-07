from django.apps import AppConfig
from django.db.models.signals import m2m_changed

from workshops.signals import trainingrequest_m2m_changed


class WorkshopsConfig(AppConfig):
    name = 'workshops'
    label = 'workshops'
    verbose_name = 'Workshops'

    def ready(self):
        # connect m2m_changed signal for TrainingRequest.domains to calculate
        # score_auto
        TrainingRequest = self.get_model('TrainingRequest')

        m2m_changed.connect(
            trainingrequest_m2m_changed,
            sender=TrainingRequest.domains.through,
        )

        m2m_changed.connect(
            trainingrequest_m2m_changed,
            sender=TrainingRequest.previous_involvement.through,
        )
