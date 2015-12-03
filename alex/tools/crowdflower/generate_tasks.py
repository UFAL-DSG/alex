#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alex.components.slu.da import DialogueAct, DialogueActItem
import random
from argparse import ArgumentParser
from alex.utils.config import as_project_path
from alex.applications.PublicTransportInfoEN.preprocessing import PTIENNLGPreprocessing
from alex.components.nlg.template import TemplateNLG

STOPS = ['Astor Place',
         'Bleecker Street',
         'Bowery',
         'Bowling Green',
         'Broad Street',
         'Bryant Park',
         'Canal Street',
         'Cathedral Parkway',
         'Central Park North',
         'Chambers Street',
         'City College',
         'City Hall',
         'Columbia University',
         'Columbus Circle',
         'Cortlandt Street',
         'Delancey Street',
         'Dyckman Street',
         'East Broadway',
         'Essex Street',
         'Franklin Street',
         'Fulton Street',
         'Grand Central',
         'Grand Street',
         'Harlem',
         'Herald Square',
         'Houston Street',
         'Hudson Yards',
         'Hunter College',
         'Inwood',
         'Lafayette Street',
         'Lincoln Center',
         'Marble Hill',
         'Museum of Natural History',
         'New York University',
         'Park Place',
         'Penn Station',
         'Port Authority Bus Terminal',
         'Prince Street',
         'Rector Street',
         'Rockefeller Center',
         'Roosevelt Island',
         'Sheridan Square',
         'South Ferry',
         'Spring Street',
         'Times Square',
         'Union Square',
         'Wall Street',
         'Washington Square',
         'World Trade Center', ]

QUESTIONS = [[DialogueActItem('request', 'duration')],
             [DialogueActItem('request', 'arrival_time')],
             [DialogueActItem('inform', 'alternative', 'next')],
             [DialogueActItem('inform', 'vehicle', 'bus')],
             [DialogueActItem('inform', 'time', '6:00'), DialogueActItem('inform', 'ampm', 'evening')],
             [DialogueActItem('inform', 'to_stop', None)]]


CFG = {'NLG': {'debug': True,
               'type': 'Template',
               'Template': {'model': as_project_path('tools/crowdflower/task_templates.cfg'),
                            'ontology': as_project_path('applications/PublicTransportInfoEN/data/ontology.py'),
                            # 'preprocessing_cls': PTIENNLGPreprocessing,
                            },
               }
       }


def generate_task():

    task = []
    da = DialogueAct()

    # indicate that we're looking for connection
    da.append(DialogueActItem('inform', 'task', 'find_connection'))
    if random.random() > 0.7:
        task.append(da)
        da = DialogueAct()

    # get two distinct stops
    from_stop = random.choice(STOPS)
    to_stop = from_stop
    while to_stop == from_stop:
        to_stop = random.choice(STOPS)
    da.append(DialogueActItem('inform', 'from_stop', from_stop))
    if random.random() > 0.8:
        task.append(da)
        da = DialogueAct()
    da.append(DialogueActItem('inform', 'to_stop', to_stop))
    task.append(da)

    # generate random subsequent questions
    questions = random.sample(range(6), random.randint(5, 6) - len(task))

    for question in sorted(questions):
        dais = QUESTIONS[question]

        if dais[0].name == 'to_stop':
            new_to_stop = random.choice(STOPS)
            while new_to_stop == from_stop or new_to_stop == to_stop:
                new_to_stop = random.choice(STOPS)
            dais[0].value = new_to_stop

        da = DialogueAct()
        da.extend(dais)
        task.append(da)

    return task


def main(num_tasks):
    random.seed()
    nlg = TemplateNLG(cfg=CFG)
    for _ in xrange(num_tasks):
        task = generate_task()
        sents = [nlg.generate(da) for da in task]
        print '\t'.join([unicode(da) for da in task])
        print '\t'.join(sents)
        print ''

if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('num_tasks', type=int, metavar='NUM_TASKS')
    args = ap.parse_args()
    main(num_tasks=args.num_tasks)
