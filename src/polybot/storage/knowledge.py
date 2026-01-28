"""Knowledge base for insights and learnings."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from polybot.config.settings import get_settings


class Insight(BaseModel):
    """An insight discovered from simulations."""

    id: str
    discovered_at: datetime
    category: str  # "indicator", "timing", "risk", "strategy"
    title: str
    description: str

    # Evidence
    evidence_simulation_ids: list[str] = Field(default_factory=list)
    sample_size: int = 0
    confidence: float = 0.0

    # Metrics
    metrics: dict = Field(default_factory=dict)

    # Metadata
    tags: list[str] = Field(default_factory=list)
    suggested_experiments: list[str] = Field(default_factory=list)

    # Validation
    validated: bool = False
    validation_count: int = 0


class Experiment(BaseModel):
    """A suggested experiment to run."""

    id: str
    created_at: datetime
    source_insight_id: str | None = None

    title: str
    hypothesis: str
    parameters: dict = Field(default_factory=dict)

    # Status
    status: str = "pending"  # pending, running, completed
    result_simulation_id: str | None = None
    outcome: str | None = None  # "confirmed", "rejected", "inconclusive"


class InsightStore:
    """Store and retrieve insights and experiments."""

    def __init__(self, storage_dir: Path | None = None):
        settings = get_settings()
        self.storage_dir = storage_dir or settings.insights_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.insights_file = self.storage_dir / "insights.json"
        self.experiments_file = self.storage_dir / "experiments.json"

        self._ensure_files()

    def _ensure_files(self):
        """Ensure storage files exist."""
        if not self.insights_file.exists():
            self._write_json(self.insights_file, [])
        if not self.experiments_file.exists():
            self._write_json(self.experiments_file, [])

    def _read_json(self, path: Path) -> list:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # Insights
    def add_insight(self, insight: Insight) -> str:
        """Add a new insight."""
        insights = self._read_json(self.insights_file)
        insights.append(insight.model_dump(mode="json"))
        self._write_json(self.insights_file, insights)
        return insight.id

    def get_insight(self, insight_id: str) -> Insight | None:
        """Get an insight by ID."""
        insights = self._read_json(self.insights_file)
        for data in insights:
            if data["id"] == insight_id:
                return Insight.model_validate(data)
        return None

    def list_insights(self, category: str | None = None, validated_only: bool = False) -> list[Insight]:
        """List all insights, optionally filtered."""
        insights = self._read_json(self.insights_file)
        result = []

        for data in insights:
            if category and data.get("category") != category:
                continue
            if validated_only and not data.get("validated"):
                continue
            result.append(Insight.model_validate(data))

        return sorted(result, key=lambda x: x.discovered_at, reverse=True)

    def update_insight(self, insight_id: str, **updates) -> bool:
        """Update an insight."""
        insights = self._read_json(self.insights_file)

        for i, data in enumerate(insights):
            if data["id"] == insight_id:
                data.update(updates)
                insights[i] = data
                self._write_json(self.insights_file, insights)
                return True

        return False

    def validate_insight(self, insight_id: str, simulation_id: str) -> bool:
        """Mark an insight as validated by a simulation."""
        insights = self._read_json(self.insights_file)

        for i, data in enumerate(insights):
            if data["id"] == insight_id:
                if simulation_id not in data.get("evidence_simulation_ids", []):
                    data.setdefault("evidence_simulation_ids", []).append(simulation_id)
                data["validation_count"] = data.get("validation_count", 0) + 1
                if data["validation_count"] >= 3:
                    data["validated"] = True
                insights[i] = data
                self._write_json(self.insights_file, insights)
                return True

        return False

    # Experiments
    def add_experiment(self, experiment: Experiment) -> str:
        """Add a new experiment."""
        experiments = self._read_json(self.experiments_file)
        experiments.append(experiment.model_dump(mode="json"))
        self._write_json(self.experiments_file, experiments)
        return experiment.id

    def list_experiments(self, status: str | None = None) -> list[Experiment]:
        """List experiments, optionally filtered by status."""
        experiments = self._read_json(self.experiments_file)
        result = []

        for data in experiments:
            if status and data.get("status") != status:
                continue
            result.append(Experiment.model_validate(data))

        return sorted(result, key=lambda x: x.created_at, reverse=True)

    def update_experiment(self, experiment_id: str, **updates) -> bool:
        """Update an experiment."""
        experiments = self._read_json(self.experiments_file)

        for i, data in enumerate(experiments):
            if data["id"] == experiment_id:
                data.update(updates)
                experiments[i] = data
                self._write_json(self.experiments_file, experiments)
                return True

        return False

    # Helpers
    def generate_insight_id(self) -> str:
        """Generate a new insight ID."""
        return f"INS-{uuid4().hex[:8]}"

    def generate_experiment_id(self) -> str:
        """Generate a new experiment ID."""
        return f"EXP-{uuid4().hex[:8]}"

    def create_insight_from_simulation(
        self,
        title: str,
        description: str,
        category: str,
        simulation_id: str,
        metrics: dict | None = None,
        tags: list[str] | None = None,
        suggested_experiments: list[str] | None = None,
    ) -> Insight:
        """Helper to create an insight from simulation results."""
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
