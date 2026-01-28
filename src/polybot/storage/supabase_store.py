"""Supabase cloud storage for simulations and insights."""

from datetime import datetime, timezone
from uuid import uuid4


def get_supabase_client():
    """Get Supabase client if configured."""
    try:
        from supabase import create_client
    except ImportError:
        return None

    from polybot.config.settings import get_settings
    settings = get_settings()

    if not settings.use_supabase:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


class SupabaseSimulationStore:
    """Store and retrieve simulations from Supabase."""

    def __init__(self):
        self.client = get_supabase_client()
        self.table = "simulations"

    def generate_id(self) -> str:
        """Generate a new simulation ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = uuid4().hex[:6]
        return f"SIM-{timestamp}-{short_uuid}"

    def save(self, simulation) -> str:
        """Save a simulation to Supabase."""
        if not self.client:
            return simulation.id

        data = {
            "id": simulation.id,
            "created_at": simulation.created_at.isoformat(),
            "data": simulation.model_dump(mode="json"),
        }

        self.client.table(self.table).upsert(data).execute()
        return simulation.id

    def load(self, sim_id: str):
        """Load a simulation by ID."""
        if not self.client:
            return None

        from polybot.brain.models import Simulation

        result = self.client.table(self.table).select("data").eq("id", sim_id).execute()

        if not result.data:
            return None

        return Simulation.model_validate(result.data[0]["data"])

    def list_all(self) -> list[dict]:
        """List all simulations with summary info."""
        if not self.client:
            return []

        result = self.client.table(self.table).select("id, created_at, data").order("created_at", desc=True).execute()

        summaries = []
        for row in result.data:
            data = row["data"]
            try:
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
            except (KeyError, TypeError):
                continue

        return summaries

    def delete(self, sim_id: str) -> bool:
        """Delete a simulation."""
        if not self.client:
            return False

        self.client.table(self.table).delete().eq("id", sim_id).execute()
        return True

    def get_stats(self) -> dict:
        """Get aggregate statistics across all simulations."""
        simulations = self.list_all()

        total_sims = len(simulations)
        total_trades = sum(s.get("total_trades", 0) for s in simulations)
        total_pnl = sum(s.get("pnl", 0) for s in simulations)
        winning_sims = len([s for s in simulations if s.get("pnl", 0) > 0])

        return {
            "total_simulations": total_sims,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "winning_simulations": winning_sims,
            "win_rate": winning_sims / total_sims if total_sims > 0 else 0,
        }


class SupabaseInsightStore:
    """Store and retrieve insights from Supabase."""

    def __init__(self):
        self.client = get_supabase_client()
        self.insights_table = "insights"
        self.experiments_table = "experiments"

    def generate_insight_id(self) -> str:
        return f"INS-{uuid4().hex[:8]}"

    def generate_experiment_id(self) -> str:
        return f"EXP-{uuid4().hex[:8]}"

    # Insights
    def add_insight(self, insight) -> str:
        """Add a new insight."""
        if not self.client:
            return insight.id

        data = {
            "id": insight.id,
            "created_at": insight.discovered_at.isoformat(),
            "data": insight.model_dump(mode="json"),
        }

        self.client.table(self.insights_table).upsert(data).execute()
        return insight.id

    def get_insight(self, insight_id: str):
        """Get an insight by ID."""
        if not self.client:
            return None

        from polybot.storage.knowledge import Insight

        result = self.client.table(self.insights_table).select("data").eq("id", insight_id).execute()

        if not result.data:
            return None

        return Insight.model_validate(result.data[0]["data"])

    def list_insights(self, category: str | None = None, validated_only: bool = False) -> list:
        """List all insights, optionally filtered."""
        if not self.client:
            return []

        from polybot.storage.knowledge import Insight

        result = self.client.table(self.insights_table).select("data").order("created_at", desc=True).execute()

        insights = []
        for row in result.data:
            try:
                insight = Insight.model_validate(row["data"])
                if category and insight.category != category:
                    continue
                if validated_only and not insight.validated:
                    continue
                insights.append(insight)
            except Exception:
                continue

        return insights

    def update_insight(self, insight_id: str, **updates) -> bool:
        """Update an insight."""
        if not self.client:
            return False

        insight = self.get_insight(insight_id)
        if not insight:
            return False

        insight_data = insight.model_dump(mode="json")
        insight_data.update(updates)

        self.client.table(self.insights_table).update({
            "data": insight_data
        }).eq("id", insight_id).execute()

        return True

    def validate_insight(self, insight_id: str, simulation_id: str) -> bool:
        """Mark an insight as validated by a simulation."""
        insight = self.get_insight(insight_id)
        if not insight:
            return False

        if simulation_id not in insight.evidence_simulation_ids:
            insight.evidence_simulation_ids.append(simulation_id)

        insight.validation_count += 1
        if insight.validation_count >= 3:
            insight.validated = True

        return self.update_insight(
            insight_id,
            evidence_simulation_ids=insight.evidence_simulation_ids,
            validation_count=insight.validation_count,
            validated=insight.validated,
        )

    # Experiments
    def add_experiment(self, experiment) -> str:
        """Add a new experiment."""
        if not self.client:
            return experiment.id

        data = {
            "id": experiment.id,
            "created_at": experiment.created_at.isoformat(),
            "data": experiment.model_dump(mode="json"),
        }

        self.client.table(self.experiments_table).upsert(data).execute()
        return experiment.id

    def list_experiments(self, status: str | None = None) -> list:
        """List experiments, optionally filtered by status."""
        if not self.client:
            return []

        from polybot.storage.knowledge import Experiment

        result = self.client.table(self.experiments_table).select("data").order("created_at", desc=True).execute()

        experiments = []
        for row in result.data:
            try:
                exp = Experiment.model_validate(row["data"])
                if status and exp.status != status:
                    continue
                experiments.append(exp)
            except Exception:
                continue

        return experiments

    def update_experiment(self, experiment_id: str, **updates) -> bool:
        """Update an experiment."""
        if not self.client:
            return False

        result = self.client.table(self.experiments_table).select("data").eq("id", experiment_id).execute()
        if not result.data:
            return False

        exp_data = result.data[0]["data"]
        exp_data.update(updates)

        self.client.table(self.experiments_table).update({
            "data": exp_data
        }).eq("id", experiment_id).execute()

        return True

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        insights = self.list_insights()
        experiments = self.list_experiments()

        return {
            "total_insights": len(insights),
            "validated_insights": len([i for i in insights if i.validated]),
            "total_experiments": len(experiments),
            "pending_experiments": len([e for e in experiments if e.status == "pending"]),
            "completed_experiments": len([e for e in experiments if e.status == "completed"]),
            "categories": list(set(i.category for i in insights)),
        }

    def create_insight_from_simulation(
        self,
        title: str,
        description: str,
        category: str,
        simulation_id: str,
        metrics: dict | None = None,
        tags: list[str] | None = None,
        suggested_experiments: list[str] | None = None,
    ):
        """Helper to create an insight from simulation results."""
        from polybot.storage.knowledge import Insight

        insight = Insight(
            id=self.generate_insight_id(),
            discovered_at=datetime.now(timezone.utc),
            category=category,
            title=title,
            description=description,
            evidence_simulation_ids=[simulation_id],
            sample_size=1,
            confidence=0.5,
            metrics=metrics or {},
            tags=tags or [],
            suggested_experiments=suggested_experiments or [],
        )

        self.add_insight(insight)
        return insight
