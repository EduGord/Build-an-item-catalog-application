# The sys module provides a number of functions and variable that can be used to
# manipulate different parts of the Python Runtime Environment
import sys

# This will come in handy when we're writting the mapper code

from sqlalchemy import Column, ForeignKey, Integer, String

#  We will use in our configuration and class code
from sqlalchemy.ext.declarative import declarative_base

# In order to create our foren keys relationships, this will be user when while
# this too will be use when we writte our mapper
from sqlalchemy.orm import relationship

# We will use in our configuration code at the end of the file
from sqlalchemy import create_engine

#  Will let SQLAlchemy know that our classes are special SQLAlchemy classes
# that correspond to tables in our database
# we use declarative_base() in order to create a base class that our class code will inherit.
Base = declarative_base()

# Class definition
class Subject(Base):

    # Table information
    __tablename__ = 'subject'

    #  Mappers
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

# Class definition
class Topic(Base):

    # Table information
    __tablename__ = 'topic'

    #  Mappers
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    subject_id = Column(Integer, ForeignKey('subject.id'))
    subject = relationship(Subject)

    @property
    def serialize(self):
        #Return object data in easily serializableformat
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
        }

class Question(Base):
    # Table information
    __tablename__ = 'question'

    #  Mappers
    id = Column(Integer, primary_key=True)
    type = Column(String(2))
    answer = Column(String(250))
    header = Column(String(250))
    body = Column(String(2500))
    topic_id = Column(Integer, ForeignKey('topic.id'))
    topic = relationship(Topic)
# An instance of our create_engine class and point to the database we'll use
# Since we're using SQLite 3 the create Engine will create a new file  that we
# can use similarly to a more robusts database like MySQL or Postgree
engine = create_engine('sqlite:///educationmenu.db')

# Goes into the database and adds the classes we will soon create as new tables
# in our database
Base.metadata.create_all(engine)
