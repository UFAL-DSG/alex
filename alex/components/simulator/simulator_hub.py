#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

import time
import argparse
import sys, traceback

from alex.applications.exceptions import SemHubException
from alex.components.hub import Hub
from alex.components.slu.da import DialogueAct, DialogueActNBList
from alex.components.slu.exceptions import DialogueActException, DialogueActItemException
from alex.components.dm.common import dm_factory, get_dm_type
from alex.utils.config import Config

from alex.components.simulator.user_simulator.simple_user_simulator import SimpleUserSimulator
from alex.components.simulator.asr_simulator.simple_asr_simulator import SimpleASRSimulator
from alex.utils.database.python_database import PythonDatabase
from alex.utils.support_functions import deep_copy
from alex.components.slu.da import DialogueActItem, DialogueAct
import multiprocessing
import time
import numpy as np

from alex.components.hub.messages import Command, ASRHyp, SLUHyp

#------------------------------------------ for final results
sucess_rate = 0
mean_turn_number = 0
mean_total_reward = 0
g_user = None
g_asr = None

def initilize(config):
    global g_user, g_asr
    db = PythonDatabase(cfg)
    g_user = SimpleUserSimulator(cfg, db)
    g_asr = SimpleASRSimulator(cfg, db)
    
class SimulatorHub(Hub):
    """SimulatorHub simulates dialogues between an user simulator and a dialogue manager.
    
    It builds a hub to connect user simulator and dialogue manager.
    It may be used to train and evaluate a dialogue mangager with an user simulator given.
    """
    #hub_type = "SimulatorHub"

    def __init__(self, cfg):
        super(SimulatorHub, self).__init__(cfg)
        #self.cfg = cfg
        dm_type = get_dm_type(cfg)
        self.dm = dm_factory(dm_type, cfg)
        #self.dm.new_dialogue()

        self.close_event = multiprocessing.Event()

    def print_da(self, agent, da):
        """Prints the dialogue act to the output, log."""
        print agent, '\t\t', unicode(da)

    def simulate_one_dialogue(self, user, asr, dm, dialogue_id=0):
        """Simulate one dialogue given user simuator, ASR simulator and dialogue manager."""
        
        '''
        cfg['Logging']['system_logger'].session_start("simulator")
        cfg['Logging']['system_logger'].session_system_log('config = ' + unicode(cfg))

        cfg['Logging']['session_logger'].session_start(cfg['Logging']['system_logger'].get_session_dir_name())
        cfg['Logging']['session_logger'].config('config = ' + unicode(cfg))
        cfg['Logging']['session_logger'].header(cfg['Logging']["system_name"], cfg['Logging']["version"])
        #cfg['Logging']['session_logger'].input_source("dialogue acts")
        #cfg['Logging']['session_logger'].input_source("voip")
        '''

        sys_das = ['hello()',
                'request(task)',
                'implconfirm(task=find_connection)&request(from_stop)',
                'request(to_stop)',
                'implconfirm(to_stop=first stop)&request(arrival_time)',
                'offer(route=take the tram 12, it will pass your destination after 6 stops.)',
                'bye()',
                ]
        
        user.new_dialogue()
        print '%s\nDialogue %d, user goal: %s\n%s'%('='*60, dialogue_id, user.goal, '='*60)
        #cfg['Logging']['session_logger'].input_source("dialogue acts")
        turn_index = 0
        #TODO: Get DM and make it conversation with simulator
        dm.new_dialogue()
        total_reward = 0
        while(True):
            print '%sTurn %d%s'%('-'*20, turn_index, '-'*20)
            #pdb.set_trace()
            #print 'Dialogue state: ', dm.dialogue_state
            sys_da = dm.da_out()
            #sys_da = DialogueAct(sys_das[index])
            print '---sys_da:\t',sys_da
            #pdb.set_trace()
            self.cfg['Logging']['session_logger'].turn("system")
            self.cfg['Logging']['session_logger'].dialogue_act("system", sys_da) 

            user.da_in(sys_da)#User Simulator
            user_da = user.da_out()
            user_da = user_da[0]
            turn_reward = user.reward_last_da()
            total_reward += turn_reward
            #print 'reward:', turn_reward
            print '---user_da:\t', user_da
            self.cfg['Logging']['session_logger'].turn("user")
            self.cfg['Logging']['session_logger'].dialogue_act("user", user_da)

            confusion_net = asr.simulate_asr(user_da)#ASR Simulator
            nbest_list = confusion_net.get_da_nblist()
            self.cfg['Logging']['session_logger'].slu("user", '*', nbest_list, confnet=confusion_net)

            hyps = SLUHyp(confusion_net, asr_hyp=None)#DM
            #print '---SLUHyp to DM:\n', hyps.hyp
            dm.da_in(hyps.hyp,  utterance=None)
            
            turn_index +=1
            if user_da.has_dat('bye') or user_da.has_dat('hangup'):
                break

        goal_reward = user.reward_final_goal()
        total_reward += goal_reward
        success = 0
        user_satisfied = False
        if goal_reward==20:
            success = 1
            user_satisfied = True
        success_text = 'success' if success else 'UNsuccess'
        dm.set_final_reward(user_satisfied)
        dm.end_dialogue()
        print '%sDialogue %d: %s after %d turns, goal reward: %d, total reward: %d'%('-'*10,dialogue_id, success_text, turn_index, goal_reward, total_reward)

        self.cfg['Logging']['system_logger'].session_end()
        self.cfg['Logging']['session_logger'].session_end()
        return success, turn_index, total_reward

    def run(self, episode=100, asr_error=0):
        global success_rate, mean_turn_number, mean_total_reward
        """Run the hub."""
        try:
            self.cfg['Logging']['system_logger'].info("Simulator Hub\n" + "=" * 120)
            self.cfg['Logging']['system_logger'].info("""Starting new one...""")
            '''move this part to evaludate_dm
            self.close_event = multiprocessing.Event()
            cfg['Logging']['session_logger'].set_close_event(self.close_event)
            cfg['Logging']['session_logger'].set_cfg(cfg)
            if cfg['Logging']['session_logger']._popen is None:
                cfg['Logging']['session_logger'].start()
            cfg['Logging']['session_logger'].cancel_join_thread()
            '''

            '''
            db = PythonDatabase(cfg)
            user = SimpleUserSimulator(cfg, db)
            asr = SimpleASRSimulator(cfg, db)
            '''
            user = g_user
            asr = g_asr
            dm = self.dm

            turn_counts = []
            rewards = []
            success_count = 0
            error_count = 0
            start_time = time.time()

            dialogue_count = 0
            while dialogue_count<episode:
                try:
                    success, turn_count, reward = self.simulate_one_dialogue(user, asr, dm, dialogue_count)
                    turn_counts.append(turn_count)
                    rewards.append(reward)
                    success_count += success
                except Exception as e:
                    print '*******---System Error at Dialogue %d:'%(dialogue_count)
                    traceback.print_exc()
                    print traceback.format_exc()
                    print '-'*50
                    error_count += 1
                    rewards.append(0)#0 is the reward of unsuccessful dialogue
                dialogue_count += 1
            
            lines = ['\n%s%s (asr error=%d%%)%s'%('='*30, 'SUMMARY', asr_error, '='*30)]
            lines.append('-Total executing time: %.3f seconds'%(time.time()-start_time))
            rate = success_count*100.0/episode
            lines.append('-Success rate: %.2f (%d/%d)'%(rate,success_count, episode))
            lines.append('-Number of dialogue error: %d (%.3f%%)'%(error_count, error_count*100.0/episode))
            lines.append('-Averaging turn number/dialogue: %.3f (std=%.3f)'%(np.mean(turn_counts), np.std(turn_counts)))
            lines.append('-Averaging total reward /dialogue: %.3f (std=%.3f)'%(np.mean(rewards), np.std(rewards)))
            lines.append('-'*66)
            
            success_rate = rate
            mean_turn_number = np.mean(turn_counts)
            mean_total_reward = np.mean(rewards)

            print '\n'.join(lines)
            #pdb.set_trace() 

        except KeyboardInterrupt:
            print 'KeyboardInterrupt exception in: %s' % multiprocessing.current_process().name
            return
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in SHUB process.')
            raise
        
        #time.sleep(3)
        #print 'Exiting: %s. Setting close event' % multiprocessing.current_process().name
        #self.close_event.set()

#########################################################################
def set_asr_error(config, error):
    config_asr = config['asr_simulator']['SimpleASRSimulator']
    error = error/100.0
    half_error = (float(error)/2.0)
    '''
    config_asr['act_confusion']['affirm']['confusion_matrix']['confusion_types']['correct'] = 1.0-half_error
    config_asr['act_confusion']['affirm']['confusion_matrix']['confusion_types']['onlist'] = half_error
    config_asr['act_confusion']['negate']['confusion_matrix']['confusion_types']['correct'] = 1.0-half_error
    config_asr['act_confusion']['negate']['confusion_matrix']['confusion_types']['onlist'] = half_error

    config_asr['default']['default_confusion_matrix']['confusion_types']['correct'] = 1.0-error
    config_asr['default']['default_confusion_matrix']['confusion_types']['onlist'] = half_error
    config_asr['default']['default_confusion_matrix']['confusion_types']['offlist'] = half_error
    '''
    config_asr['act_confusion']['affirm']['confusion_matrix']['confusion_types']['correct'] = 1.0-error
    config_asr['act_confusion']['affirm']['confusion_matrix']['confusion_types']['onlist'] = error
    config_asr['act_confusion']['negate']['confusion_matrix']['confusion_types']['correct'] = 1.0-error
    config_asr['act_confusion']['negate']['confusion_matrix']['confusion_types']['onlist'] = error

    config_asr['default']['default_confusion_matrix']['confusion_types']['correct'] = max(1.0-error-half_error, 0)
    print 'correct', config_asr['default']['default_confusion_matrix']['confusion_types']['correct']
    config_asr['default']['default_confusion_matrix']['confusion_types']['onlist'] = half_error if error + half_error<=1.0 else 1.0-error
    print 'onlist', config_asr['default']['default_confusion_matrix']['confusion_types']['onlist']
    config_asr['default']['default_confusion_matrix']['confusion_types']['offlist'] = error
    print 'offlist', config_asr['default']['default_confusion_matrix']['confusion_types']['offlist']
    #'''

    if error==0:
        config_asr['act_confusion']['affirm']['confusion_matrix']['max_length'] = 1
        config_asr['act_confusion']['negate']['confusion_matrix']['max_length'] = 1
        config_asr['act_confusion']['default']['confusion_matrix']['probability_generator']['correct']['onlist'] = 0.0

        config_asr['default']['default_confusion_matrix']['max_length'] = 1
        config_asr['default']['default_confusion_matrix']['probability_generator']['correct']['onlist'] = 0.0
        config_asr['default']['default_confusion_matrix']['probability_generator']['correct']['offlist'] = 0.0
    else:
        config_asr['act_confusion']['affirm']['confusion_matrix']['max_length'] = 2
        config_asr['act_confusion']['negate']['confusion_matrix']['max_length'] = 2
        config_asr['act_confusion']['default']['confusion_matrix']['probability_generator']['correct']['onlist'] = 1.0

        config_asr['default']['default_confusion_matrix']['max_length'] = 5
        config_asr['default']['default_confusion_matrix']['probability_generator']['correct']['onlist'] = 1.0
        config_asr['default']['default_confusion_matrix']['probability_generator']['correct']['offlist'] = 3.0

    return config
  
def evaluate_dm(config, episode=1000):
    close_event = multiprocessing.Event()
    config['Logging']['system_logger'].info("Simulator Hub\n" + "=" * 120)
    config['Logging']['system_logger'].info("""Starting...""")

    config['Logging']['session_logger'].set_close_event(close_event)
    config['Logging']['session_logger'].set_cfg(config)
    #config['Logging']['session_logger'].start()
    config['Logging']['session_logger'].cancel_join_thread()

    #asr_errors = [10, 15, 20, 30, 40, 50, 70, 90]
    asr_errors = [0, 15, 30, 50, 60, 70, 90]
    asr_errors = [30]*1
    for error in asr_errors:
        config = set_asr_error(config, error)
        print '%s\n%sASR error rate set to [%d%%]\n%s'%('='*80, '*'*25, error, '='*80)
        #config['Logging']['session_logger'].set_cfg(config)
        shub = SimulatorHub(config)
        shub.run(episode, error)

    #time.sleep(3)
    print 'Exiting: %s. Setting close event' % multiprocessing.current_process().name
    close_event.set()

def delete_file(file_path):
    import os
    if os.path.exists(file_path):
        os.remove(file_path)

#def repeated_evaluation(config, repeat_number=10, episode=1000, split=20):
#def repeated_evaluation(config, repeat_number=3, episode=1000, split=1000):
#def repeated_evaluation(config, repeat_number=20, episode=100, split=5):
def repeated_evaluation(config, repeat_number=1, episode=1, split=1):
#def repeated_evaluation(config, repeat_number=1, episode=1, split=1):
    import numpy as np
    d = episode/split
    success = np.zeros((d, repeat_number))
    turn = np.zeros((d, repeat_number))
    reward = np.zeros((d, repeat_number))
    for r in range(repeat_number):
        print '=============repeated', r, '========='
        delete_file('gp_sara.params.pkl')
        #delete_file('gp_sara.gasic.params.pkl')
        for i in range(d):
            evaluate_dm(config, split)
            success[i, r] =  success_rate
            reward[i, r] =  mean_total_reward
            turn[i, r] =  mean_turn_number

    print '!!!!!save to the file'
    sys.stderr.write('!!!!!!Finished copy the command to write files\n')
    #np.savetxt('success.csv', success, delimiter=',', fmt='%f')
    #np.savetxt('reward.csv', reward, delimiter=',', fmt='%f')
    #np.savetxt('turn.csv', turn, delimiter=',', fmt='%f')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        SimulatorHub is a simulation enviroment for SDS.

        It invokes user simulator and dialogue mangager to simulate a normal dialouger.

        The program reads the default config in the resources directory ('../resources/default.cfg') config
        in the current directory.

        In addition, it reads all config file passed as an argument of a '-c'.
        The additional config files overwrites any default or previous values.

      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    args = parser.parse_args()

    if args.configs is None:
        args.configs = ['./ptien_configs/ptien.cfg', './ptien_configs/ptien_hdc_slu.cfg','./user_simulator/demos/ptien/simulator.cfg', './user_simulator/demos/ptien/ptien_metadata.py', './asr_simulator/demos/ptien/config_asr_simulator.py', './ptien_configs/config_gp_sarsa.py']
        #TODO Remove suitablely
        #args.configs.remove('./ptien_configs/config_gp_sarsa.py')
        #args.configs.append('./ptien_configs/config_full_gp_sarsa.py')
        #args.configs.append('./ptien_configs/config_gasic_gp_sarsa.py')
        #args.configs.append('./ptien_configs/config_gasic_full_gp_sarsa.py')

    cfg = Config.load_configs(args.configs, log=False)
    initilize(cfg)

    #shub = SimulatorHub(cfg)

    #import pdb
    #pdb.set_trace()
    #shub.run()
    #evaluate_dm(cfg)
    repeated_evaluation(cfg)
