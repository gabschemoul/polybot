"""Knowledge base browser page."""

import streamlit as st
import pandas as pd

from polybot.storage.knowledge import InsightStore
from polybot.storage.simulations import SimulationStore

st.set_page_config(page_title="Connaissances - PolyBot", page_icon="📚", layout="wide")

st.title("📚 Base de Connaissances")

st.markdown("""
Ta base de connaissances accumule tous les insights découverts au fil de tes simulations.
Plus tu expérimentes, plus elle s'enrichit !
""")

# Load stores
insight_store = InsightStore()
sim_store = SimulationStore()

# Stats
stats = insight_store.get_stats()
sim_stats = sim_store.get_stats()

st.divider()

# Overview metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Simulations", sim_stats["total_simulations"])

with col2:
    st.metric("Insights Totaux", stats["total_insights"])

with col3:
    st.metric("Insights Validés", stats["validated_insights"], help="Confirmés par 3+ simulations")

with col4:
    st.metric("Expériences en Attente", stats["pending_experiments"])

st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["💡 Insights", "🔬 Expériences", "📊 Simulations"])

with tab1:
    st.markdown("### 💡 Insights Découverts")

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        categories = ["Tous"] + stats.get("categories", [])
        selected_category = st.selectbox("Catégorie", categories)

    with col2:
        validated_only = st.checkbox("Validés uniquement", value=False)

    # Load insights
    category_filter = None if selected_category == "Tous" else selected_category
    insights = insight_store.list_insights(category=category_filter, validated_only=validated_only)

    if not insights:
        st.info("📭 Aucun insight encore. Lance des simulations et utilise 'Extraire des Insights' sur la page Résultats.")
    else:
        for insight in insights:
            status = "✅ Validé" if insight.validated else f"🔄 En cours ({insight.validation_count}/3)"

            with st.expander(f"💡 {insight.title} — {status}"):
                st.markdown(f"**Catégorie:** {insight.category}")
                st.markdown(f"**Découvert le:** {insight.discovered_at.strftime('%Y-%m-%d')}")
                st.markdown(f"**Confiance:** {insight.confidence*100:.0f}%")

                st.divider()
                st.markdown(insight.description)

                if insight.metrics:
                    st.markdown("**Métriques:**")
                    for key, value in insight.metrics.items():
                        st.markdown(f"- {key}: {value}")

                if insight.tags:
                    st.markdown(f"**Tags:** {', '.join(insight.tags)}")

                if insight.suggested_experiments:
                    st.markdown("**Expériences suggérées:**")
                    for exp in insight.suggested_experiments:
                        st.markdown(f"- {exp}")

                st.markdown(f"**Basé sur:** {len(insight.evidence_simulation_ids)} simulation(s)")

with tab2:
    st.markdown("### 🔬 Expériences à Tester")

    experiments = insight_store.list_experiments()

    if not experiments:
        st.info("📭 Aucune expérience suggérée. Les insights génèrent des expériences automatiquement.")
    else:
        # Group by status
        pending = [e for e in experiments if e.status == "pending"]
        completed = [e for e in experiments if e.status == "completed"]

        if pending:
            st.markdown("#### En Attente")
            for exp in pending:
                with st.expander(f"🔬 {exp.title}"):
                    st.markdown(f"**Hypothèse:** {exp.hypothesis}")

                    if exp.parameters:
                        st.markdown("**Paramètres suggérés:**")
                        st.json(exp.parameters)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"▶️ Tester", key=f"test_{exp.id}"):
                            st.info("Fonctionnalité à venir: lancement automatique de simulation avec ces paramètres")

        if completed:
            st.markdown("#### Complétées")
            for exp in completed:
                outcome_emoji = {"confirmed": "✅", "rejected": "❌", "inconclusive": "🤷"}.get(exp.outcome, "❓")

                with st.expander(f"{outcome_emoji} {exp.title}"):
                    st.markdown(f"**Hypothèse:** {exp.hypothesis}")
                    st.markdown(f"**Résultat:** {exp.outcome}")
                    if exp.result_simulation_id:
                        st.markdown(f"**Simulation:** {exp.result_simulation_id}")

with tab3:
    st.markdown("### 📊 Historique des Simulations")

    simulations = sim_store.list_all()

    if not simulations:
        st.info("📭 Aucune simulation. Lance ta première simulation !")
        st.page_link("pages/2_Simulate.py", label="Aller à Simulation", icon="🚀")
    else:
        # Convert to dataframe
        sim_data = []
        for s in simulations:
            sim_data.append({
                "ID": s["id"],
                "Date": s["created_at"][:10],
                "Stratégie": s["strategy_name"],
                "Approche": s["approach"],
                "Trades": s["total_trades"],
                "Win Rate": f"{s['win_rate']*100:.1f}%",
                "P&L": f"${s['pnl']:+.2f}",
                "P&L %": f"{s['pnl_pct']:+.1f}%",
            })

        df = pd.DataFrame(sim_data)

        # Color the P&L column
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "P&L": st.column_config.TextColumn("P&L"),
                "P&L %": st.column_config.TextColumn("P&L %"),
            }
        )

        # Summary stats
        st.divider()
        st.markdown("#### Statistiques Globales")

        total_pnl = sum(s["pnl"] for s in simulations)
        avg_win_rate = sum(s["win_rate"] for s in simulations) / len(simulations)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("P&L Total (toutes sims)", f"${total_pnl:+,.2f}")

        with col2:
            st.metric("Win Rate Moyen", f"{avg_win_rate*100:.1f}%")

        with col3:
            profitable = len([s for s in simulations if s["pnl"] > 0])
            st.metric("Simulations Rentables", f"{profitable}/{len(simulations)}")

st.divider()

# Tips
st.markdown("### 💡 Conseils pour Apprendre")

st.markdown("""
1. **Teste une seule variable à la fois** — Change un seul paramètre entre deux simulations pour comprendre son impact

2. **Accumule les données** — Plus tu fais de simulations, plus les patterns deviennent visibles

3. **Valide tes insights** — Un insight n'est fiable que s'il se reproduit dans plusieurs simulations

4. **Documente tes hypothèses** — Avant de lancer une simulation, note ce que tu espères apprendre

5. **Sois patient** — Le trading quantitatif demande de la rigueur statistique, pas de la chance
""")
