"""
Database package initialization.
Provides access to database models and connection functionality.
"""

# Import models after they are fully defined to avoid circular imports
from src.database.models import (
    Base, init_db, get_session, engine, Session,
    User, Trade, Balance, PortfolioSnapshot, SignalLog,
    create_admin_user, create_initial_snapshot, initialize_database
)

__all__ = [
    'Base', 'init_db', 'get_session', 'engine', 'Session',
    'User', 'Trade', 'Balance', 'PortfolioSnapshot', 'SignalLog',
    'create_admin_user', 'create_initial_snapshot', 'initialize_database'
]
