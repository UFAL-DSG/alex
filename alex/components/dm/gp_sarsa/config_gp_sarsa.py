from alex.utils.config import as_project_path, online_update
from alex.components.dm.gp_sarsa.kernel_functions import gaussian_kernel_fun, kronecker_delta_kernel_fun, polyminal_kernel_fun

def kernel_function((b1, a1), (b2, a2)):
    '''Compute the value of kernel function for given pair of data points'''
    state_kernel = gaussian_kernel_fun
    #self.state_kernel = polyminal_kernel_fun
    action_kernel = kronecker_delta_kernel_fun
    return state_kernel(b1, b2, p=4, sigma=5)*action_kernel(a1, a2)

def get_possible_acts(belief_features, sys_act_history):
    acts = ['request', 'select', 'confirm', 'implconfirm', 'offer']
    return acts

config = {
    'DM': {
        'gp_sarsa':{
            'debug': True,
            'epsilon': -1,
            'gamma': 0.9,
            'sigma': 5.916,
            'variance_scale': 1,
            'threshold_v': 0.015,
            #'storage_file': 'gp_sara.params.pkl',
            'storage_file': None,
            'kernel_fun': kernel_function,
            'get_possible_sys_acts_fun': get_possible_acts,
        }, 
    },
}
