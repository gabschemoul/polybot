"""Binance API client for BTC price data."""

from datetime import datetime, timezone
from typing import Literal

import httpx
import pandas as pd

from polybot.config.settings import get_settings


class BinanceClient:
    """Client for fetching BTC price data from Binance."""

    INTERVALS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
    }

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or settings.binance_base_url
        self._client = httpx.Client(timeout=30.0)

    def get_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: Literal["1m", "5m", "15m", "1h"] = "1m",
        limit: int = 100,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> pd.DataFrame:
        """
        Fetch candlestick (OHLCV) data from Binance.

        Args:
            symbol: Trading pair (default BTCUSDT)
            interval: Candle interval
            limit: Number of candles (max 1000)
            start_time: Start time for historical data
            end_time: End time for historical data

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        response = self._client.get(f"{self.base_url}/api/v3/klines", params=params)
        response.raise_for_status()

        data = response.json()

        # Parse Binance kline format
        df = pd.DataFrame(
            data,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )

        # Convert types
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        # Keep only needed columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]

        return df

    def get_current_price(self, symbol: str = "BTCUSDT") -> float:
        """Get current BTC price."""
        response = self._client.get(
            f"{self.base_url}/api/v3/ticker/price", params={"symbol": symbol}
        )
        response.raise_for_status()
        return float(response.json()["price"])

    def get_historical_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: Literal["1m", "5m", "15m", "1h"] = "1m",
        days: int = 7,
    ) -> pd.DataFrame:
        """
        Fetch historical data for backtesting.

        Args:
            symbol: Trading pair
            interval: Candle interval
            days: Number of days of history

        Returns:
            DataFrame with OHLCV data
        """
        end_time = datetime.now(timezone.utc)
        start_time = datetime(
            end_time.year, end_time.month, end_time.day, tzinfo=timezone.utc
        ) - pd.Timedelta(days=days)

        # Calculate how many candles we need
        interval_seconds = self.INTERVALS[interval]
        total_seconds = (end_time - start_time).total_seconds()
        total_candles = int(total_seconds / interval_seconds)

        # Fetch in chunks of 1000
        all_data = []
        current_start = start_time

        while len(all_data) < total_candles:
            df = self.get_klines(
                symbol=symbol,
                interval=interval,
                limit=1000,
                start_time=current_start,
                end_time=end_time,
            )

            if df.empty:
                break

            all_data.append(df)
            current_start = df["timestamp"].iloc[-1] + pd.Timedelta(seconds=interval_seconds)

            if len(df) < 1000:
                break

        if not all_data:
            return pd.DataFrame()

        result = pd.concat(all_data, ignore_index=True)
        result = result.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

        return result.reset_index(drop=True)

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
