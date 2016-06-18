from workshops.models import Tag


def parse_event(conf):
    return {
        'slug': conf['title'],
        'start': conf['start_date'],
        'end': conf['end_date'],
        'tags': Tag.objects.get(name='PyData').pk,
    }
