import autopath
from alex.utils.config import Config
from alex.components.simulator.user_simulator.simple_user_simulator import SimpleUserSimulator
from alex.utils.database.python_database import PythonDatabase
from alex.components.slu.da import DialogueActItem, DialogueAct

cfg = None

def get_config():
    global cfg
    cfg = Config.load_configs(['simulator.cfg', 'ptien_metadata.py'], log=False)

def simulate_one_dialogue(user):
    #a list of system acts will be sent to user
    sys_das = ['hello()',
                'request(task)',
                'implconfirm(task=find_connection)&request(from_stop)',
                'request(to_stop)',
                'implconfirm(to_stop=first stop)&request(arrival_time)',
                'offer(route=take the tram 12, it will pass your destination after 6 stops.)',
                'bye()',
                ]

    user.new_dialogue()
    print '-'*60
    print 'Goal:', user.goal
    print '-'*60
    for da in sys_das:
        sys_da = DialogueAct(da)
        print 'sys_da:\t\t',sys_da
        user.da_in(sys_da)
        user_da = user.da_out()
        print 'user_da:\t', user_da[0]

def main():
    get_config()
    db = PythonDatabase(cfg)
    user = SimpleUserSimulator(cfg, db)
    simulate_one_dialogue(user)

if __name__ == '__main__':
    main()
