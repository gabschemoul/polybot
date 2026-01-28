"""Core data models for the brain engine."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StrategyApproach(str, Enum):
    """Trading strategy approach."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    HYBRID = "hybrid"
    AUTO = "auto"


class PositionSizing(str, Enum):
    """Position sizing method."""

    KELLY = "kelly"  # Kelly Criterion - size based on edge
    FIXED = "fixed"  # Fixed percentage of capital
    MARTINGALE = "martingale"  # Double after each loss


class TradeDirection(str, Enum):
    """Direction of a trade."""

    UP = "up"
    DOWN = "down"


class TradeResult(str, Enum):
    """Result of a trade."""

    WIN = "win"
    LOSS = "loss"
    PENDING = "pending"


class IndicatorConfig(BaseModel):
    """Configuration for a technical indicator."""

    name: str
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyConfig(BaseModel):
    """Complete strategy configuration."""

    name: str = "Custom Strategy"
    approach: StrategyApproach = StrategyApproach.AUTO

    # Thresholds
    min_ev: float = Field(default=0.08, ge=0.0, le=1.0, description="Minimum expected value (8% = 0.08)")
    min_confidence: float = Field(default=0.65, ge=0.5, le=1.0, description="Minimum confidence level")

    # Indicators
    indicators: list[IndicatorConfig] = Field(default_factory=list)

    # Risk management
    initial_capital: float = Field(default=1000.0, gt=0)
    max_position_pct: float = Field(default=0.02, gt=0, le=0.5, description="Max position as % of capital")

    # Position sizing
    position_sizing: PositionSizing = Field(default=PositionSizing.KELLY, description="Position sizing method")
    martingale_base_pct: float = Field(default=0.01, gt=0, le=0.1, description="Base position for martingale (1% = 0.01)")

    # Fees and slippage
    fee_pct: float = Field(default=0.01, ge=0, le=0.1, description="Fee/slippage deducted from winning trades (1% = 0.01)")


class IndicatorSignal(BaseModel):
    """Signal from a single indicator."""

    name: str
    value: float
    interpretation: str  # e.g., "Survendu", "Neutre", "Suracheté"
    direction_bias: TradeDirection | None = None  # Which direction this indicator suggests
    strength: float = Field(ge=0, le=1)  # 0-1 signal strength


class Signal(BaseModel):
    """Complete trading signal from the brain."""

    timestamp: datetime
    market_id: str
    market_name: str

    # Market data
    btc_price: float
    market_price: float  # Polymarket odds (0-1)

    # Model output
    model_probability: float = Field(ge=0, le=1)
    expected_value: float
    confidence: float = Field(ge=0, le=1)

    # Decision
    direction: TradeDirection
    should_trade: bool
    position_size: float = 0.0  # Suggested position size in $

    # Reasoning
    indicator_signals: list[IndicatorSignal] = Field(default_factory=list)
    reasoning_summary: str = ""


class Trade(BaseModel):
    """Record of a simulated or real trade."""

    id: str
    timestamp: datetime
    simulation_id: str

    # Market info
    market_id: str
    market_name: str
    direction: TradeDirection

    # Prices
    entry_price: float
    exit_price: float | None = None

    # Model data at entry
    model_probability: float
    expected_value: float
    confidence: float

    # Position
    position_size: float
    position_pct: float

    # Result
    result: TradeResult = TradeResult.PENDING
    pnl: float = 0.0
    pnl_pct: float = 0.0

    # Reasoning snapshot
    indicator_signals: list[IndicatorSignal] = Field(default_factory=list)


class SimulationMetrics(BaseModel):
    """Aggregated metrics for a simulation."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0

    avg_ev_expected: float = 0.0
    avg_ev_realized: float = 0.0

    max_drawdown: float = 0.0
    sharpe_ratio: float | None = None

    # Martingale specific
    max_consecutive_losses: int = 0
    max_position_used: float = 0.0  # Largest position taken


class Simulation(BaseModel):
    """Complete simulation record."""

    id: str
    created_at: datetime
    strategy: StrategyConfig

    # Time range
    start_time: datetime
    end_time: datetime

    # Capital
    initial_capital: float
    final_capital: float

    # Results
    trades: list[Trade] = Field(default_factory=list)
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)

    # AI Analysis (filled by tutor)
    ai_explanation: str = ""
    lessons_learned: list[str] = Field(default_factory=list)
    suggested_experiments: list[str] = Field(default_factory=list)
