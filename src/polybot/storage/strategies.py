"""Strategy storage for the leaderboard."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _get_settings():
    from polybot.config.settings import get_settings
    return get_settings()


def _get_models():
    from polybot.brain.models import SavedStrategy, StrategyConfig
    return SavedStrategy, StrategyConfig


class StrategyStore:
    """Store and retrieve saved strategies with performance tracking."""

    def __init__(self, storage_dir: Path | None = None):
        settings = _get_settings()
        self.storage_dir = storage_dir or (settings.data_dir / "strategies")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, strategy_id: str) -> Path:
        return self.storage_dir / f"{strategy_id}.json"

    def generate_id(self) -> str:
        """Generate a new strategy ID."""
        short_uuid = uuid4().hex[:8]
        return f"STRAT-{short_uuid}"

    def save(self, strategy) -> str:
        """Save a strategy."""
        path = self._get_path(strategy.id)
        data = strategy.model_dump(mode="json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return strategy.id

    def load(self, strategy_id: str):
        """Load a strategy by ID."""
        path = self._get_path(strategy_id)
        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        SavedStrategy, _ = _get_models()
        return SavedStrategy.model_validate(data)

    def list_all(self) -> list:
        """List all saved strategies."""
        SavedStrategy, _ = _get_models()
        strategies = []

        for path in self.storage_dir.glob("STRAT-*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                strategies.append(SavedStrategy.model_validate(data))
            except (json.JSONDecodeError, KeyError):
                continue

        return strategies

    def get_leaderboard(self) -> list[dict]:
        """Get strategies ranked by performance."""
        strategies = self.list_all()

        # Sort by average P&L percentage (best first)
        strategies.sort(key=lambda s: s.avg_pnl_pct, reverse=True)

        leaderboard = []
        for rank, s in enumerate(strategies, 1):
            leaderboard.append({
                "rank": rank,
                "id": s.id,
                "name": s.name,
                "author": s.author or "Anonyme",
                "approach": s.config.approach.value,
                "simulations": s.total_simulations,
                "total_pnl": s.total_pnl,
                "avg_pnl_pct": s.avg_pnl_pct,
                "best_pnl_pct": s.best_pnl_pct,
                "total_trades": s.total_trades,
                "win_rate": s.overall_win_rate,
            })

        return leaderboard

    def update_stats_from_simulation(self, strategy_id: str, simulation) -> bool:
        """Update strategy stats after a simulation."""
        strategy = self.load(strategy_id)
        if not strategy:
            return False

        # Update aggregates
        strategy.total_simulations += 1
        strategy.total_trades += simulation.metrics.total_trades

        pnl = simulation.final_capital - simulation.initial_capital
        pnl_pct = pnl / simulation.initial_capital * 100
        strategy.total_pnl += pnl

        # Update average P&L %
        if strategy.total_simulations > 0:
            # Rolling average
            strategy.avg_pnl_pct = (
                (strategy.avg_pnl_pct * (strategy.total_simulations - 1) + pnl_pct)
                / strategy.total_simulations
            )

        # Update best P&L
        if pnl_pct > strategy.best_pnl_pct:
            strategy.best_pnl_pct = pnl_pct

        # Update overall win rate (weighted by trades)
        if strategy.total_trades > 0:
            prev_wins = strategy.overall_win_rate * (strategy.total_trades - simulation.metrics.total_trades)
            new_wins = simulation.metrics.winning_trades
            strategy.overall_win_rate = (prev_wins + new_wins) / strategy.total_trades

        self.save(strategy)
        return True

    def delete(self, strategy_id: str) -> bool:
        """Delete a strategy."""
        path = self._get_path(strategy_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def create_from_config(
        self,
        config,
        name: str,
        author: str = "",
    ):
        """Create a new saved strategy from a config."""
        SavedStrategy, _ = _get_models()
        strategy = SavedStrategy(
            id=self.generate_id(),
            name=name,
            author=author,
            created_at=datetime.now(timezone.utc),
            config=config,
        )
        self.save(strategy)
        return strategy
