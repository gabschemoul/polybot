"""Multi-source crypto data client with fallback support."""

from datetime import datetime, timezone, timedelta
from typing import Literal

import httpx
import pandas as pd


class CryptoDataClient:
    """
    Unified client for fetching BTC price data.

    Tries multiple sources in order:
    1. Binance (fastest, most granular)
    2. Binance.US (if main Binance blocked)
    3. CoinGecko (free, no geo-restrictions)
    """

    INTERVALS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
    }

    def __init__(self):
        self._client = httpx.Client(timeout=30.0)
        self._working_source = None

    def _try_binance(
        self,
        base_url: str,
        interval: str,
        limit: int,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> pd.DataFrame | None:
        """Try to fetch from a Binance endpoint."""
        params = {
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        try:
            response = self._client.get(f"{base_url}/api/v3/klines", params=params)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            df = pd.DataFrame(
                data,
                columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades",
                    "taker_buy_base", "taker_buy_quote", "ignore",
                ],
            )

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            return df[["timestamp", "open", "high", "low", "close", "volume"]]

        except Exception:
            return None

    def _try_coingecko(self, days: int) -> pd.DataFrame | None:
        """Fetch from CoinGecko (limited to daily/hourly data)."""
        try:
            # CoinGecko free API - get market chart data
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            params = {
                "vs_currency": "usd",
                "days": min(days, 90),  # CoinGecko limit
            }

            response = self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            prices = data.get("prices", [])
            if not prices:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(prices, columns=["timestamp", "close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df["close"] = df["close"].astype(float)

            # CoinGecko doesn't provide OHLCV, so we estimate
            df["open"] = df["close"].shift(1).fillna(df["close"])
            df["high"] = df[["open", "close"]].max(axis=1) * 1.001
            df["low"] = df[["open", "close"]].min(axis=1) * 0.999
            df["volume"] = 1000.0  # Placeholder

            return df[["timestamp", "open", "high", "low", "close", "volume"]]

        except Exception:
            return None

    def get_historical_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: Literal["1m", "5m", "15m", "1h"] = "1m",
        days: int = 7,
    ) -> pd.DataFrame:
        """
        Fetch historical data for backtesting.

        Tries multiple sources until one works.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        # Source 1: Try main Binance
        if self._working_source in (None, "binance"):
            df = self._fetch_binance_historical(
                "https://api.binance.com",
                interval,
                start_time,
                end_time,
            )
            if df is not None and not df.empty:
                self._working_source = "binance"
                return df

        # Source 2: Try Binance.US
        if self._working_source in (None, "binance_us"):
            df = self._fetch_binance_historical(
                "https://api.binance.us",
                interval,
                start_time,
                end_time,
            )
            if df is not None and not df.empty:
                self._working_source = "binance_us"
                return df

        # Source 3: Fallback to CoinGecko (less granular but always works)
        df = self._try_coingecko(days)
        if df is not None and not df.empty:
            self._working_source = "coingecko"
            return df

        # If all sources fail, return empty DataFrame
        return pd.DataFrame()

    def _fetch_binance_historical(
        self,
        base_url: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame | None:
        """Fetch historical data from a Binance endpoint."""
        interval_seconds = self.INTERVALS[interval]
        all_data = []
        current_start = start_time

        while current_start < end_time:
            df = self._try_binance(
                base_url,
                interval,
                limit=1000,
                start_time=current_start,
                end_time=end_time,
            )

            if df is None or df.empty:
                if not all_data:
                    return None
                break

            all_data.append(df)
            current_start = df["timestamp"].iloc[-1] + timedelta(seconds=interval_seconds)

            if len(df) < 1000:
                break

        if not all_data:
            return None

        result = pd.concat(all_data, ignore_index=True)
        result = result.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        return result.reset_index(drop=True)

    def get_current_price(self) -> float:
        """Get current BTC price."""
        # Try Binance first
        for base_url in ["https://api.binance.com", "https://api.binance.us"]:
            try:
                response = self._client.get(
                    f"{base_url}/api/v3/ticker/price",
                    params={"symbol": "BTCUSDT"}
                )
                response.raise_for_status()
                return float(response.json()["price"])
            except Exception:
                continue

        # Fallback to CoinGecko
        try:
            response = self._client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"}
            )
            response.raise_for_status()
            return float(response.json()["bitcoin"]["usd"])
        except Exception:
            return 0.0

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
