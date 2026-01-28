"""Tooltip components for pedagogical UI."""

import streamlit as st

from polybot.tutor.prompts import TOOLTIPS


def render_tooltip(param_name: str) -> None:
    """Render an expandable tooltip for a parameter."""
    tooltip = TOOLTIPS.get(param_name.lower())
    if not tooltip:
        return

    with st.expander(f"ℹ️ {tooltip['name']}", expanded=False):
        st.markdown(f"**En bref:** {tooltip['simple']}")
        st.markdown(tooltip['detail'])


def render_inline_help(param_name: str) -> str:
    """Get inline help text for a parameter."""
    tooltip = TOOLTIPS.get(param_name.lower())
    if tooltip:
        return tooltip['simple']
    return ""


def render_strategy_explanation(approach: str) -> None:
    """Render explanation for a strategy approach."""
    explanations = {
        "momentum": """
        ### 📈 Stratégie Momentum

        **Philosophie:** "Ce qui monte continue de monter"

        Cette approche suit la tendance actuelle. Si le Bitcoin montre des signes
        de force (RSI élevé, MACD positif), on parie que ça va continuer.

        **Quand ça marche bien:**
        - Marchés en tendance claire
        - Mouvements prolongés

        **Risques:**
        - Retournements soudains
        - Arriver tard dans la tendance
        """,
        "mean_reversion": """
        ### 📉 Stratégie Mean Reversion

        **Philosophie:** "Les excès se corrigent toujours"

        Cette approche parie sur le retour à la normale. Si le Bitcoin a trop
        monté (RSI > 70) ou trop baissé (RSI < 30), on parie sur une correction.

        **Quand ça marche bien:**
        - Marchés en range
        - Mouvements exagérés

        **Risques:**
        - Tendances fortes qui continuent
        - "Le marché peut rester irrationnel plus longtemps que toi solvable"
        """,
        "auto": """
        ### 🤖 Mode Auto (IA)

        **Philosophie:** "Laisse les données décider"

        Le système analyse les conditions du marché et choisit automatiquement
        l'approche la plus adaptée (Momentum ou Mean Reversion).

        **Avantages:**
        - Pas besoin de choisir
        - S'adapte aux conditions

        **Inconvénients:**
        - Moins de contrôle
        - Peut être inconsistant
        """,
    }

    explanation = explanations.get(approach.lower(), "")
    if explanation:
        st.markdown(explanation)


def render_indicator_card(indicator_name: str, enabled: bool, params: dict) -> None:
    """Render an indicator configuration card with explanations."""
    tooltip = TOOLTIPS.get(indicator_name.lower(), {})
    name = tooltip.get("name", indicator_name.upper())

    status = "✅ Activé" if enabled else "❌ Désactivé"

    st.markdown(f"""
    **{name}** {status}

    {tooltip.get('simple', '')}
    """)

    if params:
        param_str = ", ".join(f"{k}={v}" for k, v in params.items())
        st.caption(f"Paramètres: {param_str}")
