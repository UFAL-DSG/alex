.. image:: ../../../../alex/doc/alex-logo.png
    :alt: Alex logo

Error simulator for ASR and SLU
===============================

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
This module is dedicated to simulate errors in Automatic Speech Recognision (ASR) and Spoken Lanugage Understanding (SLU). Currenly, this module contains only a ``SimpleASRSimulator`` which sample N-best SLU hypotheses by simulating noise adding to the correct user dialogue acts.
In this document we quickly describe the ASR simulator and also provide examples of how it could be used.

Overview
-----------------
The ASR error simulator is simple working as sampling randomly a list of alternative dialouge act items, and then sample suitably a list of probabilities correspongding to the list of alternative values.

In the ``SimpleASRSimualtor``, we currently support four types of generating the N-best list hypotheses:

- ``correct``: The user intent is kept corretly, which means the correct dialogue acts get the highest probability becoming the first item in the list of hypotheses.
- ``onlist``: The user intent is also kept in the N-best list hypotheses, but it is not in the top position and get a humble probability in the N-best list.
- ``offlist``: The user itent is confused out of the N-best hypotheses.
- ``silence``: All of user utterances will be eliminated completely, results in a slient act.

The confused values is fetching from an instance of the ``PythonDatabase``, refer to the user simulator guide for how to use the database object and a general configuration used in the Alex framwork. All confusion setting is coded in a configuration file which is described in next section.

Configurations
-----------------
A typical configuration for the ``SimpleASRSimulator``, like in user simulator, is also a python dict containing some sections as following:

::

    'asr_simulator:{
        'SimpleUserSimulator':{
            'prob_combine_fun': product_fun,
            'act_confusion':{
                ... ...
            },
            'slot_confusion':{
                ... ...
            },
            'slot_name':{
                ... ...
            },
        },
    }

In which:

- ``prob_combine_fun``: A function pointer, which refers to a function with two arguments defining how the joint probability of two events could be calculated from the probability of each event, (e.g. multiplication for two independent events). The function  will be used to combine the probability of action type, slots and values.
- ``act_confusion``: A python dict describing how user acts could be confused.
- ``slot_confusion``: A python dict describing which slots could be observed given the correct slot in the user utterance.
- ``slot_name``: The key ``slot_name`` will be changed to the name of a slot to defining how the slot values could be confused.

Each of these sections will be disccused in a separated section below.

act_confusion
----------------
Each key in this dict will be the name of action type which we would like to define how it would be confused. One interesting point is that we could define the key ``default`` which will apply to all action types without a specific confusing definition. The structure of defining the confusion for an action type looks like following:

::

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
                                'correct':6.0, 
                                'onlist': 1.0, 
                                'offlist': 0.0, 
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

We can see that all confuguration for an act (here is ``default``) is given in a dict named ``confusion_matrix``. 

- ``max_length``: An integer, specifying the maximum length of the N-best list.
- ``confusable_acts``: A list, listing all acts could be confused by the action (here is ``default``).
- ``onlist_fraction_alpha``: A real number, a parameter for beta distribution generating the correct position and probability fractions in N-best hypotheses.
- ``onlist_fraction_beta``: A real number, a parameter for beta distribution generating the correct position and probability fractions in N-best hypotheses.
- ``confusion_types``: A python dict, defining the distribution of four confusing types as mentioned at beginning.
- ``probability_generator``: A dict, specifying parameters for the Dirichlet distribution generating probability for the N-best list for each type of confusion.

Another interesting point is that, for definition of an act type, we could define only properties which are different from the ``default``, other properties without definition will automatically recieve from the ``default`` one.

slot_confusion
----------------
We define confusion for a slot  by adding the slot name to the dict. One example is given below:

::

            'slot_confusion':{
                'to_stop':{
                    'to_stop': 0.5,
                    ('departure', 'arrival'): 0.5,
                },
            },

We could simple list all cases of confusing and their corresponding active probabilities. In the case of confusing into more than one slots at one time, just list all of them in a tuple.

slot_name
----------------
The confusing definition for slot is very similar to the definition for acts, except that you may also define a refined verion for a specific act. For example, in definition below, we defined a refinement which will be applied when the slot (here is ``default``) being used in the act ``inform``. The refinement is pointed out bye a key ``act_type`` + ``_confusion_matrix`` (in this example is ``inform_confusion_matrix``)

::

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
                            'correct':6.0, 
                            'onlist': 1.0, 
                            'offlist': 3.0, 
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
                'inform_confusion_matrix':{#a refined confusion matrix for inform action
                    'confusion_types':{
                        'correct': 0.8,
                        'onlist': 0.15,
                        'offlist': 0.05,
                    },
                    #the default_prob.generator is missing the default one should be used
                },
            },#end of the default consusion for all slots

Examples
----------------
There are one example provided in the folder ``demos/ptien``. You could run the example by executing the file ``main.py``, it will simulate n-best hypothese for the dialogue act ``inform(to_stop=Central Park)``. The results should be similar as following:

::

    --Simulate da_item: inform(to_stop="Central Park")
    -------------------- da_items
    0.392 inform(to_stop="Minnehaha Blvd At River Dr#")
    0.279 inform(to_stop="Central Park")
    0.103 inform(to_stop="Brightwood Ave At Prospect St#")
    -------------------- nblist =
    0.393531968389  null()
    0.253274673808  inform(to_stop="Minnehaha Blvd At River Dr#")
    0.152073781423  inform(to_stop="Central Park")
    0.097873719236  inform(to_stop="Minnehaha Blvd At River Dr#")&inform(to_stop="Central Park")
    0.045308455738  inform(to_stop="Brightwood Ave At Prospect St#")
    0.029160234160  inform(to_stop="Minnehaha Blvd At River Dr#")&inform(to_stop="Brightwood Ave At Prospect St#")
    0.017508687344  inform(to_stop="Central Park")&inform(to_stop="Brightwood Ave At Prospect St#")
    0.011268479900  inform(to_stop="Minnehaha Blvd At River Dr#")&inform(to_stop="Central Park")&inform(to_stop="Brightwood Ave At Prospect St#")
    -------------------- best hyp=
    0.394 null()
    -------------------- best hyp non null=
    inform(to_stop="Minnehaha Blvd At River Dr#")

License
-------
This code is released under the APACHE 2.0 license unless the code says otherwise and its license does not allow re-licensing.
The full wording of the APACHE 2.0 license can be found in the LICENSE-APACHE-2.0.TXT.
