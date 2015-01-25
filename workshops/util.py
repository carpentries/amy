import csv
from math import pi, sin, cos, acos

PERSON_UPLOAD_FIELDS = ['personal', 'middle', 'family', 'email']
PERSON_TASK_UPLOAD_FIELDS = PERSON_UPLOAD_FIELDS + ['event', 'role']

def earth_distance(pos1, pos2):
    '''Taken from http://www.johndcook.com/python_longitude_latitude.html.'''

    # Extract fields.
    lat1, long1 = pos1
    lat2, long2 = pos2

    # Convert latitude and longitude to spherical coordinates in radians.
    degrees_to_radians = pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1) * degrees_to_radians
    phi2 = (90.0 - lat2) * degrees_to_radians
        
    # theta = longitude
    theta1 = long1 * degrees_to_radians
    theta2 = long2 * degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    c = sin(phi1) * sin(phi2) * cos(theta1 - theta2) + cos(phi1) * cos(phi2)
    arc = acos(c)

    # Multiply by 6373 to get distance in km.
    return arc * 6373


def upload_person_task_csv(uploaded_file):
    """
    Read data from CSV and turn it into JSON-serializable list of dictionaries.
    "Serializability" is required because we put this data into session.  See
    https://docs.djangoproject.com/en/1.7/topics/http/sessions/ for details.
    """
    persons_tasks = []
    reader = csv.DictReader(uploaded_file)
    for row in reader:
        person_fields = dict((col, row[col].strip())
                             for col in PERSON_UPLOAD_FIELDS)
        entry = {'person': person_fields, 'event': row.get('event', None),
                 'role': row.get('role', None), 'errors': None}
        persons_tasks.append(entry)
    return persons_tasks
