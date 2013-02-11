#!/usr/bin/env python
# -*- coding: utf-8 -*-

from random import seed, random, choice
from time import time

from node import Node, GroupingNode, Goal, GroupingGoal, ConstChangeGoal

if __name__ == '__main__':
    #-----------------------------------------------------------------------------
    cardinality = 200
    numObs = 15
    numTurns = 15
    goalParams = {'pRemebering': 0.9, 'pObserving': 0.9}
    #-----------------------------------------------------------------------------

    seed(0)
    values = range(cardinality)
    nodes = []
    groupingNodes = []
    constNodes = []
    observations = []

    prior = Node(name='Prior', desc='0', card=cardinality)
    for v in values:
        prior[v] = 1.0
    prior.normalise()
    prior.explain()
    nodes.append(prior)

    groupingPrior = GroupingNode(name='GroupingPrior', desc='0', card=cardinality)
    for v in values:
        groupingPrior.addOthers(v, 1.0)
    groupingPrior.normalise()
    groupingPrior.explain()
    groupingNodes.append(groupingPrior)

    constPrior = GroupingNode(name='ConstChangePrior', desc='0', card=cardinality)
    for v in values:
        constPrior.addOthers(v, 1.0)
    constPrior.normalise()
    constPrior.explain()
    constNodes.append(constPrior)

    print('==' * 60)

    start = time()

    for turn in range(1, numTurns):
        # generate observation
        #-----------------------------------------------------------------------------
        observation = Node(name='Obs', desc=str(turn), card=len(values))

        for i in range(numObs):
            observation[choice(values)] = random()

        if random() > 0.1:
            observation['__silence__'] = random()

        observation.normalise()
        observations.append(observation)

        # print values
        observation.explain()
        print('. ' * 60)

        # create goal for this turn
        #-----------------------------------------------------------------------------
        goal = Goal(
            name='Goal', desc=str(turn), card=cardinality, parameters=goalParams)
        goal.setParents({'previous': nodes[-1],
                         'observation': observations[-1]})
        nodes.append(goal)

        # update belief for the goal
        goal.update()

        # print values
        goal.explain()
        print('. ' * 60)

        # create grouping goal for this turn
        #-----------------------------------------------------------------------------
        groupingGoal = GroupingGoal(name='GroupingGoal', desc=str(turn),
                                    card=cardinality, parameters=goalParams)
        groupingGoal.setParents({'previous': groupingNodes[-1],
                                 'observation': observations[-1]})
        groupingNodes.append(groupingGoal)

        # update belief for the goal
        groupingGoal.update()

        # print values
        groupingGoal.explain()
        print('. ' * 60)

        # create const change goal for this turn
        #-----------------------------------------------------------------------------
        constGoal = ConstChangeGoal(name='ConstChangeGoal', desc=str(turn),
                                    card=cardinality, parameters=goalParams)
        constGoal.setParents({'previous': constNodes[-1],
                              'observation': observations[-1]})
        constNodes.append(constGoal)

        # update belief for the goal
        constGoal.update()

        # print values
        constGoal.explain()
        print('--' * 60)

    print('Time: %.2f' % (time() - start))
