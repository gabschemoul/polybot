"""Pre-configured strategy presets for beginners."""

from polybot.brain.models import IndicatorConfig, StrategyConfig, StrategyApproach

# Preset strategies with pedagogical descriptions
STRATEGY_PRESETS: dict[str, tuple[StrategyConfig, str]] = {
    "conservative_mean_reversion": (
        StrategyConfig(
            name="Conservative Mean Reversion",
            approach=StrategyApproach.MEAN_REVERSION,
            min_ev=0.10,
            min_confidence=0.70,
            indicators=[
                IndicatorConfig(name="rsi", enabled=True, params={"period": 14}),
                IndicatorConfig(name="bollinger", enabled=True, params={"period": 20, "std": 2}),
            ],
            initial_capital=1000.0,
            max_position_pct=0.02,
        ),
        "Stratégie prudente qui parie sur le retour à la moyenne. "
        "Ne trade que quand le RSI indique un excès ET que le prix touche les bandes de Bollinger. "
        "Idéal pour débuter avec peu de signaux mais haute confiance.",
    ),
    "balanced_momentum": (
        StrategyConfig(
            name="Balanced Momentum",
            approach=StrategyApproach.MOMENTUM,
            min_ev=0.08,
            min_confidence=0.65,
            indicators=[
                IndicatorConfig(name="rsi", enabled=True, params={"period": 14}),
                IndicatorConfig(name="macd", enabled=True, params={"fast": 12, "slow": 26, "signal": 9}),
            ],
            initial_capital=1000.0,
            max_position_pct=0.02,
        ),
        "Stratégie équilibrée qui suit la tendance. "
        "Combine RSI et MACD pour confirmer le momentum. "
        "Plus de signaux que la stratégie conservative, bon compromis risque/fréquence.",
    ),
    "aggressive_scalper": (
        StrategyConfig(
            name="Aggressive Scalper",
            approach=StrategyApproach.MOMENTUM,
            min_ev=0.05,
            min_confidence=0.60,
            indicators=[
                IndicatorConfig(name="rsi", enabled=True, params={"period": 7}),
                IndicatorConfig(name="macd", enabled=True, params={"fast": 8, "slow": 17, "signal": 9}),
            ],
            initial_capital=1000.0,
            max_position_pct=0.03,
        ),
        "Stratégie agressive avec des indicateurs rapides. "
        "Beaucoup de signaux, seuils bas. "
        "ATTENTION: Plus de trades = plus de frais et plus de risque. Pour utilisateurs expérimentés.",
    ),
}


def get_preset(name: str) -> tuple[StrategyConfig, str] | None:
    """Get a preset strategy by name."""
    return STRATEGY_PRESETS.get(name)


def list_presets() -> list[dict]:
    """List all available presets with descriptions."""
    return [
        {
            "id": key,
            "name": config.name,
            "description": desc,
            "approach": config.approach.value,
            "min_ev": config.min_ev,
            "min_confidence": config.min_confidence,
        }
        for key, (config, desc) in STRATEGY_PRESETS.items()
    ]
