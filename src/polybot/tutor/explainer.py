"""AI-powered explanation generator for simulation results."""

import json
from datetime import datetime

from anthropic import Anthropic

from polybot.brain.models import Simulation
from polybot.config.settings import get_settings
from polybot.storage.knowledge import Insight, InsightStore
from polybot.tutor.prompts import (
    EXPLAIN_RESULTS_PROMPT,
    GENERATE_INSIGHTS_PROMPT,
    PARAMETER_EXPLANATION,
    TOOLTIPS,
)


class SimulationExplainer:
    """Generate pedagogical explanations for simulation results."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.model = settings.ai_model
        self.max_tokens = settings.ai_max_tokens

        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def _call_api(self, prompt: str) -> str:
        """Make an API call to Claude."""
        if not self.client:
            return self._fallback_explanation()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _fallback_explanation(self) -> str:
        """Provide a basic explanation when API is unavailable."""
        return """## Explication Non Disponible

L'API Claude n'est pas configurée. Pour activer les explications IA:

1. Crée un compte sur https://console.anthropic.com
2. Génère une clé API
3. Ajoute `ANTHROPIC_API_KEY=sk-ant-...` dans ton fichier `.env`

En attendant, tu peux toujours:
- Analyser les métriques affichées
- Comparer avec tes simulations précédentes
- Tester différents paramètres"""

    def explain_simulation(self, simulation: Simulation) -> str:
        """
        Generate a pedagogical explanation of simulation results.

        Args:
            simulation: The completed simulation

        Returns:
            Markdown-formatted explanation
        """
        # Prepare indicators summary
        indicators_list = [
            f"- {ind.name}: {ind.params}" for ind in simulation.strategy.indicators if ind.enabled
        ]
        indicators_summary = "\n".join(indicators_list) if indicators_list else "Aucun indicateur configuré"

        # Sort trades by P&L
        sorted_trades = sorted(simulation.trades, key=lambda t: t.pnl, reverse=True)

        # Format best/worst trades
        def format_trade(t):
            return f"- {t.direction.value.upper()} @ {t.entry_price:.4f} → {t.pnl:+.2f}$ (EV attendue: {t.expected_value:.1%})"

        best_trades = "\n".join(format_trade(t) for t in sorted_trades[:3]) or "Aucun trade"
        worst_trades = "\n".join(format_trade(t) for t in sorted_trades[-3:]) or "Aucun trade"

        # Calculate period
        if simulation.start_time and simulation.end_time:
            delta = simulation.end_time - simulation.start_time
            period = f"{delta.days} jours" if delta.days > 0 else f"{delta.seconds // 3600} heures"
        else:
            period = "Non spécifié"

        # Format prompt
        prompt = EXPLAIN_RESULTS_PROMPT.format(
            strategy_name=simulation.strategy.name,
            approach=simulation.strategy.approach.value,
            period=period,
            initial_capital=simulation.initial_capital,
            final_capital=simulation.final_capital,
            pnl_pct=(simulation.final_capital - simulation.initial_capital) / simulation.initial_capital * 100,
            total_trades=simulation.metrics.total_trades,
            winning_trades=simulation.metrics.winning_trades,
            losing_trades=simulation.metrics.losing_trades,
            win_rate=simulation.metrics.win_rate * 100,
            avg_ev_expected=simulation.metrics.avg_ev_expected * 100,
            avg_ev_realized=simulation.metrics.avg_ev_realized * 100,
            indicators_summary=indicators_summary,
            best_trades=best_trades,
            worst_trades=worst_trades,
        )

        return self._call_api(prompt)

    def generate_insights(
        self, simulation: Simulation, insight_store: InsightStore
    ) -> list[Insight]:
        """
        Extract insights from simulation results.

        Args:
            simulation: The completed simulation
            insight_store: Store to check for existing insights

        Returns:
            List of new insights (already saved to store)
        """
        if not self.client:
            return []

        # Get existing insights to avoid duplicates
        existing = insight_store.list_insights()
        existing_summary = "\n".join(
            f"- {i.title}: {i.description}" for i in existing[:10]
        ) or "Aucun insight existant"

        # Format prompt
        prompt = GENERATE_INSIGHTS_PROMPT.format(
            simulation_json=simulation.model_dump_json(indent=2),
            existing_insights=existing_summary,
        )

        response = self._call_api(prompt)

        # Parse JSON response
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                raw_insights = data.get("insights", [])
            else:
                return []
        except json.JSONDecodeError:
            return []

        # Create and save insights
        new_insights = []
        for raw in raw_insights:
            insight = Insight(
                id=insight_store.generate_insight_id(),
                discovered_at=datetime.now(),
                category=raw.get("category", "strategy"),
                title=raw.get("title", "Insight sans titre"),
                description=raw.get("description", ""),
                evidence_simulation_ids=[simulation.id],
                sample_size=simulation.metrics.total_trades,
                confidence=raw.get("confidence", 0.5),
                tags=raw.get("tags", []),
                suggested_experiments=raw.get("suggested_experiments", []),
            )
            insight_store.add_insight(insight)
            new_insights.append(insight)

        return new_insights

    def explain_parameter(self, param_name: str, current_value: any, param_range: str) -> str:
        """
        Get a pedagogical explanation for a specific parameter.

        Args:
            param_name: Name of the parameter
            current_value: Current value
            param_range: Valid range description

        Returns:
            Explanation text
        """
        # Check tooltips first
        if param_name.lower() in TOOLTIPS:
            tooltip = TOOLTIPS[param_name.lower()]
            return f"**{tooltip['name']}**\n\n{tooltip['simple']}\n\n{tooltip['detail']}"

        # Fall back to API
        if not self.client:
            return f"Paramètre: {param_name}\nValeur: {current_value}\nPlage: {param_range}"

        prompt = PARAMETER_EXPLANATION.format(
            param_name=param_name,
            param_value=current_value,
            param_range=param_range,
        )

        return self._call_api(prompt)

    @staticmethod
    def get_tooltip(param_name: str) -> dict | None:
        """Get pre-defined tooltip for a parameter."""
        return TOOLTIPS.get(param_name.lower())
