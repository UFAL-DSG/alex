#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Node representations for factor graph."""

import abc
import operator

from bn.utils import constant_factor
from copy import copy


class Node(object):
    """Abstract class for nodes in factor graph."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        self.name = name
        self.neighbors = {}
        self.incoming = {}
        self.incoming_message = {}
        self.belief = None

    def add_edge_to(self, node):
        """Add a neighboring node"""
        self.neighbors[node.name] = node
        node.neighbors[self.name] = self

    @abc.abstractmethod
    def init_messages(self):
        """Initialize incoming messages from all neighbors."""
        raise NotImplementedError()

    @abc.abstractmethod
    def message_to(self, node):
        """Compute a message to neighboring node."""
        raise NotImplementedError()

    @abc.abstractmethod
    def message_from(self, node, message):
        """Save message from neighboring node."""
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self):
        """Update belief state."""
        raise NotImplementedError()

    def send_messages(self):
        """Send messages to all neighboring nodes."""
        self.update()
        for neighbor in self.neighbors.values():
            self.message_to(neighbor)

    def normalize(self):
        """Normalize belief state."""
        self.belief.normalize()


class DiscreteVariableNode(Node):
    """Node containing variable."""

    def __init__(self, name, values):
        super(DiscreteVariableNode, self).__init__(name)
        self.values = values
        self.belief = constant_factor([name], {name: values}, len(values))
        self.is_observed = False

    def init_messages(self):
        const_msg = constant_factor([self.name],
                                    {self.name: self.values},
                                    len(self.values))

        for neighbor in self.neighbors:
            self.incoming_message[neighbor] = const_msg

    def message_to(self, node):
        if self.is_observed:
            node.message_from(self, copy(self.belief))
        else:
            node.message_from(self, self.belief /
                                    self.incoming_message[node.name])

    def message_from(self, node, message):
        if not self.is_observed:
            self.incoming_message[node.name] = message

    def observed(self, assignment_dict):
        """Set observation."""
        if assignment_dict is not None:
            self.is_observed = True
            self.belief.observed(assignment_dict)
        else:
            self.is_observed = False
            self.belief.observed(None)

    def update(self):
        if not self.is_observed:
            self.belief = reduce(operator.mul, self.incoming_message.values())

    def most_probable(self, n=None):
        self.normalize()
        return self.belief.most_probable()


class DiscreteFactorNode(Node):
    """Node containing factor."""

    def __init__(self, name, factor):
        super(DiscreteFactorNode, self).__init__(name)
        self.factor = factor
        self.parameters = {}

    def init_messages(self):
        for name, node in self.neighbors.iteritems():
            self.incoming_message[name] = constant_factor([name],
                                                          {name: node.values},
                                                          len(node.values))
        self.update()

    def message_to(self, node):
        belief_without_node = self.belief / self.incoming_message[node.name]
        message = belief_without_node.marginalize([node.name])
        node.message_from(self, message)

    def message_from(self, node, message):
        self.incoming_message[node.name] = message

    def message_from_parameter(self, node, parameter):
        self.parameters[node.name] = parameter

    def update(self):
        self.belief = self.factor * reduce(operator.mul,
                                           self.incoming_message.values())


class DiscreteConvertedFactorNode(DiscreteFactorNode):
    """Node containing factor and a function, which preprocess values."""

    def __init__(self, name, factor, function):
        super(DiscreteConvertedFactorNode, self).__init__(name, factor)
        self.function = function

    def update(self):
        product_of_messages = reduce(operator.mul,
                                     self.incoming_message.values())
        self.belief = product_of_messages.multiply_by_converted(self.factor,
                                                                self.function)

class ParameterNode(Node):
    """Node containing parameter."""

    def __init__(self, name, parameter):
        super(ParameterNode, self).__init__(name)
        self.parameter = parameter
        self.beta = sum(log(gamma(self.parameter))) - gamma() # TODO

    def init_messages(self):
        pass

    def message_to(self, node):
        node.message_from_parameter(self, self.parameter)

    def message_from(self, node, message):
        pass

    def update(self):
        pass
