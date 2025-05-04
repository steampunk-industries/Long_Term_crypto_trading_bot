import os
import json
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, MetaData
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from loguru import logger

from src.config import config

# Set up the declarative base with fresh metadata
Base = declarative_base()

# Initialize engine and Session to None, will be set in init_db()
engine = None
Session = None

# User model for authentication
class User(Base, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Trade model
class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    exchange = Column(String(64), nullable=False)
    symbol = Column(String(20), nullable=False)
    order_id = Column(String(64), nullable=False)
    side = Column(String(10), nullable=False)  # buy or sell
    type = Column(String(20), nullable=False)  # market, limit, etc.
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    fee = Column(Float, nullable=True)
    fee_currency = Column(String(10), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_paper = Column(Boolean, default=True)
    strategy = Column(String(64), nullable=True)

# Balance model
class Balance(Base):
    __tablename__ = 'balances'
    
    id = Column(Integer, primary_key=True)
    exchange = Column(String(64), nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_paper = Column(Boolean, default=True)

# Portfolio Snapshot model
class PortfolioSnapshot(Base):
    __tablename__ = 'portfolio_snapshots'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_value_usd = Column(Float, nullable=False)
    pnl_daily = Column(Float, nullable=True)
    pnl_weekly = Column(Float, nullable=True)
    pnl_monthly = Column(Float, nullable=True)
    pnl_all_time = Column(Float, nullable=True)
    drawdown = Column(Float, nullable=True)
    is_paper = Column(Boolean, default=True)
    
    @property
    def total_value(self):
        return self.total_value_usd

# Signal Log model
class SignalLog(Base):
    __tablename__ = 'signal_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20), nullable=False)
    strategy = Column(String(64), nullable=False)
    signal_type = Column(String(10), nullable=False)  # buy, sell, hold
    confidence = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    executed = Column(Boolean, default=False)
    signal_metadata = Column(Text, nullable=True)  # JSON string with additional data
    
    @property
    def get_metadata(self):
        if self.signal_metadata:
            try:
                return json.loads(self.signal_metadata)
            except:
                return {}
        return {}
    
    # Maintain backward compatibility
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'strategy': self.strategy,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'price': self.price,
            'executed': self.executed,
            'metadata': self.get_metadata
        }

def init_db():
    """Initialize the database and create tables."""
    global engine, Session
    
    try:
        # Use SQLite if configured, otherwise PostgreSQL
        if config.USE_SQLITE:
            # Ensure data directory exists
            data_dir = os.path.join(os.getcwd(), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            db_path = os.path.join(data_dir, 'crypto_bot.db')
            
            # Remove any existing DB file
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Removed existing database file: {db_path}")
            
            db_url = f'sqlite:///{db_path}'
            
            # For SQLite, connect_args is needed for multi-threaded access
            engine = create_engine(
                db_url, 
                connect_args={'check_same_thread': False},
                poolclass=StaticPool
            )
        else:
            # PostgreSQL connection
            db_url = f'postgresql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}'
            engine = create_engine(db_url)
        
        # Create session factory
        Session = sessionmaker(bind=engine)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        # Create admin user if it doesn't exist
        create_admin_user()
        
        # Create initial portfolio snapshot if none exists
        create_initial_snapshot()
        
        logger.info(f"Database initialized successfully with {db_url}")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def get_session():
    """Get a database session."""
    if Session is None:
        init_db()
    return Session()

def create_admin_user():
    """Create admin user if it doesn't exist."""
    try:
        session = get_session()
        admin = session.query(User).filter_by(username='admin').first()
        
        if admin is None:
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('password')
            session.add(admin)
            session.commit()
            logger.info("Admin user created")
        
        session.close()
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")

def create_initial_snapshot():
    """Create initial portfolio snapshot if none exists."""
    try:
        session = get_session()
        snapshot_count = session.query(PortfolioSnapshot).count()
        
        if snapshot_count == 0:
            initial_snapshot = PortfolioSnapshot(
                total_value_usd=config.INITIAL_CAPITAL,
                pnl_daily=0.0,
                pnl_weekly=0.0,
                pnl_monthly=0.0,
                pnl_all_time=0.0,
                drawdown=0.0,
                is_paper=True
            )
            session.add(initial_snapshot)
            session.commit()
            logger.info("Initial portfolio snapshot created")
        
        session.close()
    except Exception as e:
        logger.error(f"Error creating initial snapshot: {e}")

def initialize_database():
    """Initialize the database and return the engine."""
    init_db()
    return engine
