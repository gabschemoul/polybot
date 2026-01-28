"""Simulation storage and retrieval."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from polybot.brain.models import Simulation, SimulationMetrics, StrategyConfig, Trade
from polybot.config.settings import get_settings


class SimulationStore:
    """Store and retrieve simulation results."""

    def __init__(self, storage_dir: Path | None = None):
        settings = get_settings()
        self.storage_dir = storage_dir or settings.simulations_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, sim_id: str) -> Path:
        return self.storage_dir / f"{sim_id}.json"

    def generate_id(self) -> str:
        """Generate a new simulation ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = uuid4().hex[:6]
        return f"SIM-{timestamp}-{short_uuid}"

    def save(self, simulation: Simulation) -> str:
        """
        Save a simulation to storage.

        Args:
            simulation: The simulation to save

        Returns:
            The simulation ID
        """
        path = self._get_path(simulation.id)
        data = simulation.model_dump(mode="json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return simulation.id

    def load(self, sim_id: str) -> Simulation | None:
        """
        Load a simulation by ID.

        Args:
            sim_id: The simulation ID

        Returns:
            The simulation or None if not found
        """
        path = self._get_path(sim_id)
        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return Simulation.model_validate(data)

    def list_all(self) -> list[dict]:
        """
        List all simulations with summary info.

        Returns:
            List of simulation summaries (id, date, strategy name, P&L)
        """
        summaries = []

        for path in sorted(self.storage_dir.glob("SIM-*.json"), reverse=True):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                summaries.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "strategy_name": data["strategy"]["name"],
                    "approach": data["strategy"]["approach"],
                    "initial_capital": data["initial_capital"],
                    "final_capital": data["final_capital"],
                    "pnl": data["final_capital"] - data["initial_capital"],
                    "pnl_pct": (data["final_capital"] - data["initial_capital"]) / data["initial_capital"] * 100,
                    "total_trades": data["metrics"]["total_trades"],
                    "win_rate": data["metrics"]["win_rate"],
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return summaries

    def delete(self, sim_id: str) -> bool:
        """Delete a simulation."""
        path = self._get_path(sim_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def iter_all(self) -> Iterator[Simulation]:
        """Iterate over all simulations."""
        for path in self.storage_dir.glob("SIM-*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                yield Simulation.model_validate(data)
            except (json.JSONDecodeError, KeyError):
                continue

    def get_stats(self) -> dict:
        """Get aggregate statistics across all simulations."""
        total_sims = 0
        total_trades = 0
        total_pnl = 0.0
        winning_sims = 0

        for sim in self.iter_all():
            total_sims += 1
            total_trades += sim.metrics.total_trades
            pnl = sim.final_capital - sim.initial_capital
            total_pnl += pnl
            if pnl > 0:
                winning_sims += 1

        return {
            "total_simulations": total_sims,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "winning_simulations": winning_sims,
            "win_rate": winning_sims / total_sims if total_sims > 0 else 0,
        }
