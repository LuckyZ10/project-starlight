from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    plan = Column(String, default="free")
    api_key_enc = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    progress = relationship("UserProgress", back_populates="user")
    assessments = relationship("Assessment", back_populates="user")

class Cartridge(Base):
    __tablename__ = "cartridges"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    version = Column(String, default="1.0.0")
    language = Column(String, default="zh-CN")
    entry_node = Column(String, nullable=False)
    status = Column(String, default="active")
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    nodes = relationship("Node", back_populates="cartridge")

class Node(Base):
    __tablename__ = "nodes"
    id = Column(String, primary_key=True)
    cartridge_id = Column(String, ForeignKey("cartridges.id"), primary_key=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    prerequisites = Column(JSON, default=list)
    difficulty = Column(Integer, default=1)
    pass_criteria = Column(Text, nullable=False)
    cartridge = relationship("Cartridge", back_populates="nodes")

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cartridge_id = Column(String, ForeignKey("cartridges.id"), nullable=False)
    current_node = Column(String, nullable=True)
    status = Column(String, default="not_started")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="progress")

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    node_id = Column(String, nullable=False)
    cartridge_id = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    score = Column(Integer, default=0)
    messages_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="assessments")

class Contributor(Base):
    __tablename__ = "contributors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    github = Column(String, nullable=True)
    location = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    quote = Column(Text, nullable=True)
    story = Column(Text, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

class CartridgeContributor(Base):
    __tablename__ = "cartridge_contributors"
    cartridge_id = Column(String, ForeignKey("cartridges.id"), primary_key=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), primary_key=True)
    role = Column(String, default="author")
