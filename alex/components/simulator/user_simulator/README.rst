.. image:: ../../../../alex/doc/alex-logo.png
    :alt: Alex logo

Domain independent user simulator for slot-filling spoken dialogue systems
=================================================

..  image:: https://travis-ci.org/UFAL-DSG/alex.png
    :target: https://travis-ci.org/UFAL-DSG/alex

.. image:: https://readthedocs.org/projects/alex/badge/?version=latest&style=travis
    :target: https://readthedocs.org/projects/alex/?badge=latest
    :alt: Documentation Status

.. image:: https://landscape.io/github/UFAL-DSG/alex/master/landscape.png
   :target: https://landscape.io/github/UFAL-DSG/alex/master
   :alt: Code Health

Description
-----------------
This module is intended to provide different user simulators which may play the role of users on testing and training spoken dialogue systems (SDS).
For current, this module contains only a ``SimpleUserSimulator`` working on dialogue act or semantic level. Thereforce, the document is mostly using to describe the user simulator, defining a domain and making conversations.

Overview
-----------------
The core of the user simulator is working based on a data provider and a metadata describing domain and behaviour of users.
The data provider, roughly speaking, is a bridge helping the simulator accessing domain data - values for slots. The interface of data provider is enclosed in this framework. An simple implementation of the provider working with text files named ``PythonDatabase`` is also included.
The metadata is a python dict encapsulating all domain specification which will be presented very detailed in next sections.

Addation to the code, this module also distributes two examples of using the user simulator. One is quite trivial, appointment scheduling, where user only decides *accept*, *delay* or *reject* an appoinment. Another example is a user simulator for public transport information system, where user manages many slots (e.g. where and when to leave, destination etc.) and answers a variety of system acts (e.g. request, confirm, offer etc.). A short description of these examples is also provided at the end of this document.

Metadata
-----------------
Apart from domain data, defining a metadata configuring the user simulator is the only thing you need to do for deloying a user simulating conversations with your SDS. In the current code, the metadata is defined by a python dict object and may includes the following sections (each section is a key in the dict):

- ``goals``: A list of final goal descriptions which the user may have. :ref:`goals`
- ``slot_table_field_mapping``: A dict mapping each slot to its data sources.
- ``same_table_slot``: A dict specifying slots which must be fetched data from the same row in the same table.
- ``dialogue_act_definitions``: A dict definiing all acts which user may uses and how to build them.
- ``reply_system_acts``: A dict defining how to answer a system act.
- ``data_observation_probability``: A dict presenting the occurrence distribution of data.

All of these configurations will be explained clearly in next sub sections.

.. _goals:

goals
-----------------
You can define multiple final goals as many as you want. The set of goals is presetned by a list of dicts, in which each goal is a dict. Inside a goal definition, we may have the following properties:

- ``fixed_slots``: A list of tuples with two string elements, slot name and its corresponding fixed value.
- ``changeable_slots``: A list of strings including all slots which have values can be changed.
- ``one_of_slot_set``: A list of dicts, each dict presents several sets of slots which are exclusively eliminating each other. In other words, only one of these sets will be active at a specific time.
- ``equivalent_slot``: A list of tuples with elementis are slots which are equivalent in meaning.
- ``sys_unaskable_slots``: A list of strings, listing all slots which system is not allowed to ask users.
- ``default_slots_values``: A list of tuples with two elements, slot name and its default value.
- ``active_prob``: A real number in range of [0, 1] preseting the probability of this goal will be activating.
- ``same_table_slot_keys``: A list of string listing keys/definitions in the ``same_table_slot`` section which will be used in this goal.
- ``goal_post_process_fun``: A function doing post process for the goal, which mean after this goal being sampled the function will be called to guarantee all combination of slots and values are fit in together.
- ``goal_slot_relax_fun``: A function relaxing a slot value when get requiremnts from a system. *Not coded yet :), but this feature may be encoded in act definition*
- ``reward_last_da_fun``: A function rewarding the last system act.
- ``reward_final_goal_fun``: A function providing the final reward after a dialouge finished.
- ``end_dialogue_post_process_fun``: A function will be called after a dialogue completed.
- ``slot_used_sequence``: A dict defining a sequence of slots will be used. For examples, slots at higher level can not be informed when there is no any slots at lower level have been used in previous turns.

The following is an example defining two goals, one is finding connection between two places and another is asking the weather of a city.

::
    
    metadata = {
        'goals': [
                    #the first goal finding route
                    {'fixed_slots':[('task','find_connection'),],
                    'changeable_slots':['from_stop', 'to_stop', 'from_city', 'to_city', 'from_street', 'to_street',
                                        'departure_time', 'arrival_time', 'departure_time_rel', 'arrival_time_rel',
                                        'vehicle',
                                        'number_transfer', 'duration', 'distance',#users dont know these slot
                            ],
                    'one_of_slot_set':[
                            {('from_stop', 'to_stop'):0.3,#choose only one of these set
                            ('from_city', 'to_city'):0.2,
                            ('from_street', 'to_street'):0.3,
                            ('from_stop', 'to_street'):0.2,
                            },#end of the fist defination of one_of_slot_set
                            {():0.3,
                            ('arrival_time',):0.1,
                            ('departure_time',):0.1,
                            ('arrival_time_rel',):0.25,
                            ('departure_time_rel',):0.25,
                            },
                            {():0.5,
                            ('vehicle',):0.5,
                            },
                        ],
                    'equivalent_slots':[('from_stop', 'from_city', 'from_street'), ('to_stop', 'to_city', 'to_street'),
                                        ('arrival_time', 'arrival_time_rel'), ('departure_time', 'departure_time_rel'),
                                    ],
                    'sys_unaskable_slots':['number_transfer', 'duration', 'distance',],
                    'default_slots_values':[('departure_time', 'as soon as possible'), ('vehicle', 'dontcare'), ('arrival_time', 'as soon as possible')],
                    'active_prob':0.8,#probability of observing the task being active
                    'same_table_slot_keys':[],
                    'goal_post_process_fun': None,
                    'goal_slot_relax_fun': None,#support function, relax the value of a slot given curretn goal, e.g. more late arrival, departure sooner
                    'reward_last_da_fun': None,
                    'reward_final_goal_fun': None,
                    'end_dialogue_post_process_fun': None,
                    'slot_used_sequence':{#higher level is only able to used when at least one of slot at previous level has used
                        0:('task',),
                        1:('from_stop', 'from_city', 'from_street', 'to_stop', 'to_city', 'to_street'),
                        2:('departure_time', 'arrival_time', 'departure_tiem_rel', 'arrival_time_rel', 'vehicle'),
                        #only need one of slot in each level informed to get next level
                        },
                    },
                    
                    #The second goal, asking weather of a city
                    {'fixed_slots':[('task','weather'),],
                    'changeable_slots':['city', 'state'],
                    'one_of_slot_set':[],
                    'sys_unaskable_slots':[],
                    'default_slots_values':[],
                    'active_prob':0.2,
                    'same_table_slot_keys':['place'],
                    'goal_post_process_fun': None,
                    'goal_slot_relax_fun': None,
                    },
                ],
    }

Notice that all sections following are also in the metadata dict but we won't write it explicitly.

slot_table_field_mapping
-----------------
This section is used for defining data sources for each slot. It is encoded by a python dict with keys are strings presenting slot names, and the value of each key (slot) is a list containing diferent data sources for fetching values for this slot. The list may contain either one or many tuples and/or one or  many functions. 
In the case of tuple, it will contains two elements corresponding the table name and the field which the slot can receive its values from. Otherwiser, in the case of function, the simulator will call the funtion generating the values for this slot. If there are many bindings in a list, a combination of all values will be considered during sumulation.

In the below is an example defining data bindings for two slots, ``street`` and ``departure_time``. In which *street* is mapped to two data souces, one from table *cities* and another form *places*, and the second slot, ``departure_time``, has values which will be dynamically generated from a function.

::

    'slot_table_field_mapping':{
                            'departure_time':[departure_time_generator],
                            'street':[('streets', 'street'), ('places', 'street')],
                        },

same_table_slot
-----------------
For encoding values for several slots must be fetched from one row in a table, we can define the dict where each key presents a case and will be referred from ``same_table_slot_keys`` in goals definitions. The value for each key is also a python dict which comprises two keys, ``table`` and ``slots``, pointing out the table name and slots which have values must be taken from the same row in that table.

A sample of the ``same_table_slot`` defined below showing a case that all three slots, *street*, *city* and *state* will be fetching their values from one row in a table named *places*.

::

    'same_table_slots':{
            'place':{
                'table': 'places',
                'slots': ['street', 'city', 'state'],
            },
    },

dialogue_act_definitions
-----------------
This section used for defining dialogue acts may be issued by a user simulator such as ``inform``, ``affirm`` and so on. The name of act will be the key of this dict and the definition of an act is also a python dict which may combine one or many keys listed below:

- ``slot_included``: A boolean value indicating this action will contain slot or not.
- ``value_included``: Similarly, a boolean value indicating this action will enclose a value for each slot or not.
- ``slot_from``: A string could be ``sys_da`` or ``none`` indicating slots for this action will be take from system dialogue act or nowhere, respectively.
- ``value_from``: A string could be either ``sys_da``, ``goal`` or ``function`` pointing out the source of slot values are respectively from system dialogue act, final goal or dynamicaly caculated by a function.
- ``combineable_slots``: A list of slots which could be combined with this action, but these slots is probably not appear in system dialogue act or final goal.
- ``limited_slots``: A list of slots which can't be used with this action.
- ``accept_used_slots``: A boolean flag, set to ``false``  indicating this action will not accept slots which are already used by this action in previous turn. Of course, the ``slot_from`` key has higher priority, which means slots getting from the source indicated in ``slot_from`` will be kept.
- ``use_slot_sequence``: A boolean value setting whether this action uses ``slot_used_sequence`` defined in the current goal or not.
- ``act_without_slot``: A true/false value indicating this action can be built and used in a conversation even that there is no any slot combineable with it, *silence* and *oog* are some those. 
- ``status_included``: A string could be either *correct* or *incorrect*, this property is used for filtering slots by their status. In other words, it can accept only slots which have the same values with the goal (correct), or have a status of deffirent to the goal (incorrect).
- ``add_to_da_prob``: A real number in [0, 1] indicating the probability of adding this action to dialogue action. Sometimes, an action can be optional for the final return dialgoue act, for examples, say *hello* to a system or say *yes* for an implicit confirm from a system.
- ``status_in_all_slots``: A boolean value indicating all slots combinable with this action must have the same status. This property is used in the combination with the property ``status_included``.
- ``value_fun``: A pointer to a function, being used to combine with ``value_from=fun``.

Here is one example defining three acts *silence*, *inform* and *affirm*:

::

    dialogue_act_definitions': {
        'silence':{
                    'slot_included': False,
                    'value_included': False,
                    'act_without_slot': True,
                },
        'inform':{
                    'slot_included': True,
                    'value_included': True,
                    'slot_from': 'sys_da', 
                    'value_from': 'goal', 
                    'accept_used_slots': False,
                    'use_slot_sequence': True,
                },
        'affirm':{
                    'slot_included': False,
                    'value_included': False,
                    'slot_from': 'sys_da',
                    'status_included': 'correct',
                    'status_in_all_slots': True,
                },
    }, 

reply_system_acts
-----------------
We have to define how the user may answer every system act in this section. For that purpose, each system act will be a key in this dict and the value of each key will be a definition of the answer for that action. We used a list of dicts for listing all alternative ways for answering the sytem action. In each dict, we have a key ``active_prob`` presenting the chance of the answer will be chosen to reply this action.
Apart from this general definition rule, there are three different ways of defining how the user may answer a system dialogue act. For convient, let call them as ``standard_answer``, ``conditional_answer`` and ``goal_based_answer``.

Let start with ``standard_answer``, the dict will includes a key, named ``return_acts``, which is a list containing one or many act names defined in the section ``dialogue_act_definitions``. All of these acts will be built and used for replying the system act received.
Addition to this, we can refine every act in the list by complementing two extra sets of properties, the keys are combination of (action name) and ``_answer_types`` and (action name) and ``_overridden_properties``. In the formmer refinement, we may define a distribtuion of differnt answer types like *direct_answer*, *over_answer* and *complete_answer*. 
For the later refinement, we can set new value for any default property of the action which already defined in the section ``dialogue_act_definitions``, or we may also add more properties for the action reinforcing exclusively the way of handling the system act.

The below is an example showing a definition of the answer for replying *request* act.

::
    
    'reply_system_acts':{
                'request':[ {   'return_acts':['inform'],
                                'inform_answer_types':{
                                    'direct_answer':0.7,
                                    'over_answer':0.25,
                                    'complete_answer':0.05,
                                },
                                'inform_overridden_properties':{
                                    'use_slot_sequence': False,
                                },
                                'active_prob':0.85,
                            },#the first answer

                            {   'return_acts':['silence'],
                                'active_prob':0.05,
                            },#end of the first alternative answer

                            {   'return_acts':['oog'],
                                'active_prob':0.1,
                            },# end of the second alternative answer
                        ],
    },

Now we are moving to the second type of answer definition, ``conditional_answer``. In this type, intead of using the key ``return_acts``, we define the key,  ``oredered_return_acts``, which is a list of dict as normal. Each element (a dict) represents a way of answer, but the difference is that the user simulator will try these answer by their order. Which means the later ones are using only if all of previous ones failed to apply. For supporting many alternative ways in each answer, we must define each way in a dict which is very similar to ``standard_answer``. Let look at the example below, a definition of how the user simulator will reply the *confirm* act from a system.

::

    'reply_system_acts':{
        'confirm':[ {
                        'ordered_return_acts':[
                                {   'case1':{'return_acts':['affirm'],
                                        'active_prob':0.5
                                    },
                                    'case2':{'return_acts':['affirm', 'inform'],
                                        'active_prob':0.5,
                                        'inform_answer_types':{
                                            'over_answer':1.0
                                        },
                                        'inform_overridden_properties':{
                                            'slot_from': 'none',
                                        },
                                    },
                                },#end of first priority answer
                                {   'case1':{'return_acts':['negate', 'inform'],
                                        'active_prob':0.4,
                                        'inform_answer_types':{
                                            'direct_answer':1.0,
                                        },
                                        'inform_overridden_properties':{
                                            'status_included': 'incorrect',
                                            'value_from': 'goal',
                                            'use_slot_sequence': False,
                                        },
                                    },
                                    'case2':{'return_acts':['deny'],
                                        'active_prob':0.2,
                                    },
                                    'case3':{'return_acts':['deny', 'inform'],
                                        'active_prob':0.4,
                                        'inform_overridden_properties':{
                                            'status_included': 'incorrect',
                                            'value_from': 'goal',
                                            'use_slot_sequence': False
                                        },
                                    },
                                }#end of seond priority answer
                        ],    
                        'active_prob':1.0,
                    },#end of the firs way of answer
                ],
    }

The last answer type is ``goal_based_answer``, it is conditioned on which final goal currently being actived to make a reply. At the begining it is somewhat different from two cases above, instead of defining a list of dict, we defines a dict containing keys are indexs (0, 1, etc.) presenting the answer will be used respectively with the index of the current goal (0, 1 or etc.). 
The value for each key is a list of dict as normal as two first types of answer. Which mean an answer for a specific goal could be described as a ``standard_answer`` or a ``conditional_answer``. Look at the code below for an example.

::

    'reply_system_acts':{
        'offer':{
                    0:[{'return_acts':['bye'],#definition for goal_id=0 - the first goal in the goal list
                        'active_prob':0.2,
                        },
                        {'return_acts':['request'],
                        'active_prob':0.2,
                        },
                        {'return_acts':['reqalts'],
                        'active_prob':0.2,
                        },
                        {'return_acts':['thankyou'],
                        'active_prob':0.4,
                        },
                    ],
                    1:[{'return_acts':['bye'],
                        'active_prob':0.5,
                        },
                        {'return_acts':['thankyou'],
                        'active_prob':0.5,
                        },
                    ],
        },
    },

data_observation_probability
-----------------
This section is an optional using for defining probability of data occurrence in user's random final goals. Each key of this dict will be a table name which we wish to define occurring frequency for its data rows. We use a tuple containing values in a row as keys in a sub dict for pointing out its chance of taking stage. You may also provide probability only for several rows in a table, other rows is automatically sharing the remaining mass.

The following is an example showing a definition of data observation probability for two tables, *time_relative* and *places*.

::

    'data_observation_probability':{
                'time_relative':{
                    ('as soon as possible',):0.2,
                    ('next hour',):0.1,
                    ('morning',):0.1,
                    ('noon',):0.1,
                    ('afternoon',):0.1,
                    ('night',):0.1,
                    ('midnight',):0.05,
                    ('early morning',):0.05,
                    ('today',):0.1,
                    ('tomorrow',):0.05,
                    ('the day after tomorrow',):0.05,
                },
                'places':{
                    ('first stop', 'rose street', 'flower city', 'New York'):0.3,
                },
    },

Examples
----------------
There are two examples provided in the folder demos. As already mentioned, one is a user simulator for appointment scheduling app (``demos/scheduler``), and another is for public transport information system (``demos/ptien``). You could run these examples by executing the file ``main.py`` which is provided in each directory.

All configuration for deploying the user simulator in the first example, scheduler, is in the file ``demos/scheduler/scheduler_simulator.cfg``. This application includes one slot, *decision*, which may recieve three values (*accept*, *delay* and  *reject*) which is provided by a function. There are also three acts which the user may choose to answer system *request* act. The results of executing the example will be similar as below:

::

    ------------------------------------------------------------
    Goal: {'decision': 'accept'}
    ------------------------------------------------------------
    sys_da:         inform(appointment="Thanh visits on Monday")&request(decision)
    user_da:        inform(decision="accept")       [last sys_da reward=-1]
    sys_da:         request(decision)
    user_da:        silence()                       [last sys_da reward=-1]
    sys_da:         request(decision)
    user_da:        inform(decision="accept")       [last sys_da reward=-1]
    sys_da:         accept(appointment="Thanh visits on Monday")
    user_da:        end()                           [last sys_da reward=-1]
    Final reward:   20
    
You may also find a similar structure for the second sample, public transport information system. Addition to this, in the directory ``test``, there is also a kind of random tests generating goals and dialogues for this example. When you deploy a new user simulator, you might refer to the test as a way of guaranteeing the user developed working correctly.

License
-------
This code is released under the APACHE 2.0 license unless the code says otherwise and its license does not allow re-licensing.
The full wording of the APACHE 2.0 license can be found in the LICENSE-APACHE-2.0.TXT.
