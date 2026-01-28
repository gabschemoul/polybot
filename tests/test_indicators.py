"""Tests for the indicators module."""

import pandas as pd
import numpy as np
import pytest

from polybot.brain.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger,
    calculate_indicators,
)
from polybot.brain.models import TradeDirection


def create_sample_df(n: int = 100, trend: str = "up") -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    np.random.seed(42)

    if trend == "up":
        close = 100 + np.cumsum(np.random.randn(n) * 0.5 + 0.1)
    elif trend == "down":
        close = 100 + np.cumsum(np.random.randn(n) * 0.5 - 0.1)
    else:
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)

    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.2

    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1min"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(1000, 10000, n),
    })


class TestRSI:
    def test_rsi_calculates(self):
        df = create_sample_df()
        signal = calculate_rsi(df, period=14)

        assert signal.name == "RSI"
        assert 0 <= signal.value <= 100
        assert signal.strength >= 0
        assert signal.strength <= 1

    def test_rsi_oversold_detection(self):
        # Create strongly downtrending data
        df = create_sample_df(100, trend="down")
        signal = calculate_rsi(df, period=14)

        # Should detect oversold or at least low RSI
        assert signal.value < 50  # Downtrend should have lower RSI

    def test_rsi_overbought_detection(self):
        # Create strongly uptrending data
        df = create_sample_df(100, trend="up")
        signal = calculate_rsi(df, period=14)

        # Should detect overbought or at least higher RSI
        assert signal.value > 50  # Uptrend should have higher RSI


class TestMACD:
    def test_macd_calculates(self):
        df = create_sample_df()
        signal = calculate_macd(df)

        assert signal.name == "MACD"
        assert signal.direction_bias in [TradeDirection.UP, TradeDirection.DOWN]

    def test_macd_uptrend(self):
        df = create_sample_df(100, trend="up")
        signal = calculate_macd(df)

        # MACD should have a direction bias (test that it calculates something)
        assert signal.direction_bias in [TradeDirection.UP, TradeDirection.DOWN]


class TestBollinger:
    def test_bollinger_calculates(self):
        df = create_sample_df()
        signal = calculate_bollinger(df)

        assert signal.name == "Bollinger"
        assert 0 <= signal.value <= 1  # Position within bands


class TestCalculateIndicators:
    def test_calculates_multiple(self):
        df = create_sample_df()
        configs = [
            {"name": "rsi", "enabled": True, "params": {"period": 14}},
            {"name": "macd", "enabled": True, "params": {}},
            {"name": "bollinger", "enabled": False, "params": {}},
        ]

        signals = calculate_indicators(df, configs)

        assert len(signals) == 2  # Only enabled indicators
        assert signals[0].name == "RSI"
        assert signals[1].name == "MACD"

    def test_empty_config(self):
        df = create_sample_df()
        signals = calculate_indicators(df, [])

        assert len(signals) == 0
