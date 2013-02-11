from alex.utils.exception import SemHubException

from .template import TemplateNLG
from .dummynlg import DummyNLG

def nlg_factory(nlg_type, cfg):
    nlg = None

    # do not forget to maintain all supported dialogue managers
    if nlg_type == 'Dummy':
        nlg = DummyNLG(cfg)
    elif nlg_type == 'Template':
        nlg = TemplateNLG(cfg)
    else:
        raise SemHubException(
            'Unsupported NLG: %s' % nlg_type)

    return nlg

def get_nlg_type(cfg):
    return cfg['NLG']['type']
