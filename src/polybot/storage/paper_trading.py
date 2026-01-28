"""Paper trading session storage."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from polybot.config.settings import get_settings
from polybot.brain.models import PaperTradingSession


class PaperTradingStore:
    """Store and retrieve paper trading sessions."""

    def __init__(self, storage_dir: Path | None = None):
        settings = get_settings()
        self.storage_dir = storage_dir or (settings.data_dir / "paper_trading")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = uuid4().hex[:6]
        return f"PAPER-{timestamp}-{short_uuid}"

    def generate_position_id(self) -> str:
        """Generate a unique position ID."""
        return f"POS-{uuid4().hex[:8]}"

    def save(self, session: PaperTradingSession) -> str:
        """Save a paper trading session."""
        path = self._get_path(session.id)
        data = session.model_dump(mode="json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return session.id

    def load(self, session_id: str) -> PaperTradingSession | None:
        """Load a paper trading session by ID."""
        path = self._get_path(session_id)
        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return PaperTradingSession.model_validate(data)

    def get_active_session(self) -> PaperTradingSession | None:
        """Get the most recent active session."""
        for path in sorted(self.storage_dir.glob("PAPER-*.json"), reverse=True):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("status") == "active":
                    return PaperTradingSession.model_validate(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return None

    def list_sessions(self) -> list[dict]:
        """List all sessions with summary info."""
        sessions = []
        for path in sorted(self.storage_dir.glob("PAPER-*.json"), reverse=True):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "status": data["status"],
                    "total_positions": data.get("total_positions", 0),
                    "resolved_positions": data.get("resolved_positions", 0),
                    "winning_positions": data.get("winning_positions", 0),
                    "total_pnl": data.get("total_pnl", 0),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        path = self._get_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
