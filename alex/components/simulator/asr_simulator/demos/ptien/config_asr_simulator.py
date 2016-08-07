#!/usr/bin/env python
# vim: set fileencoding=UTF-8 filetype=python :
#
#  When the configuration file is loaded, several automatic transformations
#  are applied:
#
# 1) '{cfg_abs_path}' as a substring of atomic attributes is replaced by
#    an absolute path of the configuration files.  This can be used to
#    make the configuration file independent of the location of programs
#    using the configuration file.
#
# or better user use the as_project_path function

import random

# Initialise the generators so that the NLG sample different templates every
# time you start the system.

random.seed()

from alex.utils.config import as_project_path, online_update

from alex.utils.database.python_database import PythonDatabase
from alex.components.simulator.user_simulator.simple_user_simulator import SimpleUserSimulator

config = {
    'database':{
        'type':PythonDatabase,
        'debug':True,
        'PythonDatabase':{
            'files':[as_project_path('applications/PublicTransportInfoEN/data/thanh_data/stops.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/streets.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/vehicles.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/time.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/cities.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/time_relative.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/places.txt'),
                    as_project_path('applications/PublicTransportInfoEN/data/thanh_data/boroughs.txt'),
                    ],
                    
        },
    },
    'domain':{#probably like the configuration for suser simulator
            'dialogue_act_definitions': {#dialogue acts which user simulator used for answering
                'request':{
                    'slot_included': True,
                    'value_included': False,
                    'combineable_slots': ['number_transfer', 'duration', 'distance']
                },
                'inform':{
                    'slot_included': True,
                    'value_included': True,
                    'slot_from': 'sys_da', #in normal case, list of slots will be informed is taken from system dialogue request act, or from goal
                    'value_from': 'goal', #in normal case, where to get values for selected slots
                    'limited_slots': [], #list of slot cant combine
                    'accept_used_slots': False,
                    'use_slot_sequence': True,
                },
                'oog':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                },
                'deny':{
                    'slot_included': True,
                    'value_included': True,
                    'slot_from': 'sys_da',
                    'value_from': 'sys_da',
                    'status_included': 'incorrect',
                },
                'repeat':{
                    'slot_included': False,
                    'value_included': False,
                },
                'help':{
                    'slot_included': False,
                    'value_included': False,
                },
                'apology':{
                    'slot_included': False,
                    'value_included': False,
                },
                'confirm':{#make a question to clarify something, ?User may also make this action?? How to make it? only at the end?, since simulator always know exactly what is going on
                    'slot_included': True,
                    'value_included': True,
                    'status_included': 'filled',
                },
                'canthearyou, notunderstood':{#only available for system, not for user
                },
                'affirm':{#simply YES #something interesting here,  doesn't include slot/value, but slots consider from sys_da and they are correct
                    'slot_included': False,
                    'value_included': False,
                    'slot_from': 'sys_da',
                    'status_included': 'correct',
                    'status_in_all_slots': True,
                    #TODO add cheeck all sys_da slot?
                    #all_slot_included: True,
                    'act_without_slot': True,
                },
                'ack':{
                    'slot_included': False,
                    'value_included': False,
                },
                'thankyou':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                },
               'silence':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                },
               'reqalts':{
                    'slot_included': True,
                    'value_included': True,
                    'combineable_slots': ['alternative'],
                    'slot_from': 'none',
                    'value_from': 'function',
                    #'value_fun': alternative_value_fun,
                },
                'negate':{
                    'slot_included': False,
                    'value_included': False,
                    'slot_from': 'sys_da',
                    'status_included': 'incorrect',
                    'act_without_slot': True,
                },
                'bye':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                },
                'hello':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                    #'add_to_da_prob':0.5,
                },
                'restart':{#TODO how to user this action?
                    'slot_included': False,
                    'value_included': False,
                },
                'hangup':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                },
                'help':{#How?
                    'slot_included': False,
                    'value_included': False,
                },
            },
            'slot_table_field_mapping':{'from_stop':[('stops','stop')],
                                        'to_stop':[('stops', 'stop')],
                                        'from_borough':[('boroughs', 'borough')],
                                        'to_borough':[('boroughs', 'borough')],
                                        'from_city':[('cities', 'city')],
                                        'to_city':[('cities', 'city')],
                                        'from_street':[('streets', 'street')],
                                        'to_street':[('streets', 'street')],
                                        'departure_time':[('time', 'time')],
                                        'departure_time_rel':[('time_relative', 'relative')],
                                        'arrival_time': [('time', 'time')],
                                        'arrival_time_rel': [('time_relative', 'relative')],
                                        'vehicle': [('vehicles', 'vehicle')],
                                        'street':[('streets', 'street'), ('places', 'street')],
                                        'city':[('cities', 'city'), ('places', 'city')],
                                        'state':[('states', 'state'), ('places', 'state')],
                                        'task': [lambda: ['find_connection', 'find_platform', 'weather']],
                                        'alternative': [lambda: ['next', 'prev', 'last', '1', '2', '3', '4', 'next hour']],
            }, 
    },
    'user_simulator':{
        'type': SimpleUserSimulator,
        'SimpleUserSimulator':{
            
        },
    },
    'asr_simulator':{
        'type': None,
        'debug': True,
        'SimpleASRSimulator':{
            'prob_combine_fun': None,#the function to calculate new prob from two event, particular is prob of da_type and prob of slot- its value
            'act_confusion':{
                'default':{ 
                    'confusion_matrix':{
                        'max_length': 1,
                        'confusable_acts': [],
                        'onlist_fraction_alpha': 0.75,
                        'onlist_fraction_beta': 1.5,
                        'confusion_types':{#confusion type for information in an action, default for all actions wihout configuration
                            'correct': 1.0,#meaning that the correction information will be still corret at 90%, highest prob on the hyp list
                            'onlist': 0.0,#The correct information is on the hyp. list but smaller prob.
                            'offlist': 0.0,#the correct information is off the hyp.list
                            'silence': 0.0,#the slot is ignored this time, and the respective action will becom silence
                        },
                        'probability_generator':{#using dicrehet for generator probability
                            'correct':{#the confution type = correct
                                'correct':6.0, #the part for the correct item
                                'onlist': 1.0, #the part for other items on the list of hypotheses
                                'offlist': 0.0, #the part for the osther items which are not on the list
                            },
                            'onlist':{
                                'correct':2.5,
                                'onlist':1.0,
                                'offlist':2.5,
                            },
                            'offlist':{
                                'correct':3.0,
                                'onlist':1.0,
                                'offlist':6.0,
                            },
                        },
                    },
                },
                'affirm':{
                    'confusion_matrix':{
                        'max_length': 2,
                        'confusable_acts': ['affirm', 'negate'],
                        'confusion_types':{
                            'correct': 0.95,
                            'onlist': 0.05,
                            'offlist': 0.0,
                            'silence': 0.0,#the slot is ignored this time, and the respective action will becom silence
                        },
                    },
                },
                'negate':{
                    'confusion_matrix':{
                        'max_length': 2,
                        'confusable_acts': ['affirm', 'negate'],
                        'confusion_types':{
                            'correct': 0.95,
                            'onlist': 0.05,
                            'offlist': 0.0,
                            'silence': 0.0,#the slot is ignored this time, and the respective action will becom silence
                        },
                    },
                },
            },
            'slot_confusion':{
                'to_stop_fake':{
                    'to_stop': 0.5,
                    ('departure', 'arrival'): 0.5,
                },
            },
            'information_confusion_types': ['correct', 'onlist', 'offlist', 'silence'],#only for imagining
            'default':{#define ASR simulator for a slot, the key default will be apply foo all slots are not specified explicitly
                #default for all informatin confusion and prob. gnerator
                'default_confusion_matrix':{
                    'max_length': 5,
                    'onlist_fraction_alpha': 0.75,
                    'onlist_fraction_beta': 1.5,
                    'confusion_types':{#confusion type for information in an action, default for all actions wihout configuration
                        'correct': 0.9,#meaning that the correction information will be still corret at 90%, highest prob on the hyp list
                        'onlist': 0.05,#The correct information is on the hyp. list but smaller prob.
                        'offlist': 0.05,#the correct information is off the hyp.list
                        'silence': 0.0,#the slot is ignored this time, and the respective action will becom silence
                    },
                    'probability_generator':{#using dicrehet for generator probability
                        'correct':{#the confution type = correct
                            'correct':6.0, #the part for the correct item
                            'onlist': 1.0, #the part for other items on the list of hypotheses
                            'offlist': 3.0, #the part for the osther items which are not on the list
                        },
                        'onlist':{
                            'correct':2.5,
                            'onlist':1.0,
                            'offlist':2.5,
                        },
                        'offlist':{
                            'correct':3.0,
                            'onlist':1.0,
                            'offlist':6.0,
                        },
                    },
                },
                'inform_fake_confusion_matrix':{#a refined confusion matrix for inform action
                    'confusion_types':{
                        'correct': 0.9,
                        'onlist': 0.05,
                        'offlist': 0.05,
                    },
                    #the default_prob.generator is missing the default one should be used
                },
            },#end of the default consusion for all slots
            'task_fake':{
                'default_confusion_matrix':{
                    'max_length': 3,
                    'onlist_fraction_alpha': 0.75,
                    'onlist_fraction_beta': 1.5,
                    'confusion_types':{#confusion type for information in an action, default for all actions wihout configuration
                        'correct': 0.9,#meaning that the correction information will be still corret at 90%, highest prob on the hyp list
                        'onlist': 0.05,#The correct information is on the hyp. list but smaller prob.
                        'offlist': 0.05,#the correct information is off the hyp.list
                        'silence': 0.0,#the slot is ignored this time, and the respective action will becom silence
                    },
                    'probability_generator':{#using dicrehet for generator probability
                        'correct':{#the confution type = correct
                            'correct':6.0, #the part for the correct item
                            'onlist': 1.0, #the part for other items on the list of hypotheses
                            'offlist': 3.0, #the part for the osther items which are not on the list
                        },
                        'onlist':{
                            'correct':2.5,
                            'onlist':1.0,
                            'offlist':2.5,
                        },
                        'offlist':{
                            'correct':3.0,
                            'onlist':1.0,
                            'offlist':6.0,
                        },
                    },
                },
            },
            'slot_name':{
                'default_confusion_matrix':{
                    'confusion_types':{
                        #something goes here
                    },
                    'probability_generator':{
                        #something goes here
                    },
                },
                'inform_confusion_matrix':{
                    
                }
            }#end of the confusion descrip for slot_name
        },#end of SimpleUserSimulator
    },#end of asr_simulator
}
