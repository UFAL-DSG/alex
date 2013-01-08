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
        self.outgoing = {}
        self.incoming = {}
        self.incoming_message = {}
        self.belief = None

    def add_edge_to(self, node):
        """Add a neighboring node"""
        self.outgoing[node.name] = node
        node.incoming[self.name] = self

    @abc.abstractmethod
    def init_messages(self):
        return
        
    @abc.abstractmethod
    def message_to(self, node):
        """Compute a message to neighboring node."""
        return

    @abc.abstractmethod
    def message_from(self, node, message):
        """Save message from neighboring node."""
        return

    def send_messages(self):
        """Send messages to all neighboring nodes."""
        for neigbor_name in self.outgoing:
            self.message_to(neigbor_name)


class DiscreteVariableNode(Node):
    """Node containing variable."""

    def __init__(self, name, values):
        super(DiscreteVariableNode, self).__init__(name)
        self.values = values
        self.belief = constant_factor({name: values}, len(values))
        self.is_observed = False

    def init_messages(self):
        const_msg = constant_factor({self.name: self.values}, len(self.values))

        for neighbor in self.incoming:
            self.incoming_message[neighbor] = const_msg

        for neighbor in self.outgoing:
            self.incoming_message[neighbor] = const_msg

    def message_to(self, node):
        if self.is_observed:
            node.message_from(self, self.belief)
        else:
            node.message_from(self, self.belief /
                                    self.incoming_message[node.name])

    def message_from(self, node, message):
        if not self.is_observed:
            self.belief /= self.incoming_message[node.name]
            self.belief *= message
            self.incoming_message[node.name] = message

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
        self.belief = factor

    def init_messages(self):
        for name, node in self.incoming.iteritems():
            self.incoming_message[name] = constant_factor({name: node.values},
                                                          len(node.values))
        for name, node in self.outgoing.iteritems():
            self.incoming_message[name] = constant_factor({name: node.values},
                                                          len(node.values))


    def message_to(self, node):
        belief_without_node = self.belief / self.incoming_message[node.name]
        message = belief_without_node.marginalize([node.name])
        node.message_from(self, message)

    def message_from(self, node, message):
        self.belief /= self.incoming_message[node.name]
        self.belief *= message
        self.incoming_message[node.name] = message
