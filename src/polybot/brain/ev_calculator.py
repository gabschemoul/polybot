"""Expected Value calculation - the core of the trading logic."""

from polybot.brain.models import (
    IndicatorSignal,
    Signal,
    StrategyApproach,
    StrategyConfig,
    TradeDirection,
)


def combine_indicator_signals(
    signals: list[IndicatorSignal],
    approach: StrategyApproach,
    market_price: float = 0.5,
) -> tuple[float, TradeDirection, str]:
    """
    Combine multiple indicator signals into a single probability estimate.

    For MEAN_REVERSION: Indicators suggesting reversal are weighted higher
    For MOMENTUM: Indicators confirming trend continuation are weighted higher

    Returns:
        tuple of (probability 0-1, suggested direction, reasoning summary)
    """
    if not signals:
        # No indicators - choose direction based on market price (bet against the market)
        direction = TradeDirection.DOWN if market_price > 0.5 else TradeDirection.UP
        return 0.5, direction, "Aucun indicateur actif"

    # Filter signals with direction bias
    directional_signals = [s for s in signals if s.direction_bias is not None]

    if not directional_signals:
        # All indicators neutral - choose direction based on market price
        direction = TradeDirection.DOWN if market_price > 0.5 else TradeDirection.UP
        return 0.5, direction, "Indicateurs neutres"

    # Count votes for each direction, weighted by strength
    up_score = sum(
        s.strength for s in directional_signals if s.direction_bias == TradeDirection.UP
    )
    down_score = sum(
        s.strength for s in directional_signals if s.direction_bias == TradeDirection.DOWN
    )

    total_score = up_score + down_score
    if total_score == 0:
        # Scores equal zero - choose direction based on market price
        direction = TradeDirection.DOWN if market_price > 0.5 else TradeDirection.UP
        return 0.5, direction, "Signaux équilibrés"

    # Determine direction and raw probability
    if up_score > down_score:
        direction = TradeDirection.UP
        raw_prob = up_score / total_score
        winning_signals = [s for s in directional_signals if s.direction_bias == TradeDirection.UP]
    else:
        direction = TradeDirection.DOWN
        raw_prob = down_score / total_score
        winning_signals = [s for s in directional_signals if s.direction_bias == TradeDirection.DOWN]

    # Apply approach-specific adjustments
    if approach == StrategyApproach.MEAN_REVERSION:
        # Mean reversion: boost signals from RSI and Bollinger
        boost = sum(0.05 for s in winning_signals if s.name in ["RSI", "Bollinger"])
        raw_prob = min(0.95, raw_prob + boost)
    elif approach == StrategyApproach.MOMENTUM:
        # Momentum: boost signals from MACD and EMA
        boost = sum(0.05 for s in winning_signals if s.name in ["MACD", "EMA Cross"])
        raw_prob = min(0.95, raw_prob + boost)

    # Scale to realistic probability range (0.45 - 0.75 for crypto short-term)
    # No model should claim >75% accuracy on 15-min crypto movements
    scaled_prob = 0.45 + (raw_prob * 0.30)

    # Build reasoning
    signal_descriptions = [f"{s.name}: {s.interpretation}" for s in winning_signals]
    reasoning = f"Direction {direction.value.upper()} basée sur: {', '.join(signal_descriptions)}"

    return scaled_prob, direction, reasoning


def calculate_expected_value(
    model_probability: float,
    market_price: float,
    direction: TradeDirection,
) -> float:
    """
    Calculate Expected Value of a trade.

    EV = (P_win × Gain) - (P_lose × Loss)

    For a binary market priced at `market_price`:
    - If we BUY at market_price and WIN: we gain (1 - market_price)
    - If we BUY at market_price and LOSE: we lose market_price

    Args:
        model_probability: Our estimated probability of the outcome (0-1)
        market_price: Current market price/odds (0-1)
        direction: UP or DOWN

    Returns:
        Expected value as a decimal (0.10 = 10% edge)
    """
    # For UP direction, we're buying YES at market_price
    # For DOWN direction, we're buying NO at (1 - market_price)
    if direction == TradeDirection.UP:
        buy_price = market_price
        p_win = model_probability
    else:
        buy_price = 1 - market_price
        p_win = 1 - model_probability

    # EV calculation
    gain_if_win = 1 - buy_price  # Payout is always $1, minus what we paid
    loss_if_lose = buy_price  # We lose what we paid

    ev = (p_win * gain_if_win) - ((1 - p_win) * loss_if_lose)

    return ev


def calculate_confidence(
    signals: list[IndicatorSignal],
    model_probability: float,
) -> float:
    """
    Calculate confidence in the signal.

    Confidence is higher when:
    - Multiple indicators agree
    - Indicator strengths are high
    - Model probability is far from 50%

    Returns:
        Confidence level 0-1
    """
    if not signals:
        return 0.5

    directional = [s for s in signals if s.direction_bias is not None]
    if not directional:
        return 0.5

    # Factor 1: Agreement ratio (how many indicators point same direction)
    directions = [s.direction_bias for s in directional]
    most_common = max(set(directions), key=directions.count)
    agreement = directions.count(most_common) / len(directions)

    # Factor 2: Average strength of agreeing signals
    agreeing = [s for s in directional if s.direction_bias == most_common]
    avg_strength = sum(s.strength for s in agreeing) / len(agreeing)

    # Factor 3: Distance from 50% (more extreme = more confident)
    prob_confidence = abs(model_probability - 0.5) * 2

    # Weighted combination
    confidence = (agreement * 0.4) + (avg_strength * 0.3) + (prob_confidence * 0.3)

    return min(1.0, confidence)


def calculate_position_size(
    ev: float,
    confidence: float,
    capital: float,
    max_position_pct: float,
) -> float:
    """
    Calculate suggested position size using modified Kelly Criterion.

    Kelly suggests: f = (bp - q) / b
    where b = odds, p = win prob, q = lose prob

    We use a fractional Kelly (25-50%) for safety.

    Args:
        ev: Expected value
        confidence: Confidence level
        capital: Available capital
        max_position_pct: Maximum position as % of capital

    Returns:
        Suggested position size in dollars
    """
    if ev <= 0:
        return 0.0

    # Use fractional Kelly based on confidence
    kelly_fraction = 0.25 + (confidence * 0.25)  # 25-50% Kelly

    # Simplified Kelly: position = EV * fraction * capital
    raw_position = ev * kelly_fraction * capital

    # Apply max position constraint
    max_position = capital * max_position_pct
    position = min(raw_position, max_position)

    return round(position, 2)


def generate_signal(
    market_id: str,
    market_name: str,
    btc_price: float,
    market_price: float,
    indicator_signals: list[IndicatorSignal],
    config: StrategyConfig,
    timestamp=None,
) -> Signal:
    """
    Generate a complete trading signal.

    This is the main entry point that combines all the logic.

    Args:
        market_id: Polymarket market ID
        market_name: Human readable market name
        btc_price: Current BTC price
        market_price: Current Polymarket odds (0-1)
        indicator_signals: List of calculated indicator signals
        config: Strategy configuration
        timestamp: Signal timestamp (defaults to now)

    Returns:
        Complete Signal object with trade decision
    """
    from datetime import datetime, timezone

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Combine indicators into probability estimate
    model_probability, direction, reasoning = combine_indicator_signals(
        indicator_signals, config.approach, market_price
    )

    # Calculate EV
    ev = calculate_expected_value(model_probability, market_price, direction)

    # Calculate confidence
    confidence = calculate_confidence(indicator_signals, model_probability)

    # Determine if we should trade
    should_trade = ev >= config.min_ev and confidence >= config.min_confidence

    # Calculate position size if trading
    position_size = 0.0
    if should_trade:
        position_size = calculate_position_size(
            ev, confidence, config.initial_capital, config.max_position_pct
        )

    return Signal(
        timestamp=timestamp,
        market_id=market_id,
        market_name=market_name,
        btc_price=btc_price,
        market_price=market_price,
        model_probability=round(model_probability, 4),
        expected_value=round(ev, 4),
        confidence=round(confidence, 4),
        direction=direction,
        should_trade=should_trade,
        position_size=position_size,
        indicator_signals=indicator_signals,
        reasoning_summary=reasoning,
    )
