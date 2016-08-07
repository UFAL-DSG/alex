import random

from alex.components.simulator.base import UserSimulator
from alex.utils.database.python_database import PythonDatabase
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork, DialogueAct

from alex.utils.sample_distribution import sample_from_list, sample_from_dict, random_filter_list, sample_a_prob
import alex.utils.matlab_functions as matlab
from alex.utils.support_functions import get_dict_value, iscallable, iprint, deep_copy

class SimpleUserSimulator(UserSimulator):
    '''Simulating an user for slot-filling spoken dialogue system.
    
    Based on a domain definitions, a database and other configurations,
    the user simulator chooses randomly a final goal and make conversation
    reponsing to system acts suitablely with the current goal picked out.
   
    The domain definitons and the database are pointed out by the Config module,
    It is also included in the framework.    

    Attributes:
        metadata: A dictionary describes a domain which user make conversations.
        goal_id: An interger indicating the index of the current goal chosen.
        goal: A dictionary present the current goal with slots filled.
        db: The object connects to database.
        config: The Config object save all configurations.
        logger: The logger of the class.
        turns: A list of dict presenting the history of the current conversation, each dict includes sys_da and user_da

    More details are available at https://github.com/thanhlct/alex/tree/user_simulator/alex/components/simulator/user_simulator
    '''

    def __init__(self, cfg, db):
        '''Create a new SimpleUserSimulator object and init core elements.

        Args:
            cfg: A config object contains domain definitions and other configurations.
            db: A object connects to database.
        '''
        self._config = cfg.config['user_simulator']
        self.system_logger = cfg['Logging']['system_logger']
        self.db = db
        self.goal = None
        self.turns = []
        self._name = self.__class__.__name__
        self.metadata = self._config[self._name]['metadata']
        #self.metadata = self.get_metadata(self.config)
        #self._goal_dist = self._get_goal_distribution()
        self._goal_dist = self._get_dict_distribution(self.metadata['goals'])

        self.config = self._config[self._name]
        self.patience_level = 0
        if 'patience_level' in self.config.keys():
            self.patience_level = self.config['patience_level']

        self.last_user_da = None

    def _get_dict_distribution(self, lst_dict):
        '''Get dict distribution for a list of dictionary or a dictionary of dictionary
        
        Args:
            lst_dict: A list or dict of dictionary, in which each dictionary contains the key active_Prob specifying the change cof it being active
        '''
        d = {}
        if isinstance(lst_dict, dict):
            for key in lst_dict.keys():
                d[key] = lst_dict[key]['active_prob']
        else:
            for i in range(len(lst_dict)):
                d[i] = lst_dict[i]['active_prob']
        return d

    def new_dialogue(self):
        '''Start a new dialogue.

        Sample a new user goal and reset everything for simulating a new dialogue.
        '''
        self.goal = self._get_random_goal()
        self.slot_level = self._build_slot_level()
        #self.dialog_turns = [] make the full history in somewhere else, not the task of user simulator
        self.unprocessed_da_queue = []
        self.act_used_slots = {}
        self.slot_level_used = 0
        self.turns = []
        self.patience_history= {}

        self.system_logger.info("SimpleUserSimulator: GOAL: %s"%self.goal)
 
        #Sample patience level, since different user will have a different level
        if 'patience_levels' in self.config.keys():
            self.patience_level = sample_from_dict(self.config['patience_levels'])
            print '---Patience - level: ', self.patience_level

        self.last_user_da = None
       

    def _build_slot_level(self):
        '''Return dict of slot level.

        Build mapping between slot and its used sequence level
        from slot_used_sequence defined in self.metadata

        Returns:
            A dict mapping slots to the coreponding slot level.
        '''
        d = {}
        goal_des = self.metadata['goals'][self.goal_id]
        if 'slot_used_sequence' in goal_des.keys():
            slot_used_sequence = goal_des['slot_used_sequence']
            for key in slot_used_sequence.keys():
                for slot in slot_used_sequence[key]:
                    d[slot] = key
        return d           

    def _get_random_goal(self):
        '''Sample a final goal of user.

        Returns:
            A dict represent slots and their values sampled.
        '''
        self.goal_id = sample_from_dict(self._goal_dist)
        goal_des = self.metadata['goals'][self.goal_id]
        goal = {}
        self.goal = goal
        sampled_slots = []

        for s, v in goal_des['fixed_slots']:#fixed slots
            goal[s] = v
            sampled_slots.append(s)

        for key in goal_des['same_table_slot_keys']:#same table slots NOTE same_table_slot was coded without testing since data hadn't faked yet
            slots_values = self._get_random_same_table_slots_values(key)
            for slot in slots_values.keys():
                if slot in goal_des['changeable_slots']:
                    sampled_slots.append(slot)
                    goal[slot] = slots_values[slot]

        for one_set in goal_des['one_of_slot_set']:#get value for  one slot set and ignore other slots
            slot_set = sample_from_dict(one_set)
            for slot in slot_set:
                goal[slot] = self._get_random_slot_value(slot)
            for key in one_set.keys():
                sampled_slots.extend(key)

        sampled_slots.extend(goal_des['sys_unaskable_slots'])
        remain_slots = matlab.subtract(goal_des['changeable_slots'], sampled_slots)
        for slot in remain_slots:#changeable slots
            goal[slot] = self._get_random_slot_value(slot)

        '''Don't fill default slots, only return when system ask
        for slot, value in goal_des['default_slots_values']:#fill the default slot which was not being filled
            if slot not in goal.keys():
                goal[slot] = value
        '''
    
        fun = get_dict_value(goal_des,'goal_post_process_fun')
        if fun is not None:
            #goal = fun(self, goal)
            goal = fun(goal)

        #for debug:
        #self.goal_id = 0
        #goal = {'to_city': u'Allerton', 'task': 'find_connection', 'from_city': u'North Massapequa',}
        return goal

    def _get_random_same_table_slots_values(self, same_table_key):
        '''Find randomly values from the same row for a set of slots.

        Args:
            same_table_key: The key refers to same table definitions.

        Returns:
            A dict mapping slots and values
        '''
        same = self.metadata['same_table_slots'][same_table_key]
        table = same['table']
        row = self._get_random_row(table)
        sv = {}
        for slot in same['slots']:
            field = self._get_field_name(slot, table)
            sv[slot]= self.db.get_row_field_value(table, row, field)
        return sv

    def _get_random_slot_value(self, slot):
        '''Get a random value for the given slot.'''
        values = []
        tables_fields = self._get_slot_mapping(slot)
        for tbf in tables_fields:#sample a value of each table which the slot is connected
            if iscallable(tbf):#slot have values generated dynamic from one or several funs
                v = sample_from_list(tbf(self.goal, slot))
                values.append(v)
            else:  
                tb, f = tbf
                row = self._get_random_row(tb)
                values.append(self.db.get_row_field_value(tb, row, f))
        return sample_from_list(values)#take one in the sampled values
        
    def _get_random_row(self, table):
        '''Get a random row for the given table.'''
        if table in self.metadata['data_observation_probability'].keys():
            data_dist = self._get_data_distribution(table)
            return sample_from_dict(data_dist)
        else:
            return self.db.get_random_row(table)

    def _get_data_distribution(self, table):
        '''Build dict presenting data observation distribution for a table.

        The observation distribution can be defined in the metadata or
        keep as default - all row has the same probability of ocurring.

        Args:
            table: The name of a table

        Returns:
            A dict mapping each row in the table with a observation probability
        '''
        dist = {}
        tb_dist = self.metadata['data_observation_probability'][table]
        predifined_mass = 0.0
        predifined_row = 0
        for key in tb_dist.keys():
            predifined_mass += tb_dist[key]
            predifined_row += 1
        
        remaining_mass = 1.0 - predifined_mass
        remaining_row = self.db.get_row_number(table) - predifined_row
        default_prob = 0
        if remaining_row>0:
            default_prob = remaining_mass/remaining_row

        for row in self.db.get_row_iterator(table):
            if row in tb_dist.keys():
                dist[row] = tb_dist[row]
            else:
                dist[row] = default_prob
        return dist
        
    def _get_field_name(self, slot, table):
        '''Return field in the table which mapped to values for the given slot.'''
        mapping = self._get_slot_mapping(slot)
        for tb, f in mapping:
            if tb==table:
                return f
        assert False, "There is no table=%s in the slot_table_field_mapping definition of the slot=%s"%(table, slot)
    def _get_slot_mapping(self, slot):
        '''Return a full set of table field mapping for the given slot.'''
        assert slot in self.metadata['slot_table_field_mapping'].keys(), "Have not defined the slot_table_field_mapping for the slot=%s"%(slot)
        return self.metadata['slot_table_field_mapping'][slot]  

    def da_in(self, da):
        '''Recieve a system dialogue act.

        Args:
            da: A DialogueAct object presents system acts
        '''
        assert self.goal is not None, 'user simulator has no goal, you have to call new_dialogue building goal first before make conversation'
        self.unprocessed_da_queue.append(da)

        self.system_logger.info('SimpleUserSimulator:da_in: %s'%da)

    def da_out(self):
        '''Answer unprocessed system dialogue act so far.

        Returns:
            A list of DialogueAct presents answers of user
        '''
        das = []
        turn = {'sys_da': deep_copy(self.unprocessed_da_queue)}
        while(len(self.unprocessed_da_queue)>0):
            da = self.unprocessed_da_queue.pop(0)
            #das.append(self._get_answer_da(da))
            da_ret = self._get_answer_da(da)
            if len(da_ret)>0:
                das.append(da_ret)

        if len(das)==0:
            print '!!!!!!!!!!!!!!!!Empty acts return?????? change to default fixed slots value act!!!!'
            das = self._zero_act_return()
        #if len(das)==1:
        #    das = das[0]
        #print das[0]
        
        #post process user acts
        goal_des = self.metadata['goals'][self.goal_id]
        if 'act_post_process_fun' in goal_des and goal_des['act_post_process_fun'] is not None:
            das = goal_des['act_post_process_fun'](das)

        turn['user_da']= das
        self.turns.append(turn)

        self.last_user_da = das[0].dais
      
        das_str = ''
        #for da in das:
            #das_str += str(da)
        #self.system_logger.info('SimpleUserSimulator:da_out: %s'%das_str)
        return das

    def _zero_act_return(self):
        da = DialogueAct()
        fixed_slots_values = self.metadata['goals'][self.goal_id]['fixed_slots']
        for s, v in fixed_slots_values:
            da.append(DialogueActItem('inform', s, v))

        if self.slot_level_used == 0:
            self.slot_level_used = 1

        return [da]
 
    def _get_answer_da(self, da_in):
        '''Answer a sytem dialogue act.'''
        da_out = DialogueAct()
        out_of_patience=False

        reply_sys_acts = self.metadata['reply_system_acts']
        da_metadata = self._get_dialogue_act_metadata(da_in)
        for act_in in da_metadata.keys():
            #debug_print('------Handling the sys_act' +  act_in)
            #print '------Handling the sys_act', act_in
            reply = reply_sys_acts[act_in]
            if isinstance(reply, dict):#this action has different definition for different goal
                reply = reply[self.goal_id]
            answer = self._sample_element_from_list_dict(reply)
            if 'ordered_return_acts' in answer:#process list of answer in order, and stop for first appliable
                for solution in answer['ordered_return_acts']:
                    case = self._sample_element_from_list_dict(solution)
                    da_items = self._build_one_answer(da_metadata[act_in], case, True)
                    if len(da_items)>0:
                        answer = case# for filtering acts with add_to_da_prob propertiy
                        break
            else:
                da_items = self._build_one_answer(da_metadata[act_in], answer)
                
            for item in da_items:#process action can be whether add to da_out or not like impl_confirmi
                act_out_des = self._get_act_out_description(item.dat, answer)
                if 'add_to_da_prob' in act_out_des.keys():
                    if sample_a_prob(act_out_des['add_to_da_prob']) and item not in da_out:
                        da_out.append(item)
                else:
                    if item not in da_out:
                        da_out.append(item)
                #-------update patience history
                if item.name is not None:#have slot, the sys act ask repeated the sema slot anserd, ignore the case of over answer
                    if act_in not in self.patience_history.keys():
                        self.patience_history[act_in] = {}
                    if item.name not in self.patience_history[act_in]:
                        self.patience_history[act_in][item.name]=1
                    else:
                        self.patience_history[act_in][item.name]+=1
                        if self.patience_level>=1 and self.patience_history[act_in][item.name]>self.patience_level:
                            out_of_patience = True
                            break#only break the inner loop
            #da_out.extend(da_items)
        if out_of_patience:
            if random.random()>0.5:
                da_out = DialogueAct(self.config['out_of_patience_act'])
                print '!!!!ANGRY...'
            else:
                print '!!Almost ANGRY...'
        return da_out

    def _get_act_out_description(self, act_out, specific_answer):
        '''Get user action definitions.
        
        Combining the default act deifintion with a specific answer act.
    
        Args:
            act_out: The name of answer act (e.g. inform, affirm)
            specific_answer: The definition of in a specific case
                            (e.g. includes refined setting inform_answer_types:{...}, inform_overridden_properties:{...}.

        Returns:
            A dict of descriptions for the given act_out
        '''
        act_out_des = self.metadata['dialogue_act_definitions'][act_out]
        if act_out + '_overridden_properties' in specific_answer.keys():
            act_out_des = self._override_act_descriptions(specific_answer[act_out + '_overridden_properties'], act_out_des)
        return act_out_des
        

    def _build_one_answer(self, da_metadata, answer, follow_order=False):
        '''Build a full answer to a system act.

        Args:
            da_metadata: a dict contains only description of system act such as slots-values.
            answer: a dic full description of answer act.
            follow_order: a boolean specifying the first return act need to be satisfied or cancel completely the answer.

        Returns:
            A list of DialogueActItem object.
        '''
        #print answer
        da_items = []
        new_items = []
        first_act = True
        for act_out in answer['return_acts']:#for reply without ordered answer
            #New for repeat
            if act_out == 'repeat':
                da_items.extend(self.last_user_da)#add previous act, may add more if we use inform in return_acts
                continue
            
            answer_types = get_dict_value(answer, act_out + '_answer_types')
            answer_type = None
            if answer_types is not None:
                answer_type = sample_from_dict(answer_types)
            overridden_properties = get_dict_value(answer, act_out + '_overridden_properties')
            #da_items.extend(self._build_dialogue_act_items(da_metadata, act_out, answer_type, overridden_properties))
            new_items = self._build_dialogue_act_items(da_metadata, act_out, answer_type, overridden_properties)
            da_items.extend(new_items)

            if follow_order and 'all_act_valid' in answer.keys() and answer['all_act_valid']==True:#this case of this answer requires all acts must appliabl
                if len(new_items)==0:
                    da_items = []#cancel all other da item already build, that will move to next case of anser
                    break 
            if first_act and follow_order:#if the first action in a return actions which follows the order not successful, that case not satisfy, give up
                first_act=False
                if len(da_items)==0:
                    break
        return da_items

    def _sample_element_from_list_dict(self, lst_dict):#should be static or class function, but this way potential for future speeup with caching
        '''Sample an element in a list based on its active probability.

        Args:
            lst_dict: A list of dict, in which each dict contains the key, active_prob,  presenting the observation probably.

        Returns:
            A dict from the given list.
        '''
        dist = self._get_dict_distribution(lst_dict)
        index = sample_from_dict(dist)
        return lst_dict[index]
        
    def _get_dialogue_act_metadata(self, da):
        '''Return metadata describe the dialogue act given.
            
        Returns:
            A dict presenting statistical info about all slots, values used for each action in the given da.
        '''
        d = {}
        for item in da:
            act = item.dat
            slot = item.name
            value = item.value
            if act in d.keys():
                d[act]['slots'].append(slot)
                d[act]['values'].append(value)
                d[act]['slot_value'][slot] = value
            else:
                d[act] = {
                    'slots': [slot],
                    'values': [value],
                    'slot_value': {slot:value},
                }
        return d
                
    def _build_dialogue_act_items(self, act_in, act_out, answer_type, overridden_properties):
        '''Build return acts for a type of answer act.

        Args:
            act_in: The metadata presenting the system act such as slots-values
            act_out: A string figure out the type of answer act such as inform or affirm
            answer_type: A string describe answer type which can be whether direct answer, over answer or complete answer.
            overridden_properties: A dict of properties which will used to override the default setting of return act.

        Returns:
            A list of DialogueActItem object.

        Raises:
            RuntiemError: Cant find value for a slot which requires, in setting, a value must be filled.
            NotImplementedError: The source providing value for a slot was not implemented.
        '''
        #print act_in
        #print '---building', act_out
        #print answer_type
        if act_out not in self.act_used_slots.keys():#saving this action used this slot
            self.act_used_slots[act_out] = set()

        act_out_des = self.metadata['dialogue_act_definitions'][act_out]
        act_out_des = self._override_act_descriptions(overridden_properties, act_out_des)
        #print 'act_out_des_override'
        #iprint(act_out_des)
        da_items = []
        combined_slots = self._get_combined_slots(act_in, act_out_des, answer_type, self.act_used_slots[act_out])
        for slot in combined_slots:
            item = DialogueActItem()
            item.dat = act_out
            if act_out_des['slot_included']:
                item.name = slot
            if act_out_des['value_included']:
                if act_out_des['value_from']=='goal':
                    if slot not in self.goal.keys():#required slot not in goal
                        eq_slots = self._get_equivalent_slots(slot)
                        for s in eq_slots:#gen value from a equivalent slot
                            if s in self.goal.keys():
                                slot = s
                                break
                    if slot not in self.goal.keys():#dont have compatible slots, get from default values
                        value = self._get_default_slot_value(slot)
                        if value is not None:
                            item.value = value
                        else:
                            for s in eq_slots:#get default of equivalent slots
                                value = self._get_default_slot_value(s)
                                if value is not None:
                                    item.value = value
                                    item.name = s
                                    break
                            if item.value is None:
                                raise RuntimeError('Cant find value for slot %s and its equivalents slot from goal and default slots'%slot)
                    else:
                        item.value=self.goal[slot]
                        item.name = slot
                elif act_out_des['value_from']=='sys_da':
                    item.value = act_in['slot_value'][slot]
                elif act_out_des['value_from']=='function':
                    item.value = act_out_des['value_fun']()
                else:
                    raise NotImplementedError('value_from=%s unhandled yet'%act_out_des['value_from'])

            self.act_used_slots[act_out].add(slot)#save to the list of used slot for this act_out
                
            if item not in da_items:
                da_items.append(item)

        act_without_slot = False
        if 'act_without_slot' in act_out_des.keys() and act_out_des['act_without_slot']:
            act_without_slot = True
            da_items.append(DialogueActItem(act_out))
        
        if len(combined_slots)==0 and len(da_items)==0 and not act_without_slot:
            pass
            #print 'Not building act=%s since it requires slots and values but we cant find any slot, value for it'%act_out
            #raise RuntimeError('Cant find any slot, value for the given dialogue act, %s'%act_out)
        return da_items

    def _override_act_descriptions(self, new_des, original_des):
        '''Merge and override properties of two dicts.

        Args:
            new_des: A dict presenting new properties for overriding
            origianl_des: A dict which will be intergrated and overridden

        Returns:
            A dict of combining properties from two dict.
        '''
        original_des = deep_copy(original_des)
        if new_des is None:
            return original_des
        for key in new_des.keys():
            original_des[key] = new_des[key]
        return original_des

    def _get_default_slot_value(self, slot):
        '''Get default value for the given slot.'''
        goal_des = self.metadata['goals'][self.goal_id]
        for s , v in goal_des['default_slots_values']:
            if s==slot:
                return v
        return None

    def _get_equivalent_slots(self, slot):
        '''Get equivalent slots fro given slot.'''
        goal_des = self.metadata['goals'][self.goal_id]
        if 'equivalent_slots' in goal_des:
            for eq_slots in goal_des['equivalent_slots']:
                if slot in eq_slots:
                    return eq_slots
        return ()

    def _get_combined_slots(self, act_in, act_out_des, answer_type, used_slots):
        '''Find combineable slots for 

        Args:
            act_in: A dict presenting the metadata of system act.
            act_out_des: A dict describing the setting of answer act.
            answer_type: A string showing the type of answer such as direct_answer, over_answer
            used_slots: A list of slots which the act already used in previous turns.
        Returns:
            A list of combineable slots.

        Raises:
            NotImplementedError:    The source providing slots for the action was not implemented.
                                    Or the answer_type used was not implemented.
        '''
        #print 'get_combined_slot, act_in=', act_in, ' act_out_des=', act_out_des
        lst = []

        remain_slots = self.goal.keys()

        if 'combineable_slots' in act_out_des.keys():#figured out list of combineable slot in the config file, but still have to filter at status slot
            lst.extend(act_out_des['combineable_slots'])
            #return act_out_des['combineable_slots']
            remain_slots = act_out_des['combineable_slots']

        #print '--combined slots1', lst
        if 'accept_used_slots' in act_out_des.keys() and act_out_des['accept_used_slots']==False:#filter used slot
            remain_slots = matlab.subtract(remain_slots, used_slots)

        #print '--combined slots2', lst
        if 'slot_from' in act_out_des.keys():#take all slot in the type figured in slot_from
            if act_out_des['slot_from']=='sys_da':
                lst.extend(act_in['slots'])
            elif act_out_des['slot_from']=='none':
                pass#dont take slot from sys_da
            elif act_out_des['slot_from']=='goal':
                lst.extend(self.goal.keys())
            else:
                raise NotImplementedError('slot_from=%s unhandled yet'%act_out_des['slot_from'])
            
        #print '--combined slots3', lst
        #process answer_type
        if answer_type=='direct_answer':
            pass#every slot in sys_da already included
        elif answer_type=='over_answer':
            #only over or complete answer for slot not mentioned
            remain_slots = matlab.subtract(remain_slots, lst)
            lst.extend(random_filter_list(remain_slots))
        elif answer_type=='complete_answer':
            remain_slots = matlab.subtract(remain_slots, lst)
            lst.extend(remain_slots)
        elif answer_type is None:
            pass
        else:
            raise NotImplementedError('answer_type=%s unhandled yet'%answer_type)            


        #print '--combined slots4', lst
        #process litmited slots
        if 'limited_slots' in act_out_des.keys():
            limits = act_out_des['limited_slots']
            limits = matlab.subtract(limits, act_in['slots'])#limited slots will be used when system ask
            #lst = matlab.subtract(lst, act_out_des['limited_slots'])
            lst = matlab.subtract(lst, limits)

        #process status included
        if 'status_included' in act_out_des.keys():
            status_included = act_out_des['status_included']
            lst = self._filter_slot_status(act_in, lst, status_included)
        
        #print '--combined slots5', lst
        # the act required all its slot need to be have the same status
        if 'status_in_all_slots' in act_out_des.keys() and act_out_des['status_in_all_slots']:
            if len(lst)!= len(act_in['slots']):#TODO this way of testing may give trouble in some cases in future, but currently it works.
                lst = []#this action require all of requested slot must satisfy the given status

        #add atlesat slots
        if 'atleast_slots' in act_out_des.keys():
            for slot in act_out_des['atleast_slots']:
                if slot not in lst:
                    lst.append(slot)

        #process slot_used_sequence
        goal_des = self.metadata['goals'][self.goal_id]
        if 'slot_used_sequence' in goal_des.keys():
            use_sequence = get_dict_value(act_out_des, 'use_slot_sequence')
            if use_sequence is not None and use_sequence:#default dont using slot sequence 
                lst = self._filter_slot_used_sequence(goal_des['slot_used_sequence'], lst)

        #print '--combined slots', lst
        return lst

    def _filter_slot_used_sequence(self, sequence, lst_slots):
        '''Filter out slots which conflict with slot used sequence.

        Remove slots which is not appliable, which requires others slot have to be used in previous turns.

        Args:
            sequence: A dict presenting the sequence of using slot.
            lst_slots: A list of slots for filtering.

        Returns:
            A list of slots.
        '''
        #finding the higtest level can reach for the give lost
        old_level = self.slot_level_used
        while(True):
            if self.slot_level_used not in sequence.keys():
                break
            for slot in sequence[self.slot_level_used]:
                if slot in lst_slots:
                    self.slot_level_used+=1
                    break
            if old_level == self.slot_level_used:
                break
            old_level = self.slot_level_used

        #--filtering
        lst = []
        for slot in lst_slots:
            if slot in self.slot_level.keys() and self.slot_level[slot]>self.slot_level_used:
                continue
            lst.append(slot)
        return lst
                
    def _filter_slot_status(self, act_in, slots, status):
        '''Filter slots based on it status.
        
        Status of a slot can be correct or incorrect regarding user final goal.

        Args:
            act_in: A dict showing the metadata description of system dialogue act.
            slots: A list of slot for filtering.
            status: A string describing the slot status which will be kept.

        Returns:
            A list of slots.

        Raises:
            NotImplementedError: Status used was not implemented.
        '''
        if status=='all':
            return slots
        lst = []
        for s in slots:
            correct_value = self._get_slot_value(s)
            if status=='correct' and correct_value is not None and correct_value== act_in['slot_value'][s]:
                lst.append(s)
            elif status=='incorrect' and correct_value is not None and correct_value!= act_in['slot_value'][s]:
                lst.append(s)
            elif status=='unmentioned' and s not in act_in['slots']:#unmetioned in only this turn, not from begining
                '''
                not_found = True
                eq_slots = self._get_equivalent_slots(s)
                for eq_s in eq_slots:
                    if eq_s in act_in['slots']:
                        not_found = False
                        break
                if not_found:
                    lst.append(s)
                '''
                lst.append(s)
            else:
                if status not in ['correct', 'incorrect', 'unmentioned']:
                    raise NotImplementedError('status_included=%s unhandled yet'%status)
        return lst

    def _get_slot_value(self, slot):
        '''Get value describing user intention for the given slot.
        
        Raises:
            RuntimeError: Cant find value for the given slot.
        '''
        item = DialogueActItem()
        if slot in self.goal.keys():
            return self.goal[slot]
        if slot not in self.goal.keys():#required slot not in goal
            eq_slots = self._get_equivalent_slots(slot)
            for s in eq_slots:#gen value from a equivalent slot
                if s in self.goal.keys():
                    slot = s
                    break
            if slot not in self.goal.keys():#dont have compatible slots, get from default values
                value = self._get_default_slot_value(slot)
                if value is not None:
                    item.value = value
                else:
                    for s in eq_slots:#get default of equivalent slots
                        value = self._get_default_slot_value(s)
                        if value is not None:
                            item.value = value
                            item.name = s
                    if item.value is None:
                        #raise RuntimeError('Cant find value for slot %s and its equivalents slot from goal and default slots'%slot)
                        #print '!!!!!!???set to None, Cant find value for slot [%s] and its equivalents slot from goal and default slots'%slot
                        item.value = None
            else:
                item.value=self.goal[slot]
                item.name = slot
        return item.value 

    def reward_last_da(self):
        '''Rewards the last system dialgoue act'''
        last_da = self.turns[len(self.turns)-1]['sys_da']
        return self.metadata['goals'][self.goal_id]['reward_last_da_fun'](self.goal, last_da)

    def reward_final_goal(self):
        '''Return final reward for the current dialouge'''
        return self.metadata['goals'][self.goal_id]['reward_final_goal_fun'](self.goal, self.turns)
        
    def end_dialogue(self):
        '''end dialgoue and post-processing'''
        fun = get_dict_value(self.metadata['goals'][self.goal_id], 'end_dialogue_post_process_fun')
        if fun is not None:
            fun(self)
