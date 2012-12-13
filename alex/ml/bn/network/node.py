#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Node representations for factor graph."""

import abc
import operator

from collections import defaultdict

from bn.utils import constant_factory, constant_factor

class Node(object):
    """Abstract class for nodes in factor graph."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        self.name = name
        self.neighbors = {}
        self.message_from = {}
        self.belief = None

    def add_neighbor(self, node):
        """Add a neighboring node"""
        self.neighbors[node.name] = node
        node.neighbors[self.name] = self

    @abc.abstractmethod
    def message_to(self, node_name):
        """Compute the message to neighboring node."""
        return

    def send_message_to(self, node_name):
        """Send a message to neighboring node."""
        message = self.message_to(node_name)
        self.neighbors[node_name].message_from[self.name] = message

    def send_messages(self):
        """Send messages to all neighboring nodes."""
        self.update_belief()
        for neigbor_name in self.neighbors:
            self.send_message_to(neigbor_name)

    @abc.abstractmethod
    def update_belief(self):
        """Update the belief."""
        return


class DiscreteVariableNode(Node):
    """Node containing variable."""

    def __init__(self, name, values):
        super(DiscreteVariableNode, self).__init__(name)
        self.values = values
        self.belief = constant_factor({name: values}, len(values))
        self.is_observed = False

    def message_to(self, node_name):
        if self.is_observed:
            return self.belief
        else:
            return self.belief / self.message_from[node_name]

    def update_belief(self):
        if not self.is_observed:
            self.belief = reduce(operator.mul, self.message_from.itervalues())

    def observed(self, value):
        """Set observation."""
        if value is not None:
            self.is_observed = True
        else:
            self.is_observed = False
        self.belief.observed((value,))


class DiscreteFactorNode(Node):
    """Node containing factor."""

    def __init__(self, name, factor):
        super(DiscreteFactorNode, self).__init__(name)
        self.factor = factor

    def init_messages(self):
        "Create messages from neighboring variable nodes."
        # Create messages from neighbors
        for name, neighbor in self.neighbors.iteritems():
            self.message_from[name] = neighbor.belief.marginalize([name])
        # Create first belief
        self.update_belief()
        # Set message from this node in neighbors
        for name, neighbor in self.neighbors.iteritems():
            neighbor.message_from[self.name] = self.message_to(name)


    def message_to(self, node_name):
        node = self.neighbors[node_name]
        message = self.belief / self.message_from[node_name]
        return message.marginalize([node_name])

    def update_belief(self):
        self.belief = self.factor * reduce(operator.mul,
                                           self.message_from.itervalues())

