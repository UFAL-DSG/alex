#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

class LBP(object):
    """Loopy belief propagation algorithm."""

    def __init__(self):
        self.nodes = []

    def add_nodes(self, nodes):
        """Add nodes to graph.

        Messages will be propagated according to the order of nodes.
        """
        self.nodes.extend(nodes)

    def forward_step(self):
        """Do one forward propagation through graph."""
        for node in self.nodes:
            node.send_messages()

    def backward_step(self):
        """Do one backward propagation through graph."""
        for node in self.nodes[::-1]:
            node.send_messages()

    def run(self, n_iterations=1):
        """Run the lbp algorithm."""
        for node in self.nodes:
            node.init_messages()

        for i in range(n_iterations):
            self.forward_step()
            self.backward_step()

class SingleLinkedLBP(LBP):
    """Loopy belief propagation for single linked factor graphs."""

    def add_nodes(self, nodes):
        super(SingleLinkedLBP, self).add_nodes(nodes)
        for node in self.nodes:
            node.wait_for_n = set(
                x for x in node.neighbors.values() if x in nodes)
            node.backward_send_to = []

    def run(self):
        for node in self.nodes:
            node.init_messages()

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
            next = ordering.pop()
            next.update()
            next.normalize()
            #print next.belief
            for x in next.backward_send_to:
                next.message_to(x)


class ComplexLBP(LBP):

    def __init__(self):
        self.layers = []

    def add_layer(self, nodes):
        self.layers.append(nodes)
