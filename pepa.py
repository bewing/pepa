__author__ = 'Michael Persson <michael.ake.persson@gmail.com>'
__copyright__ = 'Copyright (c) 2013 Michael Persson'
__license__ = 'GPLv3'
__version__ = '0.5.5'

# Import python libs
from salt.exceptions import SaltInvocationError
import logging

# Set up logging
log = logging.getLogger(__name__)

# Name
__virtualname__ = 'pepa'

# Options
__opts__ = {
    'pepa_roots': {
        'base': '/srv/salt'
    },
    'pepa_delimiter': '..'
}

# Import third party libs
try:
    import json
    HAS_JSON = True
except ImportError:
    HAS_JSON = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from os.path import isfile, join as makepath
    HAS_OS_PATH = True
except ImportError:
    HAS_OS_PATH = False

try:
    import re
    HAS_RE = True
except ImportError:
    HAS_RE = False

try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

def __virtual__():
    if not HAS_YAML:
        log.error("Pepa ext_pillar failed to load YAML library")
        return False

    if not HAS_JSON:
        log.error("Pepa ext_pillar failed to load JSON library")
        return False

    if not HAS_OS_PATH:
        log.error("Pepa ext_pillar failed to load OS Path library")
        return False

    if not HAS_RE:
        log.error("Pepa ext_pillar failed to load RE library")
        return False

    if not HAS_JINJA2:
        log.error("Pepa ext_pillar failed to load Jinja2 library")
        return False

    log.debug("Loading Pepa ext_pillar")
    return(__virtualname__)

# Convert key/value to nested dictionary
# Plundered with impunity from salt-pillar-dynamo (https://github.com/jasondenning/salt-pillar-dynamo)
def key_value_to_tree(data):
    tree = {}
    for flatkey, value in data.items():
        t = tree
        keys = flatkey.split(__opts__['pepa_delimiter'])
        for key in keys:
            if key == keys[-1]:
                t[key] = value
            else:
                t = t.setdefault(key, {})
    return(tree)

def ext_pillar(minion_id, pillar, resource, sequence):
    roots = __opts__['pepa_roots']

    # Validate roots

    # Validate sequence
    if not sequence:
        raise SaltInvocationError('ext_pillar.pepa: sequence is not defined')
    if type(sequence) is not list:
        raise SaltInvocationError('ext_pillar.pepa: sequence needs to be a list')

    input = {}
    input['default'] = 'default'

    # Load input
    fn = makepath(roots['base'], resource, 'inputs', minion_id)
    if isfile(fn + '.yaml'):
        log.debug("Pepa ext_pillar load host input: %s.json" % fn)
        input.update(yaml.load(open(fn + '.yaml').read()))
        input['pepa_input'] = minion_id + '.yaml'
    elif isfile(fn + '.json'):
        log.debug("Pepa ext_pillar load host input: %s.json" % fn)
        input.update(json.loads(open(fn + '.json').read()))
        input['pepa_input'] = minion_id + '.json'
    else:
        log.error("Pepa ext_pillar host input doesn't exist: %s.(json|yaml)" % fn)
        input['pepa_input'] = 'None'

    # Load templates
    output = input
    output['pepa_templates'] = []
    for category in sequence:
        if category not in input:
            continue

        entries = []
        if type(input[category]) is list:
            entries = input[category]
        else:
            entries = [ input[category] ]

        for entry in entries:
            results = None
            fn = makepath(roots[input['environment']], resource, 'templates', category, re.sub('\W', '_', entry.lower()))
            if isfile(fn + '.yaml'):
                log.debug("Pepa ext_pillar load template: %s.yaml" % fn)
                template = jinja2.Template(open(fn + '.yaml').read())
                output['pepa_templates'].append('%s: %s' % (category,  re.sub('\W', '_', entry.lower()) + '.yaml'))
                data = key_value_to_tree(output)
                data['grains'] = __grains__.copy()
                data['pillar'] = pillar.copy()
                results = yaml.load(template.render(data))
            elif isfile(fn + '.json'):
                log.debug("Pepa ext_pillar load template: %s.json" % fn)
                template = jinja2.Template(open(fn + '.json').read())
                output['pepa_templates'].append('%s: %s' % (category,  re.sub('\W', '_', entry.lower()) + '.json'))
                data = key_value_to_tree(output)
                data['grains'] = __grains__.copy()
                data['pillar'] = pillar.copy()
                results = json.loads(template.render(data))
            else:
                log.debug("Pepa ext_pillar template doesn't exist: %s.(json|yaml)" % fn)
                continue

            if results != None:
                for key in results:
                    log.debug("Pepa ext_pillar substituting key: %s value: %s" % (key, results[key]))
                    output[key] = results[key]

    tree = key_value_to_tree(output)
    pillar_data = tree
    pillar_data['pepa'] = tree.copy()
    return pillar_data