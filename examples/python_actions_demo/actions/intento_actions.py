def clean_title(value):
    return value.strip().replace('!!!', '').strip()


def emphasize(value):
    return value.upper() + '!'


ACTIONS = {
    'local.clean_title': {
        'accepts': ['text'],
        'returns': 'text',
        'safety': 'project-python',
        'description': 'Cleans an INTENTO project title using project-local Python.',
        'function': clean_title,
    },
    'local.emphasize': {
        'accepts': ['text'],
        'returns': 'text',
        'safety': 'project-python',
        'description': 'Returns an emphasized uppercase version of text.',
        'function': 'emphasize',
    },
}
