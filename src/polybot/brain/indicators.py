"""Technical indicators calculation."""

import pandas as pd
import pandas_ta as ta

from polybot.brain.models import IndicatorSignal, TradeDirection


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> IndicatorSignal:
    """
    Calculate RSI (Relative Strength Index).

    RSI mesure si un actif est suracheté (>70) ou survendu (<30).
    - RSI < 30: Survendu → potentiel de hausse (mean reversion: UP)
    - RSI > 70: Suracheté → risque de baisse (mean reversion: DOWN)
    - RSI 30-70: Zone neutre

    Pour momentum, l'interprétation est inversée:
    - RSI élevé = force → continue UP
    - RSI bas = faiblesse → continue DOWN
    """
    rsi_series = ta.rsi(df["close"], length=period)
    rsi_value = rsi_series.iloc[-1] if not rsi_series.empty else 50.0

    # Interpretation for mean reversion - more sensitive thresholds
    if rsi_value < 40:
        interpretation = f"Survendu ({rsi_value:.0f} < 40)"
        direction = TradeDirection.UP
        strength = (40 - rsi_value) / 40  # More oversold = stronger signal
    elif rsi_value > 60:
        interpretation = f"Suracheté ({rsi_value:.0f} > 60)"
        direction = TradeDirection.DOWN
        strength = (rsi_value - 60) / 40
    else:
        interpretation = f"Zone neutre ({rsi_value:.0f})"
        direction = None
        strength = 0.0

    return IndicatorSignal(
        name="RSI",
        value=round(rsi_value, 2),
        interpretation=interpretation,
        direction_bias=direction,
        strength=min(1.0, strength),
    )


def calculate_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> IndicatorSignal:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD compare deux moyennes mobiles pour détecter les changements de momentum.
    - MACD > Signal line: Momentum haussier → UP
    - MACD < Signal line: Momentum baissier → DOWN
    - Croisement récent = signal plus fort
    """
    macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)

    if macd_df is None or macd_df.empty:
        return IndicatorSignal(
            name="MACD",
            value=0.0,
            interpretation="Données insuffisantes",
            direction_bias=None,
            strength=0.0,
        )

    macd_col = f"MACD_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    hist_col = f"MACDh_{fast}_{slow}_{signal}"

    macd_value = macd_df[macd_col].iloc[-1]
    signal_value = macd_df[signal_col].iloc[-1]
    histogram = macd_df[hist_col].iloc[-1]

    # Check for recent crossover (last 3 candles)
    recent_hist = macd_df[hist_col].iloc[-3:]
    crossover = (recent_hist.iloc[0] < 0 < recent_hist.iloc[-1]) or (
        recent_hist.iloc[0] > 0 > recent_hist.iloc[-1]
    )

    if histogram > 0:
        interpretation = "Momentum haussier"
        if crossover:
            interpretation += " (croisement récent!)"
        direction = TradeDirection.UP
    else:
        interpretation = "Momentum baissier"
        if crossover:
            interpretation += " (croisement récent!)"
        direction = TradeDirection.DOWN

    # Strength based on histogram magnitude (normalized by price percentage)
    # Use percentage of price to normalize across different price levels
    price = df["close"].iloc[-1]
    histogram_pct = abs(histogram) / price * 100  # As percentage
    strength = min(1.0, histogram_pct * 2)  # 0.5% move = strength 1.0
    if crossover:
        strength = min(1.0, strength + 0.3)

    return IndicatorSignal(
        name="MACD",
        value=round(histogram, 6),
        interpretation=interpretation,
        direction_bias=direction,
        strength=strength,
    )


def calculate_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> IndicatorSignal:
    """
    Calculate Bollinger Bands position.

    Bollinger Bands mesurent la volatilité et les extrêmes de prix.
    - Prix proche de la bande basse: Potentiel rebond → UP
    - Prix proche de la bande haute: Risque de repli → DOWN
    - Prix au milieu: Zone neutre
    """
    bb = ta.bbands(df["close"], length=period, std=std)

    if bb is None or bb.empty:
        return IndicatorSignal(
            name="Bollinger",
            value=0.5,
            interpretation="Données insuffisantes",
            direction_bias=None,
            strength=0.0,
        )

    # Find columns dynamically (pandas-ta uses different formats)
    lower_col = [c for c in bb.columns if c.startswith("BBL")][0]
    mid_col = [c for c in bb.columns if c.startswith("BBM")][0]
    upper_col = [c for c in bb.columns if c.startswith("BBU")][0]

    current_price = df["close"].iloc[-1]
    lower = bb[lower_col].iloc[-1]
    middle = bb[mid_col].iloc[-1]
    upper = bb[upper_col].iloc[-1]

    # Calculate position within bands (0 = lower, 0.5 = middle, 1 = upper)
    band_width = upper - lower
    if band_width > 0:
        position = (current_price - lower) / band_width
    else:
        position = 0.5

    if position < 0.35:
        interpretation = f"Proche bande basse ({position:.0%})"
        direction = TradeDirection.UP
        strength = (0.35 - position) / 0.35
    elif position > 0.65:
        interpretation = f"Proche bande haute ({position:.0%})"
        direction = TradeDirection.DOWN
        strength = (position - 0.65) / 0.35
    else:
        interpretation = f"Zone médiane ({position:.0%})"
        direction = None
        strength = 0.0

    return IndicatorSignal(
        name="Bollinger",
        value=round(position, 3),
        interpretation=interpretation,
        direction_bias=direction,
        strength=min(1.0, strength),
    )


def calculate_ema_cross(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> IndicatorSignal:
    """
    Calculate EMA crossover signal.

    EMA Cross compare deux moyennes mobiles exponentielles.
    - EMA rapide > EMA lente: Tendance haussière → UP
    - EMA rapide < EMA lente: Tendance baissière → DOWN
    """
    ema_fast = ta.ema(df["close"], length=fast)
    ema_slow = ta.ema(df["close"], length=slow)

    if ema_fast is None or ema_slow is None:
        return IndicatorSignal(
            name="EMA Cross",
            value=0.0,
            interpretation="Données insuffisantes",
            direction_bias=None,
            strength=0.0,
        )

    fast_val = ema_fast.iloc[-1]
    slow_val = ema_slow.iloc[-1]
    diff_pct = (fast_val - slow_val) / slow_val * 100

    # Check for recent crossover
    fast_prev = ema_fast.iloc[-3]
    slow_prev = ema_slow.iloc[-3]
    crossover = (fast_prev < slow_prev and fast_val > slow_val) or (
        fast_prev > slow_prev and fast_val < slow_val
    )

    if fast_val > slow_val:
        interpretation = f"Tendance haussière ({diff_pct:+.2f}%)"
        if crossover:
            interpretation += " - Croisement récent!"
        direction = TradeDirection.UP
    else:
        interpretation = f"Tendance baissière ({diff_pct:+.2f}%)"
        if crossover:
            interpretation += " - Croisement récent!"
        direction = TradeDirection.DOWN

    strength = min(1.0, abs(diff_pct) / 2)  # 2% diff = max strength
    if crossover:
        strength = min(1.0, strength + 0.3)

    return IndicatorSignal(
        name="EMA Cross",
        value=round(diff_pct, 3),
        interpretation=interpretation,
        direction_bias=direction,
        strength=strength,
    )


# Registry of available indicators
INDICATOR_FUNCTIONS = {
    "rsi": calculate_rsi,
    "macd": calculate_macd,
    "bollinger": calculate_bollinger,
    "ema_cross": calculate_ema_cross,
}


def calculate_indicators(
    df: pd.DataFrame, indicator_configs: list[dict]
) -> list[IndicatorSignal]:
    """
    Calculate all enabled indicators.

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume
        indicator_configs: List of indicator configurations

    Returns:
        List of indicator signals
    """
    signals = []

    for config in indicator_configs:
        if not config.get("enabled", True):
            continue

        name = config["name"].lower()
        params = config.get("params", {})

        if name in INDICATOR_FUNCTIONS:
            signal = INDICATOR_FUNCTIONS[name](df, **params)
            signals.append(signal)

    return signals
