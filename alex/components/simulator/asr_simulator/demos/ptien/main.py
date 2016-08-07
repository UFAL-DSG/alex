import autopath
from alex.utils.config import Config
from alex.components.slu.da import DialogueAct
from alex.components.simulator.asr_simulator.simple_asr_simulator import SimpleASRSimulator
from alex.utils.database.python_database import PythonDatabase

cfg = None
db = None

def get_config():
    global cfg
    cfg = Config.load_configs(['config_asr_simulator.py'], log=False)

def print_nbest_list(nbest_list):
    print '-'*20, 'da_items'
    print nbest_list
    print '-'*20, 'nblist ='
    for prob, da in nbest_list.get_da_nblist():
        print prob, '\t', str(da)
    print '-'*20, 'best hyp='
    print nbest_list.get_best_da_hyp()
    print '-'*20, 'best hyp non null='
    print nbest_list.get_best_nonnull_da()

def print_asr_results(asr):
    for items, probs in asr:
        for item, prob in zip(items, probs):
            print prob, '\t', item

def test1():
    asr = SimpleASRSimulator(cfg, db)

    da = DialogueAct('deny(to_stop=thanh)')
    #da = DialogueAct('inform(task=find_connection)')
    da = DialogueAct('inform(to_stop=Central Park)')
    #da = DialogueAct('inform(from_stop=Thanh)&inform(to_stop=Central Park)')
    #da = DialogueAct('affirm()')
    #da = DialogueAct('affirm()&inform(to_stop=Central Park)')
    for i in range(1):
        asr_results  = asr.simulate_asr(da)
        print_nbest_list(asr_results)

    #print_asr_results(asr_results)

def main():
    global db
    get_config()
    db = PythonDatabase(cfg)
    test1()

if __name__ == '__main__':
    main()
