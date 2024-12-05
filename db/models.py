from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(100), nullable=False)
    roll_no = Column(Integer, nullable=True)
    info = Column(JSON, nullable=True)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)

    class_ = relationship("Class", back_populates="students")
    logs_as_target = relationship("Log", foreign_keys="Log.executed_on", back_populates="target_student")

class Faculty(Base):
    __tablename__ = 'faculty'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False)
    info = Column(JSON, nullable=True)
    password = Column(String(16), nullable=False)

    classes_as_head = relationship("Class", foreign_keys="Class.class_head_id", back_populates="class_head")
    logs_as_executor = relationship("Log", foreign_keys="Log.executed_by", back_populates="executor")

class Classes(Base):
    __tablename__ = 'classes'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(25), nullable=False)
    is_restricted = Column(Boolean, nullable=False)
    faculty_members_id = Column(Text, nullable=True) 
    class_head_id = Column(Integer, ForeignKey('faculty.id'), nullable=True)
    class_representative_id = Column(Integer, ForeignKey('students.id'), nullable=True)
    
    class_head = relationship("Faculty", foreign_keys=[class_head_id], back_populates="classes_as_head")
    class_representative = relationship("Student", foreign_keys=[class_representative_id])
    students = relationship("Student", back_populates="class_")

class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    action_type = Column(String(20), nullable=False)
    executed_by = Column(Integer, ForeignKey('faculty.id'), nullable=False)
    executed_on = Column(Integer, ForeignKey('students.id'), nullable=False)
    is_log_secret = Column(Boolean, nullable=False)
    description = Column(Text, nullable=True)

    executor = relationship("Faculty", foreign_keys=[executed_by], back_populates="logs_as_executor")
    target_student = relationship("Student", foreign_keys=[executed_on], back_populates="logs_as_target")
