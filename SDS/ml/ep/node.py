#!/usr/bin/env python
# -*- coding: utf-8 -*-

exludedValues = set(['__silence__', ])

####################################################################################

class Node(object):
    """A base class for all nodes in a belief state."""

    def __init__(self, name, desc, card):
        self.name = name
        self.desc = desc
        self.cardinality = card
        self.values = {} 

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def __len__(self):
        return len(self.values)

    def __str__(self):
        self.explain()

    def normalize(self):
        """This function normlize the sum of all probabilities to 1.0"""

        norm = sum(self.values.values())

        try:
            for value, prob in self.values.iteritems():
                self.values[value] = prob/norm
        except ZeroDivisionError:
            if len(self.values) > 0:
                for value, prob in self.values.iteritems():
                    self.values[value] = prob/len(self.values)

    def getMostProbableValue(self):
        """The function returns the most probable value and its probability
        in a tuple.
        """

        pMax = -1.0
        vMax = None

        for v, p in self.values.iteritems():
            if p > pMax:
                pMax = p
                vMax = v

        return (vMax, pMax)

    def getTwoMostProbableValues(self):
        """This function returns two most probable values and their probabilities.

        The function returns a tuple consisting of two tuples (value, probability).
        """

        pMax1 = -1.0
        vMax1 = None
        pMax2 = -1.0
        vMax2 = None

        for v, p in self.values.iteritems():
            if p > pMax1:
                pMax2, pMax1 = pMax1, p
                vMax2, vMax1 = vMax1, v
            elif p >pMax2:
                pMax2 = p
                vMax2 = v

        return ((vMax1, pMax1), (vMax2, pMax2))

    def explain(self,  full=None):
        """This function prints the values and their probailities
            for this node.
        """

        if full:
            for value in sorted(self.values.keys()):
                print("Name: %20s:%-10s Value: %-15s Probability: % .17f"
                      % (self.name, self.desc, value, self.values[value]))
        else:
            for v in self.getTwoMostProbableValues():
                print("Name: %20s:%-10s Value: %-15s Probability: % .17f"
                      % (self.name, self.desc, v[0], v[1]))

        print(('Cardinality: %.4d'+' '*49+' Total: % .17f')
               % (self.cardinality, sum(self.values.values())))

####################################################################################

class Goal(Node):
    """Goal can contain only the same values as the observations.

        As a consequence, it can contain values of its previous node.
    """

    def __init__(self, name, desc, card, parameters, parents = None):
        Node.__init__(self, name, desc, card)
        self.parameters = parameters
        self.parents = parents

    def setParents(self, parents):
        self.parents = parents

    def setValues(self):
        """The function copy values from its previous node and from observation nodes."""

        for v in self.parents['previous'].values:
            self.values[v] = 0.0

        for v in self.parents['observation'].values:
            if v not in exludedValues:
                self.values[v] = 0.0

    def update(self):
        """This function update belief for the goal."""

        # first, I have to get values for this node from the previous node
        # and observations
        self.setValues()

        # go over all the node's and parents' value combinations
        for cur in self.values:
            for prev in self.parents['previous'].values:
                for obs in self.parents['observation'].values:
                    self.values[cur] += self.probTable(cur,
                                        {'previous': (prev, self.parents['previous'].cardinality),
                                         'observation': (obs, self.parents['observation'].cardinality)}) \
                                        * self.parents['previous'].values[prev] \
                                        * self.parents['observation'].values[obs]

#                    print('Prev: %10s:p=%.4f Obs: %10s:p=%.4f -> p=%.4f Cur: %10s:p=%.4f'
#                          % (prev,
#                             self.parents['previous'].values[prev],
#                             obs, self.parents['observation'].values[obs],
#                             self.probTable(cur,
#                                        {'previous': (prev,self.parents['previous'].cardinality),
#                                         'observation': (obs, self.parents['observation'].cardinality)}),
#                             cur, self.values[cur]))

    def probTable(self, value, parents):
        """This function defines how the coditional probability is computed.

        pRemebering - probability that the previous value is correct
        pObserving  - probability that the observed value is correct
        """

        if parents['observation'][0] == '__silence__':
            # there is no observation
            if parents['previous'][0] == value:
                return self.parameters['pRemebering']
            else:
                return (1-self.parameters['pRemebering'])/(parents['previous'][1] - 1)
        else:
            # there is observation
            if parents['observation'][1] == 1:
                # if there is only one observation than it replaces any previous values
                return 1.0
            elif parents['observation'][0] == value:
                return self.parameters['pObserving']
            else:
                return (1-self.parameters['pObserving'])/(parents['observation'][1] - 1)

####################################################################################

class GroupingNode(Node):
    def __init__(self, name, desc, card):
        Node.__init__(self, name, desc, card)
        self.others = set()
        self.values['__others__'] = 0.0

    def __getitem__(self, key):
        try:
            return self.values[key]
        except KeyError:
            if key in self.others:
                return self.values['__others__'] / len(self.others)

    def __setitem__(self, key, value):
        self.values[key] = value

        if key in self.others:
            self.others.remove(key)

    def __len__(self):
        return len(self.values)+len(self.others)

    def __str__(self):
        self.explain()

    def explain(self, full=None):
        """This function explains the values for this node.

        In additon to the Node's function, it prints the cardinality of the others
        set.
        """
        Node.explain(self, full)

        print('Cardinality of __others__: %4d ' % len(self.others))

    def addOthers(self, value, probability):
        self.others.add(value)
        self.values['__others__'] += probability

    def splitOff(self, value):
        """This function split off the value from the others set and place it into the
        values dict.
        """

        if value in self.others:
            p = self.values['__others__']/len(self.others)
            self.others.remove(value)
            self.values['__others__'] -= p
            self.values[value] = p

####################################################################################

class GroupingGoal(GroupingNode, Goal):
    """GroupingGoal implements all functionality as is include in Goal; however,
    it only update the values for which was observed some evidence.
    """

    def __init__(self, name, desc, card, parameters, parents = None):
        GroupingNode.__init__(self, name, desc, card)
        self.parameters = parameters
        self.parents = parents

    def setValues(self):
        """The function copy values from its previous node and from observation nodes.
        """

        for v in self.parents['previous'].values:
            self.values[v] = 0.0

        for v in self.parents['observation'].values:
            if v not in exludedValues:
                self.values[v] = 0.0

            # split off all observed values in the previous node
            self.parents['previous'].splitOff(v)

        self.others = self.parents['previous'].others

    def update(self):
        """This function update belief for the goal."""

        # first, I have to get values for this node from the previous node
        # and observations
        self.setValues()

        # go over all the node's and parents' value combinations
        for cur in self.values:
            if cur == '__others__':
                continue

            for prev in self.parents['previous'].values:
                for obs in self.parents['observation'].values:
                    self.values[cur] += self.probTable(cur,
                                        {'previous': (prev, self.parents['previous'].cardinality),
                                         'observation': (obs, self.parents['observation'].cardinality)}) \
                                        * self.parents['previous'].values[prev] \
                                        * self.parents['observation'].values[obs]

        # update the __others__ value
        self.values['__others__'] = 1 - sum(self.values.values())

        # TODO: now we could reduce the number of updated values
        # if len(self.values) > 50:
        #
        # we do not have to remove these values,
        # it is better to just move them into self.others
        # and their probability add to self.values['__others__']
        #
        # the candidates for this operation are those values which has  probability
        # similar to those of others
        #
        # in other words we want very probable and very inpropable values to be split off

####################################################################################

class ConstChangeGoal(GroupingGoal):
    """ConstChangeGoal implements all functionality as is include in GroupingGoal; however,
    it that there are only two transition probabilites for transitions between
    the same values and the different values.
    """

    def __init__(self, name, desc, card, parameters, parents = None):
        GroupingGoal.__init__(self, name, desc, card, parameters, parents)

    def update(self):
        """This function update belief for the goal."""

        # first, I have to get values for this node from the previous node
        # and the observations
        self.setValues()

        # go over all the node's values
        for cur in self.values:
            if cur == '__others__':
                continue

            for obs in self.parents['observation'].values:
                # now compute transitions from the same value to the same value
                #  => use cur as previous
                self.values[cur] += self.probTable(cur,
                                    {'previous': (cur, self.parents['previous'].cardinality),
                                     'observation': (obs, self.parents['observation'].cardinality)}) \
                                    * self.parents['previous'].values[cur] \
                                    * self.parents['observation'].values[obs]

                # now compute transitions from the other values to the cur value
                #  => use cur as previous
                self.values[cur] += self.probTable(cur,
                                    {'previous': ('__other__', self.parents['previous'].cardinality),
                                     'observation': (obs, self.parents['observation'].cardinality)}) \
                                    * (1-self.parents['previous'].values[cur]) \
                                    * self.parents['observation'].values[obs]

        # update the __others__ value
        self.values['__others__'] = 1 - sum(self.values.values())



