from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def select_one(name, combine=False, id_=None):
    """Generate a select input with only two options: A or B."""
    id_ = id_ or ""
    input_ = ('<br><label class="onethird"><input type="radio" name="{name}" id="{id}" '
              'value="obj_a" checked="checked" />Use A</label>'
              '<label class="onethird"><input type="radio" name="{name}" id="{id}" '
              'value="obj_b" />Use B</label>'.format(id=id_, name=name))

    if combine:
        input_ += ('<label class="onethird"><input type="radio" name="{name}" id="{id}" '
                   'value="combine" />Combine</label>'
                   .format(id=id_, name=name))

    return mark_safe(input_)


@register.simple_tag
def select_one_or_combine(name, id_=None):
    """Generate a select input with three options: A or B, or combined
    (A+B)."""
    return select_one(name, combine=True, id_=id_)
