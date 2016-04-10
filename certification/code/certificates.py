#!/usr/bin/env python

'''
Generate a certificate from a template.

* Requires the python package 'cairosvg' to be installed.
  Please visit http://cairosvg.org/ for install instructions.
* Some systems may also need to have 'cairo' installed.
  Please visit http://cairographics.org/download/ for the same.
'''

import sys
import os
import re
import tempfile
import cairosvg
from django.conf import settings

# --------------------------------------------------------------
# Main Functions


def generate(args):
    '''Process a single entry and returns their certificate'''
    root_dir = os.path.dirname(__file__)
    template_path = construct_template_path(root_dir, args['badge_type'])
    return create_certificate(template_path, args['params'], args['cert_id'])


def create_certificate(template_path, params, cert_id):
    """Create a PDF certificate from the given parameters."""
    with open(template_path, 'r') as reader:
        template = reader.read()
    check_template(template, params)

    for key, value in params.items():
        pattern = '{{' + key + '}}'
        template = template.replace(pattern, value)

    filename = os.path.join(settings.CERTIFICATES_DIR, str(cert_id) + '.pdf')
    cairosvg.svg2pdf(bytestring=template.encode('utf-8'),
                     dpi=90, write_to=filename)

# ---------------------------------------------------------------
# Helper Functions


def construct_template_path(root_dir, badge_type):
    '''Create path for template file.'''

    return os.path.join(root_dir, badge_type + '.svg')


def check_template(template, params):
    '''Check that all values required by template are present.'''

    expected = re.findall(r'\{\{([^}]*)\}\}', template)
    missing = set(expected) - set(params.keys())
    check(not missing,
          'Missing parameters required by template: {0}'
          .format(' '.join(missing)))


def check(condition, message):
    '''Fail if condition not met.'''

    if not condition:
        print(message, file=sys.stderr)
        sys.exit(1)

# ---------------------------------------------------------------
