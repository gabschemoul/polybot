"""Tests for the EV calculator module."""

import pytest

from polybot.brain.ev_calculator import (
    calculate_expected_value,
    calculate_confidence,
    calculate_position_size,
    combine_indicator_signals,
)
from polybot.brain.models import (
    IndicatorSignal,
    StrategyApproach,
    TradeDirection,
)


class TestExpectedValue:
    def test_positive_ev(self):
        # Model thinks 60% chance, market says 45%
        ev = calculate_expected_value(
            model_probability=0.60,
            market_price=0.45,
            direction=TradeDirection.UP,
        )

        # Should be positive (we have an edge)
        assert ev > 0

    def test_negative_ev(self):
        # Model thinks 40% chance, market says 60%
        ev = calculate_expected_value(
            model_probability=0.40,
            market_price=0.60,
            direction=TradeDirection.UP,
        )

        # Should be negative (no edge)
        assert ev < 0

    def test_fair_market(self):
        # Model agrees with market
        ev = calculate_expected_value(
            model_probability=0.50,
            market_price=0.50,
            direction=TradeDirection.UP,
        )

        # Should be zero (no edge)
        assert abs(ev) < 0.01

    def test_down_direction(self):
        # Testing DOWN direction
        ev = calculate_expected_value(
            model_probability=0.40,  # 40% UP = 60% DOWN
            market_price=0.60,       # Market says 60% UP = we buy NO at 0.40
            direction=TradeDirection.DOWN,
        )

        # Should be positive (betting on DOWN when model says DOWN)
        assert ev > 0


class TestCombineSignals:
    def test_unanimous_up(self):
        signals = [
            IndicatorSignal(
                name="RSI",
                value=25,
                interpretation="Oversold",
                direction_bias=TradeDirection.UP,
                strength=0.8,
            ),
            IndicatorSignal(
                name="MACD",
                value=0.01,
                interpretation="Bullish",
                direction_bias=TradeDirection.UP,
                strength=0.6,
            ),
        ]

        prob, direction, _ = combine_indicator_signals(signals, StrategyApproach.MEAN_REVERSION)

        assert direction == TradeDirection.UP
        assert prob > 0.5

    def test_mixed_signals(self):
        signals = [
            IndicatorSignal(
                name="RSI",
                value=50,
                interpretation="Neutral",
                direction_bias=TradeDirection.UP,
                strength=0.3,
            ),
            IndicatorSignal(
                name="MACD",
                value=-0.01,
                interpretation="Bearish",
                direction_bias=TradeDirection.DOWN,
                strength=0.7,
            ),
        ]

        prob, direction, _ = combine_indicator_signals(signals, StrategyApproach.MOMENTUM)

        # Stronger signal should win
        assert direction == TradeDirection.DOWN

    def test_no_signals(self):
        prob, direction, reasoning = combine_indicator_signals([], StrategyApproach.AUTO)

        assert prob == 0.5
        assert "Aucun" in reasoning


class TestConfidence:
    def test_high_agreement(self):
        signals = [
            IndicatorSignal(name="RSI", value=25, interpretation="", direction_bias=TradeDirection.UP, strength=0.9),
            IndicatorSignal(name="MACD", value=0.01, interpretation="", direction_bias=TradeDirection.UP, strength=0.8),
        ]

        confidence = calculate_confidence(signals, 0.65)

        assert confidence > 0.6  # Should be relatively high

    def test_low_agreement(self):
        signals = [
            IndicatorSignal(name="RSI", value=50, interpretation="", direction_bias=TradeDirection.UP, strength=0.3),
            IndicatorSignal(name="MACD", value=-0.01, interpretation="", direction_bias=TradeDirection.DOWN, strength=0.3),
        ]

        confidence = calculate_confidence(signals, 0.5)

        assert confidence < 0.6  # Should be lower


class TestPositionSize:
    def test_positive_ev_sizes_position(self):
        size = calculate_position_size(
            ev=0.10,
            confidence=0.7,
            capital=1000,
            max_position_pct=0.02,
        )

        assert size > 0
        assert size <= 20  # Max 2% of 1000

    def test_negative_ev_no_position(self):
        size = calculate_position_size(
            ev=-0.05,
            confidence=0.7,
            capital=1000,
            max_position_pct=0.02,
        )

        assert size == 0

    def test_respects_max_position(self):
        size = calculate_position_size(
            ev=0.50,  # Very high EV
            confidence=0.9,
            capital=1000,
            max_position_pct=0.02,
        )

        assert size <= 20  # Still respects 2% max
