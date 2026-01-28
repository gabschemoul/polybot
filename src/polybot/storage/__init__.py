"""Storage layer for simulations and insights.

Automatically uses Supabase if configured, otherwise falls back to local storage.
"""

from polybot.config.settings import get_settings


def get_simulation_store():
    """Get the appropriate simulation store based on configuration."""
    settings = get_settings()

    if settings.use_supabase:
        from polybot.storage.supabase_store import SupabaseSimulationStore
        return SupabaseSimulationStore()
    else:
        from polybot.storage.simulations import SimulationStore
        return SimulationStore()


def get_insight_store():
    """Get the appropriate insight store based on configuration."""
    settings = get_settings()

    if settings.use_supabase:
        from polybot.storage.supabase_store import SupabaseInsightStore
        return SupabaseInsightStore()
    else:
        from polybot.storage.knowledge import InsightStore
        return InsightStore()


# For backwards compatibility
from polybot.storage.simulations import SimulationStore
from polybot.storage.knowledge import InsightStore

__all__ = ["SimulationStore", "InsightStore", "get_simulation_store", "get_insight_store"]
