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
    def __init__(self, file_name=None):
        self.ontology = {}
        if file_name:
            self.load(file_name)

    def __getitem__(self, key):
        return self.ontology[key]

    def load(self, file_name):
        on_mod = load_as_module(file_name, force=True)
        if not hasattr(on_mod, 'ontology'):
            raise OntologyException("The ontology file does not " +
                                    "define the 'ontology' object!")
        self.ontology = on_mod.ontology

    def slot_has_value(self, name, value):
        """ Check whether the slot and the value are compatible.
        """
        return value in self.ontology['slots'][name]

    def slot_is_binary(self, name):
        """Check whether the given slot has a binary value (using the 'binary'
        key in the 'slot_attributes' for the given slot name).

        :param name: name of the slot being checked
        """
        return 'binary' in self.ontology['slot_attributes'][name]

    @lru_cache(maxsize=10)
    def slots_system_requests(self):
        """ Return all slots the system can request.
        """
        return [slot for slot in self.ontology['slots'] \
                if 'system_requests' in self.ontology['slot_attributes'][slot]]

    @lru_cache(maxsize=10)
    def slots_system_confirms(self):
        """ Return all slots the system can request.
        """
        return [slot for slot in self.ontology['slots'] \
                if 'system_confirms' in self.ontology['slot_attributes'][slot]]
