from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Date, Integer, String, DateTime, Text
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import relationship, backref
from  sqlalchemy.sql.expression import func, select
from sqlalchemy.sql import and_, or_, not_

Base = declarative_base()

class Token(Base):
    """Holds data about current tokens."""
    __tablename__ = "token"

    id = Column(Integer, primary_key=True)
    number = Column(String)
    data = Column(String)
    submission_id = Column(Integer, ForeignKey("submission.id"))

    submission = relationship("Submission", backref=backref("submission", order_by=id))

    @classmethod
    def get_new(cls, session):
        session.execute("BEGIN EXCLUSIVE")
        new_submission = Submission()
        session.add(new_submission)

        new_token = session.query(Token).filter_by(submission_id=None).order_by(func.random()).first()
        if new_token is not None:
            new_token.submission = new_submission
            session.commit()
        else:
            session.remove(new_submission)
            new_submission = None
            session.commit()

        return new_token, new_submission

    @classmethod
    def generate_tokens(cls, session):
        tokens = []
        for i in range(1000, 10000):
            tokens += [Token(number=i)]
        session.add_all(tokens)
        session.commit()


class Worker(Base):
    """Holds data about workers that had worked."""
    __tablename__ = "worker"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String)
    worker_id = Column(String)

    def __init__(self, phone_number, worker_id):
        self.phone_number = phone_number
        self.worker_id = worker_id

    def get_submissions_since(self, session, timestamp):
        return session.query(Submission).filter(and_(Submission.worker==self, Submission.timestamp >= timestamp))



class Submission(Base):
    """Holds data about worker's submissions."""
    __tablename__ = "submission"

    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("worker.id"))
    worker = relationship("Worker", backref=backref("worker", order_by=id))
    dialogue_id = Column(String)
    timestamp = Column(DateTime)
    data = Column(Text)

if __name__ == "__main__":
    from local_cfg import cfg
    engine = create_engine('sqlite:///%s' % cfg['db_name'])
    Base.metadata.create_all(engine)
