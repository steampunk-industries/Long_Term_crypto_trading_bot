"""
Sentiment analysis module for the crypto trading bot.
Provides sentiment analysis from social media and news sources.
"""

import datetime
import re
import time
from typing import Dict, Any, List, Optional, Tuple, Union

import requests
import pandas as pd
import numpy as np
from textblob import TextBlob

from src.config import settings
from src.utils.logging import logger


class SentimentProvider:
    """Base class for sentiment data providers."""

    def __init__(self, api_key: str = None):
        """
        Initialize the sentiment provider.

        Args:
            api_key: API key for the data provider.
        """
        self.api_key = api_key
        self.cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 1800  # 30 minutes in seconds

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from the provider.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        raise NotImplementedError("Subclasses must implement get_data")

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if available and not expired.

        Args:
            cache_key: Cache key.

        Returns:
            Cached data or None if not available.
        """
        current_time = time.time()
        if cache_key in self.cache and current_time - self.cache_expiry.get(cache_key, 0) < self.cache_ttl:
            return self.cache[cache_key]
        return None

    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store data in cache.

        Args:
            cache_key: Cache key.
            data: Data to cache.
        """
        self.cache[cache_key] = data
        self.cache_expiry[cache_key] = time.time()


class TwitterProvider(SentimentProvider):
    """Twitter/X sentiment data provider."""

    def __init__(self, api_key: str = None, api_secret: str = None, bearer_token: str = None):
        """
        Initialize the Twitter provider.

        Args:
            api_key: Twitter API key.
            api_secret: Twitter API secret.
            bearer_token: Twitter bearer token.
        """
        super().__init__(api_key)
        self.base_url = "https://api.twitter.com/2"
        self.api_key = api_key or settings.sentiment.twitter_api_key
        self.api_secret = api_secret or settings.sentiment.twitter_api_secret
        self.bearer_token = bearer_token or settings.sentiment.twitter_bearer_token

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from Twitter.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        params = params or {}
        
        # Create cache key
        cache_key = f"twitter_{endpoint}_{str(params)}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Make request
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Cache data
            self._store_in_cache(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get data from Twitter: {e}")
            return {}

    def search_tweets(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for tweets.

        Args:
            query: Search query.
            max_results: Maximum number of results.

        Returns:
            List of tweets.
        """
        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,lang",
        }
        
        data = self.get_data("tweets/search/recent", params)
        
        if not data or "data" not in data:
            return []
        
        return data["data"]


class RedditProvider(SentimentProvider):
    """Reddit sentiment data provider."""

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        user_agent: str = "crypto_trading_bot/1.0",
    ):
        """
        Initialize the Reddit provider.

        Args:
            client_id: Reddit client ID.
            client_secret: Reddit client secret.
            user_agent: User agent string.
        """
        super().__init__(client_id)
        self.base_url = "https://oauth.reddit.com"
        self.client_id = client_id or settings.sentiment.reddit_client_id
        self.client_secret = client_secret or settings.sentiment.reddit_client_secret
        self.user_agent = user_agent
        self.access_token = None
        self.token_expiry = 0

    def _get_access_token(self) -> str:
        """
        Get an access token from Reddit.

        Returns:
            Access token.
        """
        current_time = time.time()
        
        # Return cached token if still valid
        if self.access_token and current_time < self.token_expiry:
            return self.access_token
        
        # Get new token
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "client_credentials",
        }
        headers = {
            "User-Agent": self.user_agent,
        }
        
        try:
            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data=data,
                headers=headers,
            )
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data["access_token"]
            self.token_expiry = current_time + token_data["expires_in"] - 60  # Subtract 60s for safety
            
            return self.access_token
        except Exception as e:
            logger.error(f"Failed to get Reddit access token: {e}")
            return None

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from Reddit.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        params = params or {}
        
        # Create cache key
        cache_key = f"reddit_{endpoint}_{str(params)}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Get access token
        access_token = self._get_access_token()
        if not access_token:
            return {}
        
        # Make request
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": self.user_agent,
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Cache data
            self._store_in_cache(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get data from Reddit: {e}")
            return {}

    def search_subreddit(self, subreddit: str, query: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for posts in a subreddit.

        Args:
            subreddit: Subreddit name.
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of posts.
        """
        params = {
            "limit": limit,
        }
        
        if query:
            endpoint = f"r/{subreddit}/search"
            params["q"] = query
            params["restrict_sr"] = "on"
        else:
            endpoint = f"r/{subreddit}/hot"
        
        data = self.get_data(endpoint, params)
        
        if not data or "data" not in data or "children" not in data["data"]:
            return []
        
        return [post["data"] for post in data["data"]["children"]]


class NewsProvider(SentimentProvider):
    """News sentiment data provider."""

    def __init__(self, api_key: str = None):
        """
        Initialize the news provider.

        Args:
            api_key: News API key.
        """
        super().__init__(api_key)
        self.base_url = "https://newsapi.org/v2"
        self.api_key = api_key or settings.sentiment.news_api_key

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get data from News API.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        params = params or {}
        params["apiKey"] = self.api_key
        
        # Create cache key
        cache_key = f"news_{endpoint}_{str(params)}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Make request
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cache data
            self._store_in_cache(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get data from News API: {e}")
            return {}

    def search_news(self, query: str, from_date: str = None, to_date: str = None, language: str = "en") -> List[Dict[str, Any]]:
        """
        Search for news articles.

        Args:
            query: Search query.
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
            language: Language code.

        Returns:
            List of news articles.
        """
        params = {
            "q": query,
            "language": language,
            "sortBy": "publishedAt",
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        data = self.get_data("everything", params)
        
        if not data or "articles" not in data:
            return []
        
        return data["articles"]


class FearGreedIndexProvider(SentimentProvider):
    """Fear & Greed Index sentiment data provider."""

    def __init__(self):
        """Initialize the Fear & Greed Index provider."""
        super().__init__(None)

    def get_data(self, endpoint: str = "fng", params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get Fear & Greed Index data.

        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Response data.
        """
        # Create cache key
        cache_key = f"feargreed_{endpoint}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Make request
        url = "https://api.alternative.me/fng/"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Cache data
            self._store_in_cache(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get Fear & Greed Index: {e}")
            return {}

    def get_fear_greed_index(self) -> Tuple[float, str]:
        """
        Get the Fear & Greed Index.

        Returns:
            Tuple of (index_value, classification).
        """
        data = self.get_data()
        
        if not data or "data" not in data or len(data["data"]) == 0:
            return 50, "Neutral"  # Default to neutral if no data
        
        index_value = int(data["data"][0]["value"])
        classification = data["data"][0]["value_classification"]
        
        return index_value, classification


class VolumeSentimentProvider(SentimentProvider):
    """Volume-based sentiment analysis."""

    def __init__(self, exchange_name: str = "binance"):
        """Initialize the volume sentiment provider."""
        super().__init__(None)
        self.exchange_name = exchange_name
        from src.exchange.wrapper import ExchangeWrapper
        self.exchange = ExchangeWrapper(exchange_name)

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        This method is required by the parent class but not used directly.
        
        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Empty dictionary.
        """
        return {}

    def get_volume_sentiment(self, asset: str) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze trading volume patterns to approximate sentiment.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (sentiment_score, sentiment_data).
        """
        try:
            # Get historical OHLCV data
            symbol = f"{asset}/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1h", limit=48)
            
            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Calculate price change
            df["price_change"] = df["close"].pct_change()
            
            # Calculate volume change
            df["volume_change"] = df["volume"].pct_change()
            
            # Calculate volume z-score (how many standard deviations from mean)
            volume_mean = df["volume"].mean()
            volume_std = df["volume"].std()
            df["volume_zscore"] = (df["volume"] - volume_mean) / volume_std if volume_std > 0 else 0
            
            # Get the most recent data
            recent_df = df.tail(12)  # Last 12 hours
            
            # Calculate average volume, price change and volume z-score
            avg_volume = recent_df["volume"].mean()
            avg_price_change = recent_df["price_change"].mean()
            avg_volume_zscore = recent_df["volume_zscore"].mean()
            
            # Calculate volume/price correlation
            correlation = recent_df["volume_change"].corr(recent_df["price_change"])
            
            # Determine sentiment
            # High volume + positive price change = positive sentiment
            # High volume + negative price change = negative sentiment
            if abs(correlation) < 0.3:
                # Low correlation means volume and price aren't related (neutral)
                sentiment_score = 0
                sentiment_type = "Neutral volume pattern"
            else:
                # Calculate sentiment score based on volume z-score and correlation
                sentiment_score = avg_volume_zscore * correlation
                sentiment_score = max(min(sentiment_score, 1), -1)  # Clamp between -1 and 1
                
                if sentiment_score > 0.5:
                    sentiment_type = "Strong buying volume (bullish)"
                elif sentiment_score > 0.2:
                    sentiment_type = "Moderate buying volume (slightly bullish)"
                elif sentiment_score < -0.5:
                    sentiment_type = "Strong selling volume (bearish)"
                elif sentiment_score < -0.2:
                    sentiment_type = "Moderate selling volume (slightly bearish)"
                else:
                    sentiment_type = "Neutral volume pattern"
            
            return sentiment_score, {
                "sentiment_score": sentiment_score,
                "sentiment_type": sentiment_type,
                "volume_zscore": avg_volume_zscore,
                "price_change": avg_price_change,
                "volume_price_correlation": correlation,
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze volume sentiment: {e}")
            return 0, {"error": str(e)}


class TechnicalSentimentProvider(SentimentProvider):
    """Technical analysis based sentiment provider."""

    def __init__(self, exchange_name: str = "binance"):
        """Initialize the technical sentiment provider."""
        super().__init__(None)
        self.exchange_name = exchange_name
        from src.exchange.wrapper import ExchangeWrapper
        self.exchange = ExchangeWrapper(exchange_name)

    def get_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        This method is required by the parent class but not used directly.
        
        Args:
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Empty dictionary.
        """
        return {}

    def get_technical_sentiment(self, asset: str) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze technical indicators to approximate sentiment.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (sentiment_score, sentiment_data).
        """
        try:
            # Get historical OHLCV data
            symbol = f"{asset}/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1h", limit=100)
            
            # Create DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Calculate RSI
            from ta.momentum import RSIIndicator
            rsi_indicator = RSIIndicator(close=df["close"], window=14)
            df["rsi"] = rsi_indicator.rsi()
            
            # Calculate MACD
            from ta.trend import MACD
            macd_indicator = MACD(close=df["close"])
            df["macd"] = macd_indicator.macd()
            df["macd_signal"] = macd_indicator.macd_signal()
            df["macd_diff"] = macd_indicator.macd_diff()
            
            # Calculate Bollinger Bands
            from ta.volatility import BollingerBands
            bollinger_indicator = BollingerBands(close=df["close"])
            df["bb_high"] = bollinger_indicator.bollinger_hband()
            df["bb_low"] = bollinger_indicator.bollinger_lband()
            df["bb_mavg"] = bollinger_indicator.bollinger_mavg()
            
            # Get the most recent values
            latest = df.iloc[-1]
            
            # Determine RSI sentiment
            if latest["rsi"] > 70:
                rsi_sentiment = -0.7  # Overbought (bearish)
                rsi_signal = "Overbought"
            elif latest["rsi"] < 30:
                rsi_sentiment = 0.7   # Oversold (bullish)
                rsi_signal = "Oversold"
            elif latest["rsi"] > 60:
                rsi_sentiment = -0.3  # Approaching overbought
                rsi_signal = "Approaching overbought"
            elif latest["rsi"] < 40:
                rsi_sentiment = 0.3   # Approaching oversold
                rsi_signal = "Approaching oversold"
            else:
                rsi_sentiment = 0     # Neutral
                rsi_signal = "Neutral"
            
            # Determine MACD sentiment
            if latest["macd"] > latest["macd_signal"] and latest["macd_diff"] > 0:
                macd_sentiment = 0.6  # Bullish
                macd_signal = "Bullish crossover"
            elif latest["macd"] < latest["macd_signal"] and latest["macd_diff"] < 0:
                macd_sentiment = -0.6 # Bearish
                macd_signal = "Bearish crossover"
            elif latest["macd"] > latest["macd_signal"]:
                macd_sentiment = 0.3  # Slightly bullish
                macd_signal = "Bullish"
            elif latest["macd"] < latest["macd_signal"]:
                macd_sentiment = -0.3 # Slightly bearish
                macd_signal = "Bearish"
            else:
                macd_sentiment = 0    # Neutral
                macd_signal = "Neutral"
            
            # Determine Bollinger Bands sentiment
            if latest["close"] > latest["bb_high"]:
                bb_sentiment = -0.5   # Price above upper band (potential reversal)
                bb_signal = "Above upper band"
            elif latest["close"] < latest["bb_low"]:
                bb_sentiment = 0.5    # Price below lower band (potential reversal)
                bb_signal = "Below lower band"
            else:
                bb_sentiment = 0      # Price within bands
                bb_signal = "Within bands"
            
            # Calculate combined sentiment
            combined_sentiment = (rsi_sentiment * 0.4) + (macd_sentiment * 0.4) + (bb_sentiment * 0.2)
            combined_sentiment = max(min(combined_sentiment, 1), -1)  # Clamp between -1 and 1
            
            if combined_sentiment > 0.5:
                sentiment_type = "Strongly bullish"
            elif combined_sentiment > 0.2:
                sentiment_type = "Moderately bullish"
            elif combined_sentiment < -0.5:
                sentiment_type = "Strongly bearish"
            elif combined_sentiment < -0.2:
                sentiment_type = "Moderately bearish"
            else:
                sentiment_type = "Neutral"
            
            return combined_sentiment, {
                "sentiment_score": combined_sentiment,
                "sentiment_type": sentiment_type,
                "rsi": {
                    "value": latest["rsi"],
                    "signal": rsi_signal,
                    "sentiment": rsi_sentiment
                },
                "macd": {
                    "value": latest["macd"],
                    "signal": macd_signal,
                    "sentiment": macd_sentiment
                },
                "bollinger_bands": {
                    "signal": bb_signal,
                    "sentiment": bb_sentiment
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze technical sentiment: {e}")
            return 0, {"error": str(e)}


class SentimentAnalyzer:
    """Sentiment analyzer for trading signals."""

    def __init__(self, use_alternative_data: bool = True):
        """Initialize the sentiment analyzer."""
        # Check if API keys are available
        twitter_available = bool(settings.sentiment.twitter_bearer_token)
        reddit_available = bool(settings.sentiment.reddit_client_id and settings.sentiment.reddit_client_secret)
        news_available = bool(settings.sentiment.news_api_key)
        
        # Initialize traditional providers only if API keys are available and alternative data not requested
        if not use_alternative_data:
            self.twitter_provider = TwitterProvider() if twitter_available else None
            self.reddit_provider = RedditProvider() if reddit_available else None
            self.news_provider = NewsProvider() if news_available else None
        else:
            self.twitter_provider = None
            self.reddit_provider = None
            self.news_provider = None
        
        # Always initialize alternative data providers
        self.fear_greed_provider = FearGreedIndexProvider()
        self.volume_provider = VolumeSentimentProvider()
        self.technical_provider = TechnicalSentimentProvider()
        
        # Log availability
        if use_alternative_data or not any([twitter_available, reddit_available, news_available]):
            logger.info("Using alternative data sources for sentiment analysis")

    def analyze_text(self, text: str) -> Tuple[float, str]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze.

        Returns:
            Tuple of (sentiment_score, sentiment_label).
            Sentiment score is between -1 (negative) and 1 (positive).
        """
        # Clean text
        text = re.sub(r'http\S+', '', text)  # Remove URLs
        text = re.sub(r'@\w+', '', text)     # Remove mentions
        text = re.sub(r'#\w+', '', text)     # Remove hashtags
        text = re.sub(r'\s+', ' ', text)     # Normalize whitespace
        
        # Analyze sentiment
        blob = TextBlob(text)
        sentiment_score = blob.sentiment.polarity
        
        # Determine sentiment label
        if sentiment_score > 0.2:
            sentiment_label = "positive"
        elif sentiment_score < -0.2:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"
        
        return sentiment_score, sentiment_label

    def analyze_twitter_sentiment(self, asset: str) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze Twitter sentiment for an asset.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (sentiment_score, sentiment_data).
        """
        try:
            # Search for tweets
            query = f"{asset} OR #{asset} OR #{asset.lower()} OR #{asset}USD OR crypto"
            tweets = self.twitter_provider.search_tweets(query, max_results=100)
            
            if not tweets:
                return 0, {"error": "No tweets found"}
            
            # Analyze sentiment of each tweet
            sentiments = []
            for tweet in tweets:
                if "text" in tweet:
                    score, label = self.analyze_text(tweet["text"])
                    sentiments.append(score)
            
            # Calculate average sentiment
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Calculate sentiment distribution
            positive = sum(1 for s in sentiments if s > 0.2) / len(sentiments) if sentiments else 0
            negative = sum(1 for s in sentiments if s < -0.2) / len(sentiments) if sentiments else 0
            neutral = sum(1 for s in sentiments if -0.2 <= s <= 0.2) / len(sentiments) if sentiments else 0
            
            return avg_sentiment, {
                "average_sentiment": avg_sentiment,
                "sentiment_distribution": {
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                },
                "tweet_count": len(tweets),
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze Twitter sentiment: {e}")
            return 0, {"error": str(e)}

    def analyze_reddit_sentiment(self, asset: str) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze Reddit sentiment for an asset.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (sentiment_score, sentiment_data).
        """
        try:
            # Define relevant subreddits
            subreddits = ["cryptocurrency", f"{asset}", f"{asset}markets", "cryptomarkets"]
            
            all_posts = []
            for subreddit in subreddits:
                try:
                    posts = self.reddit_provider.search_subreddit(subreddit, query=asset, limit=25)
                    all_posts.extend(posts)
                except Exception as e:
                    logger.warning(f"Failed to get posts from r/{subreddit}: {e}")
            
            if not all_posts:
                return 0, {"error": "No Reddit posts found"}
            
            # Analyze sentiment of each post
            sentiments = []
            for post in all_posts:
                if "title" in post:
                    title_score, _ = self.analyze_text(post["title"])
                    sentiments.append(title_score)
                
                if "selftext" in post and post["selftext"]:
                    text_score, _ = self.analyze_text(post["selftext"])
                    sentiments.append(text_score)
            
            # Calculate average sentiment
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Calculate sentiment distribution
            positive = sum(1 for s in sentiments if s > 0.2) / len(sentiments) if sentiments else 0
            negative = sum(1 for s in sentiments if s < -0.2) / len(sentiments) if sentiments else 0
            neutral = sum(1 for s in sentiments if -0.2 <= s <= 0.2) / len(sentiments) if sentiments else 0
            
            return avg_sentiment, {
                "average_sentiment": avg_sentiment,
                "sentiment_distribution": {
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                },
                "post_count": len(all_posts),
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze Reddit sentiment: {e}")
            return 0, {"error": str(e)}

    def analyze_news_sentiment(self, asset: str) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze news sentiment for an asset.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (sentiment_score, sentiment_data).
        """
        try:
            # Get news articles
            query = f"{asset} OR cryptocurrency OR crypto"
            
            # Get date range for last 7 days
            to_date = datetime.datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            
            articles = self.news_provider.search_news(query, from_date=from_date, to_date=to_date)
            
            if not articles:
                return 0, {"error": "No news articles found"}
            
            # Analyze sentiment of each article
            sentiments = []
            for article in articles:
                if "title" in article:
                    title_score, _ = self.analyze_text(article["title"])
                    sentiments.append(title_score * 2)  # Give more weight to titles
                
                if "description" in article and article["description"]:
                    desc_score, _ = self.analyze_text(article["description"])
                    sentiments.append(desc_score)
            
            # Calculate average sentiment
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Calculate sentiment distribution
            positive = sum(1 for s in sentiments if s > 0.2) / len(sentiments) if sentiments else 0
            negative = sum(1 for s in sentiments if s < -0.2) / len(sentiments) if sentiments else 0
            neutral = sum(1 for s in sentiments if -0.2 <= s <= 0.2) / len(sentiments) if sentiments else 0
            
            return avg_sentiment, {
                "average_sentiment": avg_sentiment,
                "sentiment_distribution": {
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                },
                "article_count": len(articles),
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze news sentiment: {e}")
            return 0, {"error": str(e)}

    def get_fear_greed_sentiment(self) -> Tuple[float, Dict[str, Any]]:
        """
        Get sentiment based on Fear & Greed Index.

        Returns:
            Tuple of (sentiment_score, sentiment_data).
        """
        try:
            # Get Fear & Greed Index
            index_value, classification = self.fear_greed_provider.get_fear_greed_index()
            
            # Convert to sentiment score (-1 to 1)
            # 0-25 = Extreme Fear, 25-50 = Fear, 50-75 = Greed, 75-100 = Extreme Greed
            sentiment_score = (index_value - 50) / 50  # -1 to 1 scale
            
            # Apply contrarian interpretation
            # When Fear & Greed is showing extreme fear, it's actually a bullish signal
            contrarian_score = -sentiment_score
            
            if index_value <= 25:
                sentiment_type = "Extreme Fear (potentially bullish contrarian indicator)"
            elif index_value <= 50:
                sentiment_type = "Fear (slightly bullish contrarian indicator)"
            elif index_value <= 75:
                sentiment_type = "Greed (slightly bearish contrarian indicator)"
            else:
                sentiment_type = "Extreme Greed (potentially bearish contrarian indicator)"
            
            return contrarian_score, {
                "index_value": index_value,
                "classification": classification,
                "sentiment_score": sentiment_score,
                "contrarian_score": contrarian_score,
                "sentiment_type": sentiment_type,
            }
            
        except Exception as e:
            logger.error(f"Failed to get Fear & Greed sentiment: {e}")
            return 0, {"error": str(e)}

    def get_combined_sentiment(self, asset: str) -> Tuple[float, Dict[str, Any]]:
        """
        Get combined sentiment from all sources.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (combined_sentiment_score, sentiment_data).
        """
        sentiment_sources = {}
        scores = {}
        
        # Try to get sentiment from traditional sources if available
        if self.twitter_provider:
            scores["twitter"], sentiment_sources["twitter"] = self.analyze_twitter_sentiment(asset)
        
        if self.reddit_provider:
            scores["reddit"], sentiment_sources["reddit"] = self.analyze_reddit_sentiment(asset)
        
        if self.news_provider:
            scores["news"], sentiment_sources["news"] = self.analyze_news_sentiment(asset)
        
        # Always get alternative data source sentiment
        scores["fear_greed"], sentiment_sources["fear_greed"] = self.get_fear_greed_sentiment()
        scores["volume"], sentiment_sources["volume"] = self.volume_provider.get_volume_sentiment(asset)
        scores["technical"], sentiment_sources["technical"] = self.technical_provider.get_technical_sentiment(asset)
        
        # Set up weights based on available sources
        weights = {}
        
        # If traditional sources are available, give them some weight
        traditional_total = 0
        if "twitter" in scores and "error" not in sentiment_sources["twitter"]:
            weights["twitter"] = 0.2
            traditional_total += 0.2
        
        if "reddit" in scores and "error" not in sentiment_sources["reddit"]:
            weights["reddit"] = 0.1
            traditional_total += 0.1
        
        if "news" in scores and "error" not in sentiment_sources["news"]:
            weights["news"] = 0.1
            traditional_total += 0.1
        
        # Alternative sources get the remaining weight
        alt_weight = 1.0 - traditional_total
        weights["fear_greed"] = alt_weight * 0.3
        weights["volume"] = alt_weight * 0.3
        weights["technical"] = alt_weight * 0.4
        
        # Calculate combined score
        combined_score = 0
        for source, score in scores.items():
            if source in weights:
                combined_score += score * weights[source]
        
        # Determine sentiment label
        if combined_score > 0.2:
            sentiment_label = "bullish"
        elif combined_score < -0.2:
            sentiment_label = "bearish"
        else:
            sentiment_label = "neutral"
        
        return combined_score, {
            "combined_sentiment": combined_score,
            "sentiment_label": sentiment_label,
            "sources": sentiment_sources,
            "weights": weights,
        }

    def get_sentiment_signal(self, asset: str) -> Tuple[float, str]:
        """
        Get trading signal based on sentiment analysis.

        Args:
            asset: Asset symbol (e.g., BTC).

        Returns:
            Tuple of (signal_strength, signal_type).
            Signal strength is between -1 and 1, where:
            - Negative values indicate bearish signals
            - Positive values indicate bullish signals
            - Magnitude indicates strength
            Signal type is a string description of the signal.
        """
        try:
            # Get combined sentiment
            sentiment_score, sentiment_data = self.get_combined_sentiment(asset)
            
            # Map sentiment score to signal strength
            signal_strength = sentiment_score
            
            # Determine signal type
            if signal_strength > 0.5:
                signal_type = "Strong positive sentiment (bullish)"
            elif signal_strength > 0.2:
                signal_type = "Moderate positive sentiment (slightly bullish)"
            elif signal_strength < -0.5:
                signal_type = "Strong negative sentiment (bearish)"
            elif signal_strength < -0.2:
                signal_type = "Moderate negative sentiment (slightly bearish)"
            else:
                signal_type = "Neutral sentiment"
            
            # Log the sources used
            sources_used = [source for source in sentiment_data["sources"] if source != "error"]
            logger.info(f"Sentiment signal for {asset}: {signal_strength:.2f} ({signal_type}) based on {sources_used}")
            
            return signal_strength, signal_type
            
        except Exception as e:
            logger.error(f"Failed to get sentiment signal: {e}")
            return 0, "Error analyzing sentiment"
