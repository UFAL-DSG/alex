#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Node representations for factor graph."""

import abc
import operator

from collections import defaultdict

from bn.utils import constant_factory

class Node(object):
    """Abstract class for nodes in factor graph."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        self.name = name
        self.neighbors = {}
        self.message_from = defaultdict(constant_factory(1.0))
        self.belief = None

    def add_neighbor(self, node):
        """Add a neighboring node"""
        self.neighbors[node.name] = node

    def init_messages(self):
        """Initialize messages."""
        for neighbor in self.neighbors:
            self.message_from[neighbor.name] = 1
        self.update_belief()

    @abc.abstractmethod
    def message_to(self, node_name): #pylint: disable=W0613
        """Compute the message to neighboring node."""
        return

    @abc.abstractmethod
    def update_belief(self):
        """Update the belief."""
        return


class DiscreteVariableNode(Node):
    """Node containing variable."""

    def __init__(self, name):
        super(DiscreteVariableNode, self).__init__(name)

    def message_to(self, node):
        return self.belief / self.message_from[node.name]

    def update_belief(self):
        self.belief = reduce(operator.mul, self.message_from.itervalues())


class DiscreteFactorNode(Node):
    """Node containing factor."""

    def __init__(self, name, factor):
        super(DiscreteFactorNode, self).__init__(name)
        self.factor = factor

    def message_to(self, node):
        common_variables = sorted(
            set(self.factor.variables).intersection(node.factor.variables))
        message = self.belief / self.message_from[node.name]
        return message.marginalize(common_variables)

    def update_belief(self):
        self.belief = self.factor * reduce(operator.mul,
                                           self.message_from.itervalues())

