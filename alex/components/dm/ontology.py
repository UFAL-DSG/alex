#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

from alex.utils.config import load_as_module
from alex.utils.cache import lru_cache

class OntologyException(Exception):
    pass
    
class Ontology(object):
    """Represents an ontology for a dialogue domain.
    """
    def __init__(self, file_name):
        self.ontology = {}
        if file_name:
            self.load(file_name)

    def __getitem__(self, key):
        return self.ontology[key]
    
    def load(self, file_name):
        on_mod = load_as_module(file_name, force=True)
        if not hasattr(on_mod, 'ontology'):
            raise OntologyException("The ontology file does not define the 'ontology' object!")
        
        self.ontology = on_mod.ontology

    def slot_has_value(self, name, value):
        """ Check whether the slot and the value are compatible.
        """
        return value in self.ontology['slots'][name]
    
    @lru_cache(maxsize=10)    
    def slots_system_requests(self):
        """ Return all slots the system can request.
        """
        return [slot for slot in ontology['slots'] if 'system_requests' in ontology['slot_attributes'][slot]]

    @lru_cache(maxsize=10)    
    def slots_system_confirms(self):
        """ Return all slots the system can request.
        """
        return [slot for slot in ontology['slots'] if 'system_confirms' in ontology['slot_attributes'][slot]]
