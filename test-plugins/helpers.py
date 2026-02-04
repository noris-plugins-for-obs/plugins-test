'''
Helper functions
'''

import unittest
import os

def flatten_widgets(widget):
    'Iterate self and all widgets'
    yield widget
    for w in widget['children']:
        yield from flatten_widgets(w)

SEVERITY_COVERAGE = 10
SEVERITY_FULL = 20
_SEVERITIES_TO_NAME = {
        SEVERITY_COVERAGE: 'COVERAGE',
        SEVERITY_FULL: 'FULL',
}

def _get_severity():
    if not 'SEVERITY' in os.environ:
        return 0
    s = os.environ['SEVERITY']
    if not s:
        return 0
    for k, v in _SEVERITIES_TO_NAME.items():
        if s.upper() == v:
            return k
    raise ValueError(f'Unknown SEVERITY "{s}"')

def severity(level):
    '''
    A decorator to skip test based on severity setting

    :param level:  Level of severity
    '''
    if level > _get_severity():
        return unittest.skip(f'requires severity {_SEVERITIES_TO_NAME[level]}')
    return lambda f: f
