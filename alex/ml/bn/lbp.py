#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Belief propagation algorithms for factor graph."""

import abc
import itertools


class BPError(Exception):
    pass


class LBPError(BPError):
    pass


class BP(object):
    """Abstract class for Belief Propagation algorithm."""

    __metaclass__ = abc.ABCMeta

    def run(self):
        """Run inference algorithm."""
        raise NotImplementedError()


class LBP(BP):
    """Loopy Belief Propagation.

    LBP is an approximative inference algorithm for factor graphs. LBP works
    with generic factor graphs. It does accurate inference for trees
    and is equal to sum-product algorithm there.

    It is possible to specify which strategy should be used for choosing next
    node for update. Sequential strategy will update nodes in exact order in
    which they were added. Tree strategy will assume the graph is a tree
    (without checking) and will do one pass of sum-product algorithm.
    """

    def __init__(self, strategy="sequential", **kwargs):
        """Initialize Loopy Belief Propagation algorithm."""
        self.strategy = strategy
        if self.strategy not in ('sequential', 'tree', 'layers'):
            raise LBPError('Unknown strategy.')

        self.options = kwargs
        self.nodes = []
        self.layers = []

    def add_nodes(self, nodes):
        """Add nodes to graph."""
        self.nodes.extend(nodes)

        # Create a tree structure for tree strategy.
        if self.strategy == 'tree':
            for node in self.nodes:
                node.wait_for_n = set(
                    x for x in node.neighbors.values() if x in self.nodes)
                node.backward_send_to = []

    def clear_nodes(self):
        self.nodes = []

    def add_layer(self, layer):
        self.add_nodes(layer)

        if self.strategy == 'layers':
            self.layers.append(layer)

    def add_layers(self, layers):
        """Add layers of nodes to graph."""
        # Flatten layers and save all nodes.
        new_nodes = list(itertools.chain.from_iterable(layers))
        self.add_nodes(new_nodes)

        # Save information about layers.
        if self.strategy == 'layers':
            self.layers.extend(layers)

    def clear_layers(self):
        self.layers = []
        self.clear_nodes()

    def run(self, n_iterations=1, from_layer=None):
        """Run the lbp algorithm."""

        if self.strategy == 'sequential':
            self._run_sequential(n_iterations)
        elif self.strategy == 'tree':
            self._run_tree()
        elif self.strategy == 'layers':
            if from_layer == 'last':
                from_layer = len(self.layers) - 2 if len(self.layers) else None
            self._run_layers(from_layer)

        self._normalize_nodes()

    def init_messages(self):
        for node in self.nodes:
            node.init_messages()

        # Create a tree structure for tree strategy.
        if self.strategy == 'tree':
            for node in self.nodes:
                node.wait_for_n = set(
                    x for x in node.neighbors.values() if x in self.nodes)
                node.backward_send_to = []

    def _normalize_nodes(self):
        for node in self.nodes:
            node.normalize()

    def _run_sequential(self, n_iterations):
        for i in range(n_iterations):
            for node in self.nodes:
                node.send_messages()

            for node in reversed(self.nodes):
                node.send_messages()

    def _run_tree(self):
        ordering = []

        not_updated_nodes = set(self.nodes)
        changed = True
        while changed:
            changed = False
            remove = []
            for x in not_updated_nodes:
                if len(x.wait_for_n) == 1:
                    changed = True

                    remove.append(x)
                    x.update()
                    ordering.append(x)

                    neighbor = x.wait_for_n.pop()
                    x.message_to(neighbor)

                    neighbor.wait_for_n.remove(x)
                    neighbor.backward_send_to.append(x)

            for x in remove:
                not_updated_nodes.remove(x)

        for node in not_updated_nodes:
            node.send_messages()

        while len(ordering) > 0:
            next_node = ordering.pop()
            next_node.update()
            for x in next_node.backward_send_to:
                next_node.message_to(x)

    def _run_layers(self, idx_last_layer=None):
        if idx_last_layer is None:
            # Forward
            self._send_messages_through_layers(self.layers)
            # Backward
            self._send_messages_through_layers(reversed(self.layers))
        else:
            # Forward
            forward_layers = self.layers[idx_last_layer+1:]
            last_layer = self.layers[idx_last_layer]
            self._send_messages_through_layers(forward_layers, last_layer)
            # Backward
            backward_layers = reversed(self.layers[idx_last_layer:])
            self._send_messages_through_layers(backward_layers)

    def _send_messages_through_layers(self, layers, last_layer=None):
        for layer in layers:
            # Send messages from last layer to this layer.
            if last_layer is not None:
                self._send_messages_to_layer(last_layer, layer)

            # Send messages between nodes in this layer.
            self._send_messages_to_layer(layer, layer)

            last_layer = layer

    def _send_messages_to_layer(self, from_layer, to_layer):
        for node in from_layer:
            node.update()
            for name, neighbor in node.neighbors.iteritems():
                if neighbor in to_layer:
                    node.message_to(neighbor)
