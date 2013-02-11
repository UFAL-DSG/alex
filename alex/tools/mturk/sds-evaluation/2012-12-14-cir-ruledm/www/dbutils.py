from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_local_db_session():
    # open database
    from local_cfg import cfg
    db_name = cfg['db_name']
    engine = create_engine('sqlite:///%s' % db_name)
    
    # get session
    Session = sessionmaker(bind=engine)
    session = Session()

    return session
