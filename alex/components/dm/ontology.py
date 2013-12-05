#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import re

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

    def __contains__(self, key):
        return key in self.ontology

    def load(self, file_name):
        on_mod = load_as_module(file_name, force=True)
        if not hasattr(on_mod, 'ontology'):
            raise OntologyException("The ontology file does not define the 'ontology' object!")
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
        return [slot for slot in self.ontology['slots'] if 'system_requests' in self.ontology['slot_attributes'][slot]]

    @lru_cache(maxsize=10)
    def slots_system_confirms(self):
        """ Return all slots the system can request.
        """
        return [slot for slot in self.ontology['slots'] if 'system_confirms' in self.ontology['slot_attributes'][slot]]

    @lru_cache(maxsize=10)
    def slots_system_selects(self):
        """ Return all slots the system can request.
        """
        return [slot for slot in self.ontology['slots'] if 'system_selects' in self.ontology['slot_attributes'][slot]]

    @lru_cache(maxsize=1000)
    def last_talked_about(self, dat, name, value):
        """Returns a list of slots and values that should be used to for tracking about what was talked about recently,
        given the input dialogue acts.

        :param dat: the source dialogue act type
        :param name: the source slot name
        :param value: the source slot value
        :return: returns a list of target slot names and values used for tracking
        """
        lta_tsv = []

        dat = dat if dat else ''
        name = name if name else ''
        value = value if value else ''

        for target_slot, target_values in self.ontology['last_talked_about'].iteritems():
            for target_value, source_patterns in target_values.iteritems():
                for source_dat, source_name, source_value in source_patterns:
                    if re.match(source_dat, dat) and re.match(source_name, name) and re.match(source_value, value):
                        lta_tsv.append((target_slot, target_value))

        return lta_tsv

    @lru_cache(maxsize=1000)
    def reset_on_change(self, slot, changed_slot):
        if slot in self.ontology['reset_on_change']:
            for pattern in self.ontology['reset_on_change'][slot]:
                if re.match(pattern, changed_slot):
                    return True
        else:
            return False

    def get_compatible_vals(self, slot_pair, value):
        """Given a slot pair (key to 'compatible_values' in ontology data), this returns the set of
        compatible values for the given key. If there is no information about the given pair,
        None is returned.

        :param slot_pair: key to 'compatible_values' in ontology data
        :param value: the subkey to check compatible values for
        :rtype: set
        """
        if slot_pair in self.ontology['compatible_values']:
            return self.ontology['compatible_values'][slot_pair].get(value, set()).copy()
        return None
