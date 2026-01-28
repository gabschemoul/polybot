"""Storage layer for simulations and insights.

Automatically uses Supabase if configured, otherwise falls back to local storage.
"""


def get_simulation_store():
    """Get the appropriate simulation store based on configuration."""
    from polybot.config.settings import get_settings
    settings = get_settings()

    if settings.use_supabase:
        from polybot.storage.supabase_store import SupabaseSimulationStore
        return SupabaseSimulationStore()
    else:
        from polybot.storage.simulations import SimulationStore
        return SimulationStore()


def get_insight_store():
    """Get the appropriate insight store based on configuration."""
    from polybot.config.settings import get_settings
    settings = get_settings()

    if settings.use_supabase:
        from polybot.storage.supabase_store import SupabaseInsightStore
        return SupabaseInsightStore()
    else:
        from polybot.storage.knowledge import InsightStore
        return InsightStore()


__all__ = ["get_simulation_store", "get_insight_store"]
