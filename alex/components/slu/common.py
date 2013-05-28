import autopath

from alex.components.slu.base import SLUInterface, SLUPreprocessing, \
                                     CategoryLabelDatabase
from alex.components.slu.exception import SLUException
from alex.components.slu.dailrclassifier import DAILogRegClassifier

def get_slu_type(cfg):
    """Get slu type from the configuration."""
    return cfg['SLU']['type']


def slu_factory(slu_type, cfg):
    cldb = CategoryLabelDatabase(cfg['SLU']['cldb'])

    preprocessing_cls = cfg['SLU'].get('preprocessing_cls', SLUPreprocessing)
    preprocessing = preprocessing_cls(cldb)

    if isinstance(slu_type, SLUInterface):
        slu = slu_type(preprocessing, cfg=cfg['SLU'].get(slu_type, None))
        return slu
    if slu_type == 'DAILogRegClassifier':
        slu = DAILogRegClassifier(preprocessing)
        slu.load_model(
            cfg['SLU']['DAILogRegClassifier']['model'])

        return slu
    else:
        raise SLUException(
            'Unsupported spoken language understanding: {type_}'\
            .format(type_=cfg['SLU']['type']))
