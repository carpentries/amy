from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django_comments.models import Comment

from consents.models import Consent, TrainingRequestConsent
from workshops.utils.consents import (
    archive_least_recent_active_consents,
    archive_least_recent_active_training_request_consents,
)


def merge_objects(object_a, object_b, easy_fields, difficult_fields, choices, base_a=True):
    """Merge two objects of the same model.

    `object_a` and `object_b` are two objects being merged. If `base_a==True`
    (default value), then object_b will be removed and object_a will stay
    after the merge.  If `base_a!=True` then object_a will be removed, and
    object_b will stay after the merge.

    `easy_fields` contains names of non-M2M-relation fields, while
    `difficult_fields` contains names of M2M-relation fields.

    Finally, `choices` is a dictionary of field name as a key and one of
    3 values: 'obj_a', 'obj_b', or 'combine'.

    This view can throw ProtectedError when removing an object is not allowed;
    in that case, this function's call should be wrapped in try-except
    block."""
    if base_a:
        base_obj = object_a
        merging_obj = object_b
    else:
        base_obj = object_b
        merging_obj = object_a

    # used to catch all IntegrityErrors caused by violated database constraints
    # when adding two similar entries by the manager (see below for more
    # details)
    integrity_errors = []

    with transaction.atomic():
        for attr in easy_fields:
            value = choices.get(attr)
            if value == "obj_a":
                setattr(base_obj, attr, getattr(object_a, attr))
            elif value == "obj_b":
                setattr(base_obj, attr, getattr(object_b, attr))
            elif value == "combine":
                try:
                    new_value = getattr(object_a, attr) + getattr(object_b, attr)
                    setattr(base_obj, attr, new_value)
                except TypeError:
                    # probably 'unsupported operand type', but we
                    # can't do much about it…
                    pass

        for attr in difficult_fields:
            if attr == "comments":
                # special case handled below the for-loop
                continue

            related_a = getattr(object_a, attr)
            related_b = getattr(object_b, attr)

            manager = getattr(base_obj, attr)
            value = choices.get(attr)

            # switch only if this is opposite object
            if value == "obj_a" and manager != related_a:
                if hasattr(manager, "clear"):
                    # M2M and FK with `null=True` have `.clear()` method
                    # which unassigns instead of removing the related objects
                    manager.clear()
                else:
                    # in some cases FK are strictly related with the instance
                    # ie. they cannot be unassigned (`null=False`), so the
                    # only sensible solution is to remove them
                    manager.all().delete()
                manager.set(list(related_a.all()))

            elif value == "obj_b" and manager != related_b:
                if hasattr(manager, "clear"):
                    # M2M and FK with `null=True` have `.clear()` method
                    # which unassigns instead of removing the related objects
                    manager.clear()
                else:
                    # in some cases FK are strictly related with the instance
                    # ie. they cannot be unassigned (`null=False`), so the
                    # only sensible solution is to remove them
                    manager.all().delete()
                manager.set(list(related_b.all()))

            elif value == "obj_a" and manager == related_a:
                # since we're keeping current values, try to remove (or clear
                # if possible) opposite (obj_b) - they may not be removable
                # via on_delete=CASCADE, so try manually
                if hasattr(related_b, "clear"):
                    related_b.clear()
                else:
                    related_b.all().delete()

            elif value == "obj_b" and manager == related_b:
                # since we're keeping current values, try to remove (or clear
                # if possible) opposite (obj_a) - they may not be removable
                # via on_delete=CASCADE, so try manually
                if hasattr(related_a, "clear"):
                    related_a.clear()
                else:
                    related_a.all().delete()

            elif value == "combine":
                to_add = None

                if manager == related_a:
                    to_add = related_b.all()
                if manager == related_b:
                    to_add = related_a.all()

                # Some entries may cause IntegrityError (violation of
                # uniqueness constraint) because they are duplicates *after*
                # being added by the manager.
                # In this case they must be removed to not cause
                # on_delete=PROTECT violation after merging
                # (merging_obj.delete()).
                for element in to_add:
                    try:
                        with transaction.atomic():
                            manager.add(element)
                    except IntegrityError:
                        try:
                            element.delete()
                        except IntegrityError as e:
                            integrity_errors.append(str(e))

            elif attr == "consent_set" and value == "most_recent":
                # Special case: consents should be merge with a "most recent" strategy.
                archive_least_recent_active_consents(object_a, object_b, base_obj)

                # Reassign consents to the base object
                try:
                    Consent.objects.active().filter(person__in=[object_a, object_b]).update(person=base_obj)
                except IntegrityError as e:
                    integrity_errors.append(str(e))

            elif attr == "trainingrequestconsent_set" and value == "most_recent":
                # Special case: consents should be merge with a "most recent" strategy.
                archive_least_recent_active_training_request_consents(object_a, object_b, base_obj)

                # Reassign consents to the base object
                try:
                    TrainingRequestConsent.objects.active().filter(training_request__in=[object_a, object_b]).update(
                        training_request=base_obj
                    )
                except IntegrityError as e:
                    integrity_errors.append(str(e))

        if "comments" in choices:
            value = choices["comments"]
            # special case: comments made regarding these objects
            comments_a = Comment.objects.for_model(object_a)
            comments_b = Comment.objects.for_model(object_b)
            base_obj_ct = ContentType.objects.get_for_model(base_obj)

            if value == "obj_a":
                # we're keeping comments on obj_a, and removing (hiding)
                # comments on obj_b
                # WARNING: sequence of operations is important here!
                comments_b.update(is_removed=True)
                comments_a.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )

            elif value == "obj_b":
                # we're keeping comments on obj_b, and removing (hiding)
                # comments on obj_a
                # WARNING: sequence of operations is important here!
                comments_a.update(is_removed=True)
                comments_b.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )

            elif value == "combine":
                # we're making comments from either of the objects point to
                # the new base object
                comments_a.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )
                comments_b.update(
                    content_type=base_obj_ct,
                    object_pk=base_obj.pk,
                )

        merging_obj.delete()

        return base_obj.save(), integrity_errors
