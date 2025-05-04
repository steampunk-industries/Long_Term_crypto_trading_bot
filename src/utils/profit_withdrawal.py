"""
Profit withdrawal module for the crypto trading bot.
Implements the 50% profit withdrawal strategy once a bot reaches $50K.
"""

import datetime
import os
import time
from typing import Dict, Any, List, Optional

import pandas as pd

from src.config import settings
from src.utils.logging import logger
from src.utils.database import get_db_session, BotPerformance, ProfitWithdrawal

class ProfitWithdrawalManager:
    """Manager for implementing the profit withdrawal strategy."""

    def __init__(
        self,
        profit_threshold: float = None,  # $50K threshold
        withdrawal_percentage: float = None,  # 50% of daily profits
    ):
        """
        Initialize the profit withdrawal manager.

        Args:
            profit_threshold: Threshold in USD for starting profit withdrawals.
            withdrawal_percentage: Percentage of daily profits to withdraw.
        """
        self.profit_threshold = profit_threshold or settings.portfolio.profit_threshold
        self.withdrawal_percentage = withdrawal_percentage or settings.portfolio.profit_withdrawal_percentage
        self.thresholds_reached = {
            "low_risk": False,
            "medium_risk": False,
            "high_risk": False,
        }
        self.last_withdrawal_date = {
            "low_risk": None,
            "medium_risk": None,
            "high_risk": None,
        }
        self.total_withdrawn = {
            "low_risk": 0.0,
            "medium_risk": 0.0,
            "high_risk": 0.0,
        }

    def check_threshold(self, bot_type: str, current_balance: float) -> bool:
        """
        Check if a bot has reached the profit threshold.

        Args:
            bot_type: The bot type (low_risk, medium_risk, high_risk).
            current_balance: Current balance of the bot.

        Returns:
            True if threshold is reached, False otherwise.
        """
        # If already reached, return True
        if self.thresholds_reached.get(bot_type, False):
            return True

        # Check if balance exceeds threshold
        if current_balance >= self.profit_threshold:
            logger.info(f"{bot_type} bot has reached the ${self.profit_threshold:,.2f} threshold")
            self.thresholds_reached[bot_type] = True
            return True

        return False

    def calculate_daily_profit(self, bot_type: str, current_balance: float) -> float:
        """
        Calculate daily profit for a bot.

        Args:
            bot_type: The bot type (low_risk, medium_risk, high_risk).
            current_balance: Current balance of the bot.

        Returns:
            Daily profit amount.
        """
        try:
            # Get database session
            session = get_db_session()

            # Get yesterday's balance
            yesterday = datetime.datetime.now().date() - datetime.timedelta(days=1)
            yesterday_performance = (
                session.query(BotPerformance)
                .filter(
                    BotPerformance.bot_type == bot_type,
                    BotPerformance.timestamp >= yesterday,
                )
                .order_by(BotPerformance.timestamp.asc())
                .first()
            )

            if yesterday_performance is None:
                logger.warning(f"No performance data found for {bot_type} bot yesterday")
                return 0.0

            yesterday_balance = yesterday_performance.balance
            daily_profit = current_balance - yesterday_balance

            logger.info(f"{bot_type} bot daily profit: ${daily_profit:,.2f}")
            return daily_profit

        except Exception as e:
            logger.error(f"Error calculating daily profit for {bot_type} bot: {e}")
            return 0.0
        finally:
            session.close()

    def process_withdrawal(self, bot_type: str, current_balance: float) -> float:
        """
        Process profit withdrawal for a bot if conditions are met.

        Args:
            bot_type: The bot type (low_risk, medium_risk, high_risk).
            current_balance: Current balance of the bot.

        Returns:
            Amount withdrawn.
        """
        try:
            # Check if threshold is reached
            if not self.check_threshold(bot_type, current_balance):
                return 0.0

            # Check if we already processed withdrawal today
            today = datetime.datetime.now().date()
            if self.last_withdrawal_date.get(bot_type) == today:
                return 0.0

            # Calculate daily profit
            daily_profit = self.calculate_daily_profit(bot_type, current_balance)

            # Only withdraw if profit is positive
            if daily_profit <= 0:
                logger.info(f"No profit to withdraw for {bot_type} bot today")
                return 0.0

            # Calculate withdrawal amount
            withdrawal_amount = daily_profit * self.withdrawal_percentage

            # Record withdrawal
            self._record_withdrawal(bot_type, withdrawal_amount)

            # Update last withdrawal date
            self.last_withdrawal_date[bot_type] = today

            # Update total withdrawn
            self.total_withdrawn[bot_type] += withdrawal_amount

            logger.info(
                f"Withdrew ${withdrawal_amount:,.2f} from {bot_type} bot "
                f"({self.withdrawal_percentage:.0%} of ${daily_profit:,.2f} daily profit)"
            )
            logger.info(f"Total withdrawn from {bot_type} bot: ${self.total_withdrawn[bot_type]:,.2f}")

            return withdrawal_amount

        except Exception as e:
            logger.error(f"Error processing withdrawal for {bot_type} bot: {e}")
            return 0.0

    def _record_withdrawal(self, bot_type: str, amount: float) -> None:
        """
        Record a profit withdrawal in the database.

        Args:
            bot_type: The bot type (low_risk, medium_risk, high_risk).
            amount: Withdrawal amount.
        """
        try:
            # Get database session
            session = get_db_session()

            # Create withdrawal record
            withdrawal = ProfitWithdrawal(
                bot_type=bot_type,
                amount=amount,
                timestamp=datetime.datetime.now(),
            )

            # Add to database
            session.add(withdrawal)
            session.commit()

        except Exception as e:
            logger.error(f"Error recording withdrawal for {bot_type} bot: {e}")
        finally:
            session.close()

    def get_withdrawal_summary(self) -> Dict[str, Any]:
        """
        Get summary of profit withdrawals.

        Returns:
            Dictionary with withdrawal summary.
        """
        try:
            # Get database session
            session = get_db_session()

            # Get all withdrawals
            withdrawals = session.query(ProfitWithdrawal).all()

            # Calculate total withdrawn per bot
            total_per_bot = {}
            for bot_type in ["low_risk", "medium_risk", "high_risk"]:
                bot_withdrawals = [w for w in withdrawals if w.bot_type == bot_type]
                total_per_bot[bot_type] = sum(w.amount for w in bot_withdrawals)

            # Calculate total withdrawn
            total_withdrawn = sum(total_per_bot.values())

            # Get recent withdrawals
            recent_withdrawals = (
                session.query(ProfitWithdrawal)
                .order_by(ProfitWithdrawal.timestamp.desc())
                .limit(10)
                .all()
            )

            return {
                "total_withdrawn": total_withdrawn,
                "total_per_bot": total_per_bot,
                "thresholds_reached": self.thresholds_reached,
                "recent_withdrawals": [
                    {
                        "bot_type": w.bot_type,
                        "amount": w.amount,
                        "timestamp": w.timestamp.isoformat(),
                    }
                    for w in recent_withdrawals
                ],
            }

        except Exception as e:
            logger.error(f"Error getting withdrawal summary: {e}")
            return {
                "total_withdrawn": 0.0,
                "total_per_bot": {
                    "low_risk": 0.0,
                    "medium_risk": 0.0,
                    "high_risk": 0.0,
                },
                "thresholds_reached": self.thresholds_reached,
                "recent_withdrawals": [],
                "error": str(e),
            }
        finally:
            session.close()


# Create a global profit withdrawal manager instance
profit_withdrawal_manager = ProfitWithdrawalManager()
