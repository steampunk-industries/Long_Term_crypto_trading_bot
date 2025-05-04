from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly
import plotly.graph_objs as go
from sqlalchemy import desc, func, text, inspect
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import traceback
from loguru import logger
import os

from src.database.models import Trade, Balance, PortfolioSnapshot, SignalLog, get_session
from src.config import config
from src.exchanges.exchange_factory import ExchangeFactory

# Create blueprint
dashboard = Blueprint('dashboard', __name__)

def create_portfolio_chart(portfolio_data):
    """
    Create a portfolio value chart.
    """
    if not portfolio_data:
        return {}

    dates = [p.timestamp for p in portfolio_data]
    values = [p.total_value for p in portfolio_data]

    trace = go.Scatter(
        x=dates,
        y=values,
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#17BECF')
    )

    layout = go.Layout(
        title='Portfolio Value Over Time',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Value (USD)'),
        template='plotly_dark'
    )

    fig = go.Figure(data=[trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Make sure the database is initialized properly
def ensure_tables_exist():
    """Ensure all required database tables exist."""
    try:
        from src.database.models import initialize_database
        engine = initialize_database()
        inspector = inspect(engine)
        
        # Check for required tables
        required_tables = ['users', 'trades', 'balances', 'portfolio_snapshots', 'signal_logs']
        existing_tables = inspector.get_table_names()
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}, running database initialization")
            # Full initialization
            from src.database.models import create_admin_user, create_initial_snapshot
            create_admin_user()
            create_initial_snapshot()
            
            # Check if data directory exists and has proper permissions (for SQLite)
            if hasattr(config, 'USE_SQLITE') and config.USE_SQLITE:
                data_dir = os.path.join(os.getcwd(), 'data')
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir, exist_ok=True)
                
                db_path = os.path.join(data_dir, 'crypto_bot.db')
                # If file doesn't exist, it will be created by SQLAlchemy
                
                logger.info(f"Ensuring SQLite database file has proper permissions: {db_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring tables exist: {e}")
        return False

@dashboard.route('/')
@dashboard.route('/index')
@login_required
def index():
    """
    Dashboard home page.
    """
    latest_snapshot = None
    recent_trades = []
    recent_signals = []
    portfolio_data = []
    portfolio_chart = {}

    try:
        # Ensure database tables exist
        ensure_tables_exist()
        
        session = get_session()

        try:
            # Get latest portfolio snapshot
            latest_snapshot = session.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.timestamp.desc()
            ).first()
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error getting portfolio snapshot: {db_err}")
            flash("Could not load portfolio data. Database may need initialization.", "warning")

        try:
            # Get recent trades
            recent_trades = session.query(Trade).order_by(
                Trade.timestamp.desc()
            ).limit(10).all()
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error getting recent trades: {db_err}")
            recent_trades = []

        try:
            # Get recent signals
            recent_signals = session.query(SignalLog).order_by(
                SignalLog.timestamp.desc()
            ).limit(10).all()
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error getting recent signals: {db_err}")
            recent_signals = []

        try:
            # Get portfolio performance data for chart
            portfolio_data = session.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.timestamp.asc()
            ).all()
            
            # Create portfolio value chart
            portfolio_chart = create_portfolio_chart(portfolio_data)
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error getting portfolio data: {db_err}")
            portfolio_data = []
            portfolio_chart = {}

        return render_template(
            'index.html',
            title='Dashboard',
            latest_snapshot=latest_snapshot,
            recent_trades=recent_trades,
            recent_signals=recent_signals,
            portfolio_chart=portfolio_chart
        )
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in index route: {e}\n{error_details}")
        return render_template(
            'errors/500.html', 
            error=f"Dashboard error: {str(e)}", 
            details="Check server logs for more information."
        ), 500

@dashboard.route('/portfolio')
@login_required
def portfolio():
    """
    Portfolio page showing detailed holdings and performance.
    """
    # Initialize variables with default values
    portfolio_data = []
    latest_snapshot = None
    portfolio_chart = {}
    allocation_chart = None
    exchanges = {}
    performance_data = {
        'daily_change': 0.0,
        'weekly_change': 0.0
    }
    
    try:
        # Ensure database tables exist
        ensure_tables_exist()
        
        session = get_session()

        try:
            # Get portfolio snapshots for chart
            portfolio_data = session.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.timestamp.asc()
            ).all()

            # Get latest portfolio snapshot
            latest_snapshot = session.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.timestamp.desc()
            ).first()

            # Create portfolio value chart
            portfolio_chart = create_portfolio_chart(portfolio_data)
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error retrieving portfolio data: {db_err}")
            flash("Could not load portfolio data. Database may need initialization.", "warning")
            portfolio_data = []
            latest_snapshot = None
            portfolio_chart = {}
        
        try:
            # Calculate performance metrics if we have the data
            if latest_snapshot and portfolio_data:
                # Try to find snapshot from yesterday for daily change
                one_day_ago = datetime.now() - timedelta(days=1)
                day_snapshot = session.query(PortfolioSnapshot).filter(
                    PortfolioSnapshot.timestamp <= one_day_ago
                ).order_by(PortfolioSnapshot.timestamp.desc()).first()
                
                if day_snapshot and day_snapshot.total_value > 0:
                    daily_change = ((latest_snapshot.total_value - day_snapshot.total_value) / day_snapshot.total_value) * 100
                    performance_data['daily_change'] = daily_change
                
                # Try to find snapshot from a week ago for weekly change
                one_week_ago = datetime.now() - timedelta(days=7)
                week_snapshot = session.query(PortfolioSnapshot).filter(
                    PortfolioSnapshot.timestamp <= one_week_ago
                ).order_by(PortfolioSnapshot.timestamp.desc()).first()
                
                if week_snapshot and week_snapshot.total_value > 0:
                    weekly_change = ((latest_snapshot.total_value - week_snapshot.total_value) / week_snapshot.total_value) * 100
                    performance_data['weekly_change'] = weekly_change
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            # Keep default values in performance_data

        # Get current balances from all exchanges
        allocation_data = {}
        
        # Try to get exchange info from config
        exchange_name = config.TRADING_EXCHANGE
        if exchange_name:
            try:
                exchange = ExchangeFactory.create_exchange_from_config(exchange_name)
                if exchange:
                    balances = []
                    total_value = 0.0
                    
                    # Get balances for common cryptocurrencies
                    for currency in ['BTC', 'ETH', 'USDT', 'USD', 'BNB', 'ADA', 'SOL', 'DOT', 'XRP']:
                        try:
                            balance = exchange.get_balance(currency)
                            if balance and balance > 0:
                                # Get current price if possible
                                price = 0
                                value_usd = 0
                                try:
                                    if currency != 'USDT' and currency != 'USD':
                                        ticker = exchange.get_ticker(f"{currency}/USDT")
                                        price = ticker.get('last', 0)
                                        value_usd = balance * price
                                    else:
                                        # Stablecoins have value of 1 USD
                                        price = 1
                                        value_usd = balance
                                except Exception:
                                    pass
                                
                                balances.append({
                                    'currency': currency,
                                    'balance': balance,
                                    'price': price,
                                    'value_usd': value_usd
                                })
                                
                                total_value += value_usd
                                allocation_data[currency] = value_usd
                        except Exception as currency_err:
                            logger.error(f"Error getting balance for {currency}: {currency_err}")
                    
                    exchanges[exchange_name] = balances
            except Exception as e:
                logger.error(f"Error initializing exchange: {e}")

        # Create asset allocation chart
        if allocation_data:
            try:
                # Filter out very small allocations
                allocation_data = {k: v for k, v in allocation_data.items() if v > 0.01}
                
                labels = list(allocation_data.keys())
                values = list(allocation_data.values())
                
                # Create pie chart
                trace = go.Pie(
                    labels=labels,
                    values=values,
                    textinfo='label+percent',
                    marker=dict(
                        colors=[
                            '#FF9900', '#3366CC', '#DC3912', '#109618', 
                            '#990099', '#0099C6', '#DD4477', '#66AA00',
                            '#B82E2E', '#316395'
                        ]
                    )
                )
                
                layout = go.Layout(
                    title='Asset Allocation',
                    template='plotly_dark'
                )
                
                fig = go.Figure(data=[trace], layout=layout)
                allocation_chart = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            except Exception as chart_err:
                logger.error(f"Error creating allocation chart: {chart_err}")
                allocation_chart = None

        return render_template(
            'portfolio.html',
            title='Portfolio',
            portfolio_data=portfolio_data,
            latest_snapshot=latest_snapshot,
            portfolio_chart=portfolio_chart,
            allocation_chart=allocation_chart,
            exchanges=exchanges,
            performance_data=performance_data
        )
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in portfolio route: {e}\n{error_details}")
        return render_template(
            'errors/500.html', 
            error=f"Portfolio error: {str(e)}", 
            details="Check server logs for more information."
        ), 500

@dashboard.route('/signals')
@login_required
def signals():
    """
    Trading signals page.
    """
    # Initialize with default values
    signals = []
    strategies = {}
    signal_stats = {
        'total': 0,
        'buy': 0,
        'sell': 0,
        'executed': 0,
        'execution_rate': 0
    }
    
    try:
        # Ensure database tables exist
        ensure_tables_exist()
        
        session = get_session()

        try:
            # Get all signals
            signals = session.query(SignalLog).order_by(
                SignalLog.timestamp.desc()
            ).limit(100).all()

            # Group signals by strategy
            strategies = {}
            for signal in signals:
                if signal.strategy not in strategies:
                    strategies[signal.strategy] = []
                strategies[signal.strategy].append(signal)

            # Create signal stats
            total_signals = len(signals)
            buy_signals = sum(1 for s in signals if s.signal_type == 'buy')
            sell_signals = sum(1 for s in signals if s.signal_type == 'sell')
            executed_signals = sum(1 for s in signals if s.executed)
            
            signal_stats = {
                'total': total_signals,
                'buy': buy_signals,
                'sell': sell_signals,
                'executed': executed_signals,
                'execution_rate': (executed_signals / total_signals * 100) if total_signals > 0 else 0
            }
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error getting signals data: {db_err}")
            flash("Could not load signals data. Database may need initialization.", "warning")

        return render_template(
            'signals.html',
            title='Trading Signals',
            signals=signals,
            strategies=strategies,
            signal_stats=signal_stats
        )
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in signals route: {e}\n{error_details}")
        return render_template(
            'errors/500.html', 
            error=f"Signals error: {str(e)}", 
            details="Check server logs for more information."
        ), 500

@dashboard.route('/trades')
@login_required
def trades():
    """
    Trades page.
    """
    # Initialize with default values
    trades = []
    trade_stats = {
        'total': 0,
        'buys': 0,
        'sells': 0,
        'volume': 0,
        'fees': 0
    }
    
    try:
        # Ensure database tables exist
        ensure_tables_exist()
        
        session = get_session()

        try:
            # Get all trades
            trades = session.query(Trade).order_by(
                Trade.timestamp.desc()
            ).limit(100).all()

            # Calculate trade statistics
            total_trades = len(trades)
            buy_trades = sum(1 for t in trades if t.side == 'buy')
            sell_trades = sum(1 for t in trades if t.side == 'sell')
            
            # Calculate total volume and fees
            total_volume = sum(t.value for t in trades) if trades else 0
            total_fees = sum(t.fee for t in trades) if trades else 0

            trade_stats = {
                'total': total_trades,
                'buys': buy_trades,
                'sells': sell_trades,
                'volume': total_volume,
                'fees': total_fees
            }
        except (OperationalError, SQLAlchemyError) as db_err:
            logger.error(f"Database error getting trades data: {db_err}")
            flash("Could not load trades data. Database may need initialization.", "warning")

        return render_template(
            'trades.html',
            title='Trades',
            trades=trades,
            trade_stats=trade_stats
        )
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in trades route: {e}\n{error_details}")
        return render_template(
            'errors/500.html', 
            error=f"Trades error: {str(e)}", 
            details="Check server logs for more information."
        ), 500

@dashboard.route('/settings')
@login_required
def settings():
    """
    View and update settings.
    """
    try:
        # Ensure database tables exist
        ensure_tables_exist()
        
        # Get current settings from config
        settings = {
            'PAPER_TRADING': config.PAPER_TRADING,
            'TRADING_SYMBOL': config.TRADING_SYMBOL,
            'INITIAL_CAPITAL': config.INITIAL_CAPITAL,
            'LOW_RISK_STOP_LOSS': config.LOW_RISK_STOP_LOSS,
            'MEDIUM_RISK_STOP_LOSS': config.MEDIUM_RISK_STOP_LOSS,
            'HIGH_RISK_STOP_LOSS': config.HIGH_RISK_STOP_LOSS,
            'MEDIUM_RISK_LEVERAGE': config.MEDIUM_RISK_LEVERAGE,
            'HIGH_RISK_LEVERAGE': config.HIGH_RISK_LEVERAGE,
            'TAKER_FEE': config.TAKER_FEE,
            'MAKER_FEE': config.MAKER_FEE,
            'MAX_PORTFOLIO_DRAWDOWN': config.MAX_PORTFOLIO_DRAWDOWN,
            'MAX_CORRELATION': config.MAX_CORRELATION,
            'MAX_ALLOCATION_PER_ASSET': config.MAX_ALLOCATION_PER_ASSET,
            'RISK_FREE_RATE': config.RISK_FREE_RATE,
            'PROFIT_THRESHOLD': config.PROFIT_THRESHOLD,
            'PROFIT_WITHDRAWAL_PERCENTAGE': config.PROFIT_WITHDRAWAL_PERCENTAGE,
        }

        # Add user settings section
        user_settings = {
            'username': current_user.username,
            'email': current_user.email if hasattr(current_user, 'email') else 'Not set',
        }
        
        # Get current exchange
        exchange = None
        assets = []
        exchange_name = config.TRADING_EXCHANGE
        
        if exchange_name:
            try:
                exchange = ExchangeFactory.create_exchange_from_config(exchange_name)
                
                # Get balances for common cryptocurrencies
                if exchange:
                    for currency in ['BTC', 'ETH', 'USDT', 'USD', 'BNB', 'ADA', 'SOL', 'DOT', 'XRP']:
                        try:
                            balance = exchange.get_balance(currency)
                            if balance and balance > 0:
                                # Get current price if possible
                                price = 0
                                try:
                                    if currency != 'USDT' and currency != 'USD':
                                        ticker = exchange.get_ticker(f"{currency}/USDT")
                                        price = ticker.get('last', 0)
                                except Exception:
                                    # If price fetch fails, use 0
                                    pass
                                
                                assets.append({
                                    'currency': currency,
                                    'balance': balance,
                                    'price': price,
                                    'value_usd': balance * price if price > 0 and currency not in ['USDT', 'USD'] else balance
                                })
                        except Exception:
                            # Skip currencies that cause errors
                            continue
            except Exception as e:
                logger.error(f"Error initializing exchange: {e}")

        return render_template(
            'settings.html',
            title='Settings',
            settings=settings,
            user_settings=user_settings,
            is_paper_trading=config.PAPER_TRADING,
            assets=assets,
            exchange_name=exchange_name
        )
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in settings route: {e}\n{error_details}")
        return render_template(
            'errors/500.html', 
            error=f"Settings error: {str(e)}", 
            details="Check server logs for more information."
        ), 500

@dashboard.route('/user_settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    """
    View and update user settings.
    """
    try:
        if request.method == 'POST':
            # Handle form submission
            email = request.form.get('email')
            if email and email != current_user.email:
                # Update user email
                current_user.email = email
                session = get_session()
                session.commit()
                flash('Email updated successfully.', 'success')

            # Check if password update requested
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if current_password and new_password and confirm_password:
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect.', 'danger')
                elif new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                else:
                    current_user.set_password(new_password)
                    session = get_session()
                    session.commit()
                    flash('Password updated successfully.', 'success')

            return redirect(url_for('dashboard.user_settings'))

        return render_template(
            'user_settings.html',
            title='User Settings',
            user=current_user
        )
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in user_settings route: {e}\n{error_details}")
        return render_template('errors/500.html', error=str(e)), 500

@dashboard.route('/api/portfolio/history')
@login_required
def api_portfolio_history():
    """
    API endpoint to get portfolio history data.
    """
    try:
        session = get_session()

        # Get portfolio history
        portfolio_data = session.query(PortfolioSnapshot).order_by(
            PortfolioSnapshot.timestamp.asc()
        ).all()

        result = [snapshot.to_dict() for snapshot in portfolio_data]
        return jsonify(result)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in api_portfolio_history route: {e}\n{error_details}")
        return jsonify({'error': str(e)}), 500

@dashboard.route('/api/trades')
@login_required
def api_trades():
    """
    API endpoint to get trade data.
    """
    try:
        session = get_session()

        # Get all trades
        trades = session.query(Trade).order_by(
            Trade.timestamp.desc()
        ).all()

        result = [trade.to_dict() for trade in trades]
        return jsonify(result)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in api_trades route: {e}\n{error_details}")
        return jsonify({'error': str(e)}), 500

@dashboard.route('/api/signals')
@login_required
def api_signals():
    """
    API endpoint to get signal data.
    """
    try:
        session = get_session()

        # Get all signals
        signals = session.query(SignalLog).order_by(
            SignalLog.timestamp.desc()
        ).all()

        result = [signal.to_dict() for signal in signals]
        return jsonify(result)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in api_signals route: {e}\n{error_details}")
        return jsonify({'error': str(e)}), 500

@dashboard.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring the system's status.
    Returns different status codes based on health:
    - 200: All systems operational
    - 503: One or more components degraded
    """
    health = {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'components': {}
    }
    
    try:
        # Check database connection
        session = get_session()
        try:
            session.execute(text('SELECT 1'))
            health['components']['database'] = {'status': 'ok'}
        except Exception as e:
            health['components']['database'] = {
                'status': 'error',
                'message': str(e)
            }
            health['status'] = 'degraded'
        finally:
            session.close()
        
        # Check exchange connections
        health['components']['exchanges'] = {}
        exchanges = ['binance', 'coinbase', 'kraken', 'gemini', 'kucoin']
        
        for exchange_name in exchanges:
            try:
                exchange = ExchangeFactory.create_exchange(exchange_name, paper_trading=True)
                if exchange and exchange.connect():
                    health['components']['exchanges'][exchange_name] = {'status': 'ok'}
                else:
                    health['components']['exchanges'][exchange_name] = {
                        'status': 'error', 
                        'message': 'Connection failed'
                    }
                    health['status'] = 'degraded'
            except Exception as e:
                health['components']['exchanges'][exchange_name] = {
                    'status': 'error', 
                    'message': str(e)
                }
                health['status'] = 'degraded'
        
        # Check service monitor status
        try:
            from src.utils.status_monitor import get_service_status
            services = get_service_status()
            health['components']['services'] = services
            
            if any(s.get('status') == 'down' for s in services.values()):
                health['status'] = 'degraded'
        except Exception as e:
            health['components']['services'] = {
                'status': 'error',
                'message': str(e)
            }
            health['status'] = 'degraded'
            
        # Return different status code based on health
        status_code = 200 if health['status'] == 'ok' else 503
        return jsonify(health), status_code
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in health check endpoint: {e}\n{error_details}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'message': str(e)
        }), 500
