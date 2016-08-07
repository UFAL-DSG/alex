import autopath
from alex.utils.config import Config
from alex.utils.database.python_database import PythonDatabase
from alex.components.simulator.user_simulator.simple_user_simulator import SimpleUserSimulator
from alex.components.slu.da import DialogueActItem, DialogueAct
from alex.utils.sample_distribution import sample_from_list, sample_a_prob
from alex.utils.support_functions import iprint

cfg = None

def get_config():
    global cfg
    cfg = Config.load_configs(['../demos/ptien/simulator.cfg', '../demos/ptien/ptien_metadata.py'], log=False)

def test_user_goal(user, n):
    for i in range(n):
        user.new_dialogue()
        print '-------------------------Goal %d (type=%d)---------------------'%(i+1, user.goal_id+1)
        iprint(user.goal)
        user.end_dialogue()

def test_reply(user):
    user.new_dialogue()
    print 'GOAL', user.goal
    act_type = 'implconfirm'
    slots = ['from_stop', 'from_street', 'from_city']
    act_slot = None
    act_value = None
    for slot in slots:
        if slot in user.goal.keys():
            act_slot = slot
            act_value = user.goal[slot]
            break
    act_value='abc'
    da = DialogueAct()
    item = DialogueActItem(act_type, act_slot, act_value)
    da.append(item)
    item = DialogueActItem('request', 'to_stop')
    da.append(item)
    print 'sys_da:', da
    user.da_in(da)
    dao = user.da_out()
    print 'user_da:', dao[0]

def get_metadata():
    metadata = {
        'goals':{
            'find_connection':{
                'slots': ['task', 'from_stop', 'to_stop', 'arrival_time', 'vehicle'],
                'acts': ['hello', 'request', 'confirm', 'request', 'implconfirm&request', 'request', 'confirm', 'offer', 'bye',],
                'equivalent_slots':[('from_stop', 'from_city', 'from_street'), ('to_stop', 'to_city', 'to_street'),
                                        ('arrival_time', 'arrival_time_rel'), ('departure_time', 'departure_time_rel'),
                                ],
            },
            'find_platform':{
                'slots': ['task', 'street', 'city', 'state'],
                'acts': ['hello', 'request', 'confirm', 'request', 'offer', 'bye'],
            },
            'weather':{
                'slots': ['task', 'city', 'state'],
                'acts': ['hello', 'request', 'implconfirm&request', 'offer', 'bye'],
            }
        },
        'act_definitions':{
            'hello':{
                'slot_included': False,
                'value_included': False,
            },
            'request':{
                'slot_included': True,
                'value_included': False,
            },
            'confirm':{
                'slot_included': True,
                'value_included': True,
            },
            'implconfirm':{
                'slot_included': True,
                'value_included': True,
            },
            'offer':{
                'slot_included': True,
                'value_included': True,
            },
            'bye':{
                'slot_included': False,
                'value_included': False,
            },
        },
    }
    return metadata

def get_equivalent_slots(goal_des, slot,):
    if 'equivalent_slots' in goal_des:
        for eq_slots in goal_des['equivalent_slots']:
            if slot in eq_slots:
                return eq_slots
    return ()

def test_random_dialogues(user):
    metadata = get_metadata()
    for i in range(100):
        print '=======================Dialogue %i============================'%(i+1)
        user.new_dialogue()
        print 'Goal:', user.goal
        print '-'*60
        goal_des = metadata['goals'][user.goal['task']]
        ordered_acts = goal_des['acts']
        slots = goal_des['slots']
        for acts in ordered_acts:
            da = DialogueAct()
            for act in acts.split('&'):
                act_des = metadata['act_definitions'][act]
                slot = None
                if act_des['slot_included']:
                    slot = sample_from_list(slots)
                value = None
                if act_des['value_included']:
                    if slot not in user.goal.keys():
                        for s in get_equivalent_slots(goal_des, slot):
                            if s in user.goal.keys():
                                slot = s
                                break
                    if slot in user.goal.keys():
                        if sample_a_prob(0.5):
                            value = user.goal[slot]
                        else:
                            value = 'lct'
                    else:
                        value = 'lct'

                item = DialogueActItem(act, slot, value)
                da.append(item)
            print 'sys_da:\t\t', da
            user.da_in(da)
            da = user.da_out()
            print 'user_da:\t', da[0]
            if len(da[0])==0:
                raise RuntimeError('User simulator doesnt reply anything!!')
                pdb.set_trace()

def run1():
    db = PythonDatabase(cfg)
    user = SimpleUserSimulator(cfg, db)
    #test_user_goal(user, 100)
    #test_reply(user)
    test_random_dialogues(user)

def main():
    get_config()
    run1()

if __name__ == '__main__':
    main()




