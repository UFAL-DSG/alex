#!/usr/bin/env python
# -*- coding: utf-8 -*-

class LBP(object):

    def __init__(self):
        self.nodes = []

    def add_nodes(self, nodes):
        self.nodes.extend(nodes)

    def forward_step(self):
        for node in self.nodes:
            node.send_messages()

    def update_beliefs(self):
        for node in self.nodes:
            node.update_belief()

    def backward_step(self):
        for node in self.nodes[::-1]:
            node.send_messages()


    def run(self, n_iterations):
        for i in range(n_iterations):
            print "Step #%d" % i
            self.forward_step()
            self.backward_step()

        self.update_beliefs()