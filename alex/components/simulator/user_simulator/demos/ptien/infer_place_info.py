from alex.utils.config import as_project_path
from alex.components.dm.ontology import Ontology
from alex.utils.sample_distribution import sample_from_list
import copy
import pdb

def add_place_info(goal):
    infer = InferInfo()
    final_goal = infer.infer_info(goal)
    if final_goal != goal:
        print '***---Goal is added info....'
        print '---Original goal', goal
        print '---Final goal:', final_goal
        #pdb.set_trace()
    return final_goal

class InferInfo(object):

    def __init__(self):
        path = as_project_path('applications/PublicTransportInfoEN/data/ontology.py')
        self.ontology = Ontology(path)

    def get_accepted_mpv(self, ds, slot, accepted_slots):
        if slot in self.goal.keys():
            return self.goal[slot]
        else:
            return 'none'

    def infer_info(self, goal):
        ds = None
        accepted_slots = None
        self.goal = copy.deepcopy(goal)

        # retrieve the slot variables
        from_city_val = self.get_accepted_mpv(ds, 'from_city', accepted_slots)
        from_borough_val = self.get_accepted_mpv(ds, 'from_borough', accepted_slots)
        from_stop_val = self.get_accepted_mpv(ds, 'from_stop', accepted_slots)
        from_street_val = self.get_accepted_mpv(ds, 'from_street', accepted_slots)
        from_street2_val = self.get_accepted_mpv(ds, 'from_street2', accepted_slots)
        to_city_val = self.get_accepted_mpv(ds, 'to_city', accepted_slots)
        to_borough_val = self.get_accepted_mpv(ds, 'to_borough', accepted_slots)
        to_stop_val = self.get_accepted_mpv(ds, 'to_stop', accepted_slots)
        to_street_val = self.get_accepted_mpv(ds, 'to_street', accepted_slots)
        to_street2_val = self.get_accepted_mpv(ds, 'to_street2', accepted_slots)
        vehicle_val = self.get_accepted_mpv(ds, 'vehicle', accepted_slots)
        max_transfers_val = self.get_accepted_mpv(ds, 'num_transfers', accepted_slots)

        # infer cities based on stops
        from_cities, to_cities = None, None
        if from_stop_val != 'none' and from_city_val == 'none':
            from_cities = self.ontology.get_compatible_vals('stop_city', from_stop_val)
            if len(from_cities) == 1:
                from_city_val = from_cities.pop()
            elif len(from_cities)>1:
                from_city_val = sample_from_list(from_cities)
            #if from_city_val != 'none':
                self.goal['from_city']= from_city_val

        if to_stop_val != 'none' and to_city_val == 'none':
            to_cities = self.ontology.get_compatible_vals('stop_city', to_stop_val)
            if len(to_cities) == 1:
                to_city_val = to_cities.pop()
            elif len(to_cities)>1:
                to_city_val = sample_from_list(to_cities)
            #if to_city_val != 'none':
                self.goal['to_city']= to_city_val

        # infer cities based on street
        from_cities_st, to_cities_st = None, None
        if from_street_val != 'none' and from_city_val == 'none':
            from_cities_st = self.ontology.get_compatible_vals('street_city', from_street_val)
            if len(from_cities_st) == 1:
                from_city_val = from_cities_st.pop()
            elif len(from_cities_st)>1:
                from_city_val = sample_from_list(from_cities_st)
            #if from_city_val != 'none':
                self.goal['from_city']= from_city_val

        if to_street_val != 'none' and to_city_val == 'none':
            to_cities_st = self.ontology.get_compatible_vals('street_city', to_stop_val)
            if len(to_cities_st) == 1:
                to_city_val = to_cities_st.pop()
            elif len(to_cities_st)>1:
                to_city_val = sample_from_list(to_cities_st)
            #if to_city_val != 'none':
                self.goal['to_city']= to_city_val

        # infer boroughs based on stops
        from_boroughs, to_boroughs = None, None
        if from_stop_val != 'none' and from_borough_val == 'none':
            from_boroughs = self.ontology.get_compatible_vals('stop_borough', from_stop_val)
            if len(from_boroughs) == 1:
                from_borough_val = from_boroughs.pop()
            elif len(from_boroughs)>1:
                from_borough_val = sample_from_list(from_boroughs)
            #if from_borough_val != 'none':
                self.goal['from_borough']= from_borough_val

        if to_stop_val != 'none' and to_borough_val == 'none':
            to_boroughs = self.ontology.get_compatible_vals('stop_borough', to_stop_val)
            if len(to_boroughs) == 1:
                to_borough_val = to_boroughs.pop()
            elif len(to_boroughs)>1:
                to_borough_val = sample_from_list(to_boroughs)
            #if to_borough_val != 'none':
                self.goal['to_borough']= to_borough_val

        # infer boroughs based on streets
        from_boroughs_st, to_boroughs_st = None, None
        if to_street_val != 'none' and to_borough_val == 'none':
            to_boroughs_st = self.ontology.get_compatible_vals('street_borough', to_street_val)
            if len(to_boroughs_st) == 1:
                to_borough_val = to_boroughs_st.pop()
            elif len(to_boroughs_st)>1:
                to_borough_val = sample_from_list(to_boroughs_st)
            #if to_borough_val != 'none':
                self.goal['to_borough']= to_borough_val

        if from_street_val != 'none' and from_borough_val == 'none':
            from_boroughs_st = self.ontology.get_compatible_vals('street_borough', from_street_val)
            if len(from_boroughs_st) == 1:
                from_borough_val = from_boroughs_st.pop()
            elif len(from_boroughs_st)>1:
                from_borough_val= sample_from_list(from_boroughs_st)
            #if from_borough_val!= 'none':
                self.goal['from_borough']= from_borough_val

        '''
        #set 'none' for slot which could find info in database present I don't know
        val = 'none'
        if 'from_borough' not in self.goal and ('from_stop' in self.goal or 'from_street' in self.goal):
            self.goal['from_borough'] = val
        if 'to_borough' not in self.goal and ('to_stop' in self.goal or 'to_street' in self.goal):
            self.goal['to_borough'] = val
        if 'from_city' not in self.goal:
            self.goal['from_city'] = val
        if 'to_city' not in self.goal:
            self.goal['to_city'] = val
        '''
    
        return self.goal
