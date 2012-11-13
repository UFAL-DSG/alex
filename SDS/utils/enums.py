
def enum(*sequential, **named):
    """Useful for creating enumerations.

    e.g.:
    DialogueType = enum(deterministic=0, statistical=1, mix=2)"""

    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)