from django.apps import AppConfig
from django.db.models.signals import m2m_changed


def trainingrequest_m2m_changed(sender, **kwargs):
    """Signal receiver for TrainingRequest m2m_changed signal.

    The purpose of this receiver is to react on `TrainingRequest.domains` and
    `TrainingRequest.previous_involvement` change and recalculate request's
    automatic score, which depends on these M2M fields.

    Originally calculation takes place in model's `save` method, but
    it was being called before M2M fields changed."""

    # react only on "post_add"/"post_remove", forward (not reverse) action
    action = kwargs.get("action", "")
    forward = not kwargs.get("reverse", True)
    instance = kwargs.get("instance", None)
    using = kwargs.get("using")

    # There's a catch - we can alter the relation from a different side, ie.
    # from KnowledgeDomain.trainingrequest_set, but it's harder to recalculate
    # because we'd have to make N recalculations. Therefore we only allow
    # `forward` direction.
    if instance and forward and action in ["post_add", "post_remove"]:
        # recalculation happens in `save()` method
        instance.save(using=using)


class WorkshopsConfig(AppConfig):
    name = "workshops"
    label = "workshops"
    verbose_name = "Workshops"

    def ready(self):
        # connect m2m_changed signal for TrainingRequest.domains to calculate
        # score_auto
        TrainingRequest = self.get_model("TrainingRequest")

        m2m_changed.connect(
            trainingrequest_m2m_changed,
            sender=TrainingRequest.domains.through,
        )

        m2m_changed.connect(
            trainingrequest_m2m_changed,
            sender=TrainingRequest.previous_involvement.through,
        )
        from workshops import receivers  # noqa
