import traceback
import os
import re
import xml.etree.ElementTree as ET
from django.test import TestCase
from ..models import Site


TEMPLATE_STRING_IF_INVALID = 'XXX-unset-variable-XXX' # FIXME: get by importing settings


class TestBase(TestCase):
    '''Base class for Amy test cases.'''

    def setUp(self):
        '''Create standard objects.'''

        self._setUpSites()

    def _setUpSites(self):
        '''Set up site objects.'''

        self.site_alpha = Site.objects.create(domain='alpha.edu',
                                              fullname='Alpha Site',
                                              country='Azerbaijan',
                                              notes='')

        self.site_beta = Site.objects.create(domain='beta.com',
                                             fullname='Beta Site',
                                             country='Brazil',
                                             notes='Notes\nabout\nBrazil\n')

    def _parse(self, content, save_to=None):
        """
        Parse the HTML page returned by the server.
        Must remove the DOCTYPE to avoid confusing Python's XML parser.
        Must also remove the namespacing, or use long-form names for elements.
        If save_to is a path, save a copy of the content to that file
        for debugging.
        """
        # Save the raw HTML if explicitly asked to (during debugging).
        if save_to:
            with open(save_to, 'w') as writer:
                w.write(content)

        # Report unfilled tags.
        if TEMPLATE_STRING_IF_INVALID in content:
            lines = content.split('\n')
            hits = [x for x in enumerate(lines)
                    if TEMPLATE_STRING_IF_INVALID in x[1]]
            msg = '"{0}" found in HTML page:\n'.format(TEMPLATE_STRING_IF_INVALID)
            assert not hits, msg + '\n'.join(['{0}: "{1}"'.format(h[0], h[1].rstrip())
                                              for h in hits])

        # Make the content safe to parse.
        content = re.sub('<!DOCTYPE [^>]*>', '', content)
        content = re.sub('<html[^>]*>', '<html>', content)
        content = content.replace('&nbsp;', ' ')

        # Parse if we can.
        try:
            doc = ET.XML(content)
            return doc
        # ...and save in a uniquely-named file if we can't.
        except ET.ParseError, e:
            stack = traceback.extract_stack()
            callers = [s[2] for s in stack] # get function/method names
            while callers and not callers[-1].startswith('test'):
                callers.pop()
            assert callers, 'Internal error: unable to find caller'
            caller = callers[-1]
            err_dir = 'htmlerror'
            if not os.path.isdir(err_dir):
                os.mkdir(err_dir)
            filename = os.path.join(err_dir, '{0}.html'.format(caller))
            with open(filename, 'w') as writer:
                writer.write(content)
            assert False, 'HTML parsing failed: {0}'.format(str(e))

    def _check_status_code_and_parse(self, response, expected):
        '''Check the status code, then parse if it is OK.'''
        assert response.status_code == expected, \
            'Got status code {0}, expected {1}'.format(response.status_code, expected)
        return self._parse(response.content)

    def _check_0(self, doc, xpath, msg):
        '''Check that there are no nodes of a particular type.'''
        nodes = doc.findall(xpath)
        assert len(nodes) == 0, (msg + ': got {0}'.format(len(nodes)))

    def _get_1(self, doc, xpath, msg):
        '''Get exactly one node from the document, checking that there _is_ exactly one.'''
        nodes = doc.findall(xpath)
        assert len(nodes) == 1, (msg + ': got {0}'.format(len(nodes)))
        return nodes[0]

    def _get_N(self, doc, xpath, msg, expected=None):
        '''Get all matching nodes from the document, checking the count if provided.'''
        nodes = doc.findall(xpath)
        if expected is not None:
            assert len(nodes) == expected, (msg + ': expected {0}, got {1}'.format(expected, len(nodes)))
        return nodes
