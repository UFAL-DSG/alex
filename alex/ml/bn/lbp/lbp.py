#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
            node.send_messages(False)


    def run(self, n_iterations):
        """Run the lbp algorithm."""
        for node in self.nodes:
            node.init_messages()

        for i in range(n_iterations):
            print "Step #%d" % i
            self.forward_step()
            self.backward_step()