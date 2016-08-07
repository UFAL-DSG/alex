from alex.utils.config import as_project_path, online_update
from alex.components.dm.gp_sarsa.kernel_functions import gaussian_kernel_fun, kronecker_delta_kernel_fun, polyminal_kernel_fun

def kernel_function((b1, a1), (b2, a2)):
    '''Compute the value of kernel function for given pair of data points'''
    state_kernel = gaussian_kernel_fun
    #self.state_kernel = polyminal_kernel_fun
    action_kernel = kronecker_delta_kernel_fun
    return state_kernel(b1, b2, p=4, sigma=5)*action_kernel(a1, a2)

def get_possible_acts(belief_features, sys_act_history):
    #acts = ['request', 'select', 'confirm', 'implconfirm', 'offer']
    acts = ['request_from', 'request_to', 'request_time', 'request_vehicle',
            'confirm_from', 'confirm_to', 'confirm_time', 'confirm_vehicle',
            'implconfirm_from', 'implconfirm_to', 'implconfirm_time', 'implconfirm_vehicle',
            'select_from', 'select_to', 'select_time', 'select_vehicle',
            'offer',]

    return acts

config = {
    'DM': {
        'dialogue_policy':{
            'PTIENHDCPolicy': {#for GP-Sarsa embed HDCPolicy
                'accept_prob_ludait': 0.5,
                'accept_prob_being_requested': 0.8,
                'accept_prob_being_confirmed': 0.8,
                'accept_prob_being_selected': 0.8,
                'accept_prob_noninformed': 0.8,
                'accept_prob': 0.8,#0.8 is original, change for GP-Sarsa
                'confirm_prob':  0.1,#0.4 is original, chang efor gP_Sarsa
                'select_prob': 0.1,#0.4 is original, change for GP-Sarsa
                'min_change_prob': 0.1,
            },
            'gp_sarsa':{
                'debug': False,
                'epsilon': -1,
                'gamma': 0.9,
                'sigma': 5.916,
                'variance_scale': 1,#old value =1, best =3
                'threshold_v': 0.015,
                'storage_file': 'gp_sara.params.pkl',
                #'storage_file': None,
                'kernel_fun': kernel_function,
                'get_possible_sys_acts_fun': get_possible_acts,
            },
        }, 
    },
}
