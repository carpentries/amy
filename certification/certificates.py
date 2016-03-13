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

#---------------------------------------------------------------
# Main Functions

def process_single(args):
    '''Process a single entry and returns their certificate'''
    root_dir = os.path.dirname(__file__)
    template_path = construct_template_path(root_dir, args.badge_type)
    return create_certificate(template_path, args.params)


def create_certificate(template_path, params):
    '''Creates and returns a single certificate.'''

    with open(template_path, 'r') as reader:
        template = reader.read()
    check_template(template, params)

    for key, value in params.items():
        pattern = '{{' + key + '}}'
        template = template.replace(pattern, value)

    tmp = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
    tmp.write(bytes(template, 'utf-8'))

    return cairosvg.svg2pdf(url=tmp.name, dpi=90)

#---------------------------------------------------------------
# Helper Functions

def construct_template_path(root_dir, badge_type):
    '''Create path for template file.'''

    return os.path.join(root_dir, badge_type + '.svg')

def check_template(template, params):
    '''Check that all values required by template are present.'''

    expected = re.findall(r'\{\{([^}]*)\}\}', template)
    missing = set(expected) - set(params.keys())
    check(not missing,
          'Missing parameters required by template: {0}'.format(' '.join(missing)))

def check(condition, message):
    '''Fail if condition not met.'''

    if not condition:
        print(message, file=sys.stderr)
        sys.exit(1)

#---------------------------------------------------------------
