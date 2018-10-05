from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Subject, Base, Topic, Question

engine = create_engine('sqlite:///educationmenu.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

#Subject
subject1 = Subject(name="English")
session.add(subject1)
session.commit()

topic1 = Topic(name="Question Words", description="A list of verbs that are \
irregular in the Past Tense", subject=subject1)

session.add(topic1)
session.commit()

topic2 = Topic(name="Past Tense Irregular Verbs", description="Who, When, Why,\
 What, Which, How", subject=subject1)

session.add(topic2)
session.commit()




subject2 = Subject(name="Mathematics")
session.add(subject2)
session.commit()

topic3 = Topic(name="First degree equations with one variable", description=\
"((x + 2)*3 + 1)/6 = 10", subject = subject2)

session.add(topic3)
session.commit()

topic4 = Topic(name="First degree inequations", description="x + 6 > 5 + 2x",\
 subject = subject2)

session.add(topic4)
session.commit()




subject3 = Subject(name="Chemestry")
session.add(subject3)
session.commit()

topic5 = Topic(name="Atom basics", description="", subject = subject3)

session.add(topic5)
session.commit()

topic6 = Topic(name="Atomic Mass & Atomic Mass Number", description="", \
subject = subject3)

session.add(topic6)
session.commit()




subject4 = Subject(name="Physics")
session.add(subject4)
session.commit()

topic7 = Topic(name="Kinematics of uniform motion", description="S = S0 + V*t",\
 subject = subject4)

session.add(topic7)
session.commit()

topic8 = Topic(name="Kinematics of uniform accelerated motion", \
description="S = S0 + V*t + (a*t^2)/2", subject = subject4)

session.add(topic8)
session.commit()

print "Added Topics!"
