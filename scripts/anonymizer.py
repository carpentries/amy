import sys
from datetime import date, timedelta
import random
import shutil
import sqlite3

#------------------------------------------------------------

ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

LOREM_IPSUM = [
'''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec a
diam lectus. Sed sit amet ipsum mauris. Maecenas congue ligula ac quam
viverra nec consectetur ante hendrerit. Donec et mollis
dolor. Praesent et diam eget libero egestas mattis sit amet vitae
augue. Nam tincidunt congue enim, ut porta lorem lacinia
consectetur. Donec ut libero sed arcu vehicula ultricies a non
tortor. Lorem ipsum dolor sit amet, consectetur adipiscing
elit. Aenean ut gravida lorem. Ut turpis felis, pulvinar a semper sed,
adipiscing id dolor. Pellentesque auctor nisi id magna consequat
sagittis. Curabitur dapibus enim sit amet elit pharetra tincidunt
feugiat nisl imperdiet. Ut convallis libero in urna ultrices
accumsan. Donec sed odio eros. Donec viverra mi quis quam pulvinar at
malesuada arcu rhoncus. Cum sociis natoque penatibus et magnis dis
parturient montes, nascetur ridiculus mus. In rutrum accumsan
ultricies. Mauris vitae nisi at sem facilisis semper ac in est.'''
,
'''Vivamus fermentum semper porta. Nunc diam velit, adipiscing ut
tristique vitae, sagittis vel odio. Maecenas convallis ullamcorper
ultricies. Curabitur ornare, ligula semper consectetur sagittis, nisi
diam iaculis velit, id fringilla sem nunc vel mi. Nam dictum, odio nec
pretium volutpat, arcu ante placerat erat, non tristique elit urna et
turpis. Quisque mi metus, ornare sit amet fermentum et, tincidunt et
orci. Fusce eget orci a orci congue vestibulum. Ut dolor diam,
elementum et vestibulum eu, porttitor vel elit. Curabitur venenatis
pulvinar tellus gravida ornare. Sed et erat faucibus nunc euismod
ultricies ut id justo. Nullam cursus suscipit nisi, et ultrices justo
sodales nec. Fusce venenatis facilisis lectus ac semper. Aliquam at
massa ipsum. Quisque bibendum purus convallis nulla ultrices
ultricies. Nullam aliquam, mi eu aliquam tincidunt, purus velit
laoreet tortor, viverra pretium nisi quam vitae mi. Fusce vel volutpat
elit. Nam sagittis nisi dui.'''
,
'''Suspendisse lectus leo, consectetur in tempor sit amet, placerat quis
neque. Etiam luctus porttitor lorem, sed suscipit est rutrum
non. Curabitur lobortis nisl a enim congue semper. Aenean commodo
ultrices imperdiet. Vestibulum ut justo vel sapien venenatis
tincidunt. Phasellus eget dolor sit amet ipsum dapibus condimentum
vitae quis lectus. Aliquam ut massa in turpis dapibus
convallis. Praesent elit lacus, vestibulum at malesuada et, ornare et
est. Ut augue nunc, sodales ut euismod non, adipiscing vitae
orci. Mauris ut placerat justo. Mauris in ultricies enim. Quisque nec
est eleifend nulla ultrices egestas quis ut quam. Donec sollicitudin
lectus a mauris pulvinar id aliquam urna cursus. Cras quis ligula sem,
vel elementum mi. Phasellus non ullamcorper urna.'''
,
'''Class aptent taciti sociosqu ad litora torquent per conubia nostra,
per inceptos himenaeos. In euismod ultrices facilisis. Vestibulum
porta sapien adipiscing augue congue id pretium lectus molestie. Proin
quis dictum nisl. Morbi id quam sapien, sed vestibulum sem. Duis
elementum rutrum mauris sed convallis. Proin vestibulum magna
mi. Aenean tristique hendrerit magna, ac facilisis nulla hendrerit
ut. Sed non tortor sodales quam auctor elementum. Donec hendrerit nunc
eget elit pharetra pulvinar. Suspendisse id tempus tortor. Aenean
luctus, elit commodo laoreet commodo, justo nisi consequat massa, sed
vulputate quam urna quis eros. Donec vel.''']

#------------------------------------------------------------

def get_one(cursor, statement, *params):
    cursor.execute(statement, params)
    results = cursor.fetchall()
    if len(results) == 0:
        return None
    return results[0][0]

RANDWORD_SEEN = set()

def randword(low, high):
    while True:
        r = ''.join([random.choice(ALPHA) for i in range(random.randrange(low, high))])
        if r not in RANDWORD_SEEN:
            RANDWORD_SEEN.add(r)
            return r

def change(cursor, table, field, func, *args):
    lower = get_one(cursor, 'select min(id) from {0};'.format(table))
    upper = get_one(cursor, 'select max(id) from {0};'.format(table))
    assert (lower is not None) and (upper is not None), \
           'No lower/upper bounds for {0}.{1}'.format(table, field)

    if isinstance(field, str):
        stmt = 'update {0} set {1}=? where id=?;'.format(table, field)
    elif isinstance(field, tuple):
        filler = ', '.join(['{0}=?'.format(f) for f in field])
        stmt = 'update {0} set {1} where id=?;'.format(table, filler)
    else:
        assert False, 'Unknown field type "{0}" for "{1}"'.format(type(field), field)

    for i in range(lower, upper+1):
        vals = func(cursor, i, *args) + (i, )
        try:
            cursor.execute(stmt, vals)
        except sqlite3.OperationalError as e:
            print('FAILED (operational error):', stmt, vals, e)
        except sqlite3.IntegrityError as e:
            print('FAILED (integrity error):', stmt, vals, e)

def tuplify(func):
    def f(*args, **kwargs):
        result = func(*args, **kwargs)
        return (result,)
    return f

#------------------------------------------------------------

def dates(cursor, i):
    '''Generate start and end dates for workshop.'''
    start = date(2012, 1, 1) + timedelta(random.randrange(4 * 365))
    end = start + timedelta(random.randrange(4))
    if end == start:
        end = None
    return (start, end)

@tuplify
def event_reg_key(cursor, i):
    '''Generate random event registration key.'''
    return str(1000000 + i)

@tuplify
def event_slug(cursor, i):
    '''Generate event slugs once start/end dates and site names are set.'''
    start = get_one(cursor, 'select start from workshops_event where id=?;', i)
    if start is None:
        return
    year, month, day = start.split('-')
    return '{0}-{1}-{2}-{3}'.format(year, month, day, randword(3, 8))

@tuplify
def url(cursor, i):
    '''Generate something that looks like a URL.'''
    return 'http://{0}.{1}/{2}-{3}'.format(*[randword(2, 10) for x in range(4)])

@tuplify
def lorem_ipsum(cursor, i):
    '''Fill in a large text field.'''
    result = '\n'.join(LOREM_IPSUM[0:random.randrange(len(LOREM_IPSUM))])
    return result

@tuplify
def monicker(cursor, i):
    '''Generate a username-style field.'''
    return randword(2, 10)

@tuplify
def multi_word(cursor, i, prob_multi, prob_null=0.0):
    '''Fill in a multi-word field (e.g., site name or person's name).'''
    if random.uniform(0.0, 1.0) < prob_null:
        return None
    elif random.uniform(0.0, 1.0) < prob_multi:
        return '{0} {1}'.format(randword(2, 10), randword(2, 12))
    else:
        return randword(2, 10)

@tuplify
def domain(cursor, i):
    '''Fill in site.domain.'''
    fields = []
    for x in range(2, random.randrange(4, 5)):
        fields.append(randword(2, 10))
    return '.'.join(fields)

@tuplify
def gender(cursor, i):
    return random.choice('FMO')

@tuplify
def email(cursor, i):
    if random.uniform(0.0, 1.0) < 0.05:
        return None
    return '{0}@{1}.{2}'.format(*[randword(2, 8) for x in range(3)])

#------------------------------------------------------------

def main():
    assert len(sys.argv) == 4, 'Usage: {0} seed /path/to/source/db /path/to/destination/db'.format(sys.argv[0])
    assert sys.argv[2] != sys.argv[3], 'Source and destination must be different database'

    seed = int(sys.argv[1])
    if seed == 0:
        seed = None
    db_src = sys.argv[2]
    db_dst = sys.argv[3]

    random.seed(seed)
    shutil.copyfile(db_src, db_dst)
    cnx = sqlite3.connect(db_dst)
    cur = cnx.cursor()

    change(cur, 'workshops_site', 'domain', domain)
    change(cur, 'workshops_site', 'fullname', multi_word, 1.0)
    change(cur, 'workshops_site', 'notes', lorem_ipsum)

    change(cur, 'workshops_person', 'personal', multi_word, 0.1)
    change(cur, 'workshops_person', 'middle', multi_word, 0.0, 0.9)
    change(cur, 'workshops_person', 'family', multi_word, 0.1)
    change(cur, 'workshops_person', 'gender', gender)
    change(cur, 'workshops_person', 'email', email)
    change(cur, 'workshops_person', 'github', monicker)
    change(cur, 'workshops_person', 'twitter', monicker)
    change(cur, 'workshops_person', 'url', url)
    change(cur, 'workshops_person', 'username', monicker)

    change(cur, 'workshops_event', ('start', 'end'), dates)
    change(cur, 'workshops_event', 'slug', event_slug)
    change(cur, 'workshops_event', 'url', url)
    change(cur, 'workshops_event', 'reg_key', event_reg_key)
    change(cur, 'workshops_event', 'notes', lorem_ipsum)

    cnx.commit()
    cur.close()
    cnx.close()

if __name__ == '__main__':
    main()
