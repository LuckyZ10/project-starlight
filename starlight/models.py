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
    learning_sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    learner_profile = relationship("LearnerProfileModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    review_cards = relationship("ReviewCardModel", back_populates="user", cascade="all, delete-orphan")

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


class LearningSession(Base):
    """Persisted learning session — survives bot restarts."""
    __tablename__ = "learning_sessions"
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cartridge_id = Column(String, ForeignKey("cartridges.id"), nullable=False)
    current_node = Column(String, nullable=False)
    turn_count = Column(Integer, default=0)
    max_turns = Column(Integer, default=5)
    conversation_json = Column(JSON, default=list)
    node_scores_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="learning_sessions")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class LearnerProfileModel(Base):
    """Persisted learner profile — survives bot restarts."""
    __tablename__ = "learner_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    knowledge_level = Column(Float, default=0.0)
    learning_speed = Column(Float, default=1.0)
    confidence = Column(Float, default=0.5)
    engagement = Column(Float, default=0.5)
    cognitive_load = Column(Float, default=0.3)
    zpd_zone = Column(String, default="zpd")
    bloom_level = Column(Integer, default=1)
    streak_days = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)
    nodes_completed = Column(Integer, default=0)
    error_patterns_json = Column(JSON, default=list)
    history_json = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="learner_profile")


class ReviewCardModel(Base):
    """Persisted SM-2+ review cards — survives bot restarts."""
    __tablename__ = "review_cards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    node_id = Column(String, nullable=False)
    cartridge_id = Column(String, nullable=False)
    interval = Column(Integer, default=1)
    ease_factor = Column(Float, default=2.5)
    repetition = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)
    title = Column(String, default="")
    user = relationship("User", back_populates="review_cards")
