"""Results analysis page with AI explanations."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from polybot.brain.models import TradeDirection, TradeResult
from polybot.storage import get_simulation_store, get_insight_store
from polybot.tutor.explainer import SimulationExplainer

st.set_page_config(page_title="Résultats - PolyBot", page_icon="📊", layout="wide")

st.title("📊 Analyse des Résultats")

# Load simulations
sim_store = get_simulation_store()
insight_store = get_insight_store()
explainer = SimulationExplainer()

# Get simulation list
simulations = sim_store.list_all()

if not simulations:
    st.info("📭 Aucune simulation disponible. Lance une simulation d'abord !")
    st.page_link("pages/2_Simulate.py", label="Aller à Simulation", icon="🚀")
    st.stop()

# Simulation selector
st.markdown("### Sélectionne une Simulation")

# Default to last simulation if available
default_index = 0
if "last_simulation_id" in st.session_state:
    for i, sim in enumerate(simulations):
        if sim["id"] == st.session_state.last_simulation_id:
            default_index = i
            break

sim_options = [
    f"{s['id']} | {s['strategy_name']} | {s['pnl']:+.2f}$ ({s['pnl_pct']:+.1f}%)"
    for s in simulations
]

selected_sim_str = st.selectbox(
    "Simulation:",
    sim_options,
    index=default_index,
)

selected_sim_id = simulations[sim_options.index(selected_sim_str)]["id"]
simulation = sim_store.load(selected_sim_id)

if not simulation:
    st.error("Simulation introuvable")
    st.stop()

st.divider()

# Summary metrics
st.markdown("### 📈 Performance")

col1, col2, col3, col4, col5 = st.columns(5)

pnl = simulation.final_capital - simulation.initial_capital
pnl_pct = pnl / simulation.initial_capital * 100

with col1:
    st.metric(
        "P&L Total",
        f"${pnl:+,.2f}",
        f"{pnl_pct:+.1f}%",
        delta_color="normal" if pnl >= 0 else "inverse",
    )

with col2:
    st.metric("Capital Final", f"${simulation.final_capital:,.2f}")

with col3:
    st.metric("Trades", simulation.metrics.total_trades)

with col4:
    st.metric("Win Rate", f"{simulation.metrics.win_rate*100:.1f}%")

with col5:
    st.metric("EV Moyenne", f"{simulation.metrics.avg_ev_expected*100:.1f}%")

st.divider()

# Charts
st.markdown("### 📉 Visualisations")

tab1, tab2, tab3 = st.tabs(["Évolution Capital", "Distribution Trades", "Détail Trades"])

with tab1:
    # Capital evolution over time
    if simulation.trades:
        capital_history = [simulation.initial_capital]
        timestamps = [simulation.start_time]

        current_capital = simulation.initial_capital
        for trade in simulation.trades:
            current_capital += trade.pnl
            capital_history.append(current_capital)
            timestamps.append(trade.timestamp)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=capital_history,
            mode='lines+markers',
            name='Capital',
            line=dict(color='blue' if pnl >= 0 else 'red'),
        ))

        # Add baseline
        fig.add_hline(
            y=simulation.initial_capital,
            line_dash="dash",
            line_color="gray",
            annotation_text="Capital Initial"
        )

        fig.update_layout(
            title="Évolution du Capital",
            xaxis_title="Date",
            yaxis_title="Capital ($)",
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun trade à afficher")

with tab2:
    if simulation.trades:
        col1, col2 = st.columns(2)

        with col1:
            # Win/Loss distribution
            win_loss_data = {
                "Résultat": ["Gagnants", "Perdants"],
                "Nombre": [simulation.metrics.winning_trades, simulation.metrics.losing_trades],
            }
            fig = px.pie(
                win_loss_data,
                values="Nombre",
                names="Résultat",
                color="Résultat",
                color_discrete_map={"Gagnants": "green", "Perdants": "red"},
                title="Répartition Win/Loss",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Direction distribution
            up_trades = len([t for t in simulation.trades if t.direction == TradeDirection.UP])
            down_trades = len([t for t in simulation.trades if t.direction == TradeDirection.DOWN])

            dir_data = {
                "Direction": ["UP 📈", "DOWN 📉"],
                "Nombre": [up_trades, down_trades],
            }
            fig = px.pie(
                dir_data,
                values="Nombre",
                names="Direction",
                color="Direction",
                color_discrete_map={"UP 📈": "blue", "DOWN 📉": "orange"},
                title="Répartition Direction",
            )
            st.plotly_chart(fig, use_container_width=True)

        # P&L distribution
        pnl_values = [t.pnl for t in simulation.trades]
        fig = px.histogram(
            x=pnl_values,
            nbins=20,
            title="Distribution des P&L par Trade",
            labels={"x": "P&L ($)", "y": "Nombre de trades"},
        )
        fig.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    if simulation.trades:
        trade_data = []
        for t in simulation.trades:
            trade_data.append({
                "Date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Direction": "📈 UP" if t.direction == TradeDirection.UP else "📉 DOWN",
                "Prix Entrée": f"{t.entry_price:.4f}",
                "Probabilité": f"{t.model_probability*100:.1f}%",
                "EV": f"{t.expected_value*100:+.1f}%",
                "Confiance": f"{t.confidence*100:.0f}%",
                "Position": f"${t.position_size:.2f}",
                "Résultat": "✅" if t.result == TradeResult.WIN else "❌",
                "P&L": f"${t.pnl:+.2f}",
            })

        df = pd.DataFrame(trade_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Télécharger CSV",
            csv,
            f"trades_{simulation.id}.csv",
            "text/csv",
        )

st.divider()

# AI Explanation
st.markdown("### 🤖 Analyse IA")

# Check if we already have a valid explanation (not a fallback/error message)
has_valid_explanation = simulation.ai_explanation and "API Claude n'est pas configurée" not in simulation.ai_explanation

if has_valid_explanation:
    st.markdown(simulation.ai_explanation)
    if st.button("🔄 Régénérer l'analyse", type="secondary"):
        st.rerun()
else:
    if st.button("🧠 Générer l'Analyse IA", type="primary"):
        with st.spinner("L'IA analyse tes résultats..."):
            try:
                explanation = explainer.explain_simulation(simulation)
                # Only save if it's a real explanation, not a fallback
                if "API Claude n'est pas configurée" not in explanation:
                    simulation.ai_explanation = explanation
                    sim_store.save(simulation)
                st.markdown(explanation)
            except Exception as e:
                st.error(f"Erreur lors de l'analyse: {str(e)}")
                st.info("Configure ta clé API Anthropic dans .env pour activer les explications IA.")

# Insights generation
st.divider()
st.markdown("### 💡 Extraction d'Insights")

if st.button("🔍 Extraire des Insights"):
    with st.spinner("Recherche de patterns..."):
        try:
            new_insights = explainer.generate_insights(simulation, insight_store)
            if new_insights:
                st.success(f"✅ {len(new_insights)} nouveaux insights découverts !")
                for insight in new_insights:
                    with st.expander(f"💡 {insight.title}"):
                        st.markdown(f"**Catégorie:** {insight.category}")
                        st.markdown(insight.description)
                        if insight.suggested_experiments:
                            st.markdown("**Expériences suggérées:**")
                            for exp in insight.suggested_experiments:
                                st.markdown(f"- {exp}")
            else:
                st.info("Pas de nouveaux insights pour cette simulation. Peut-être qu'ils existent déjà ou qu'il faut plus de données.")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")
            st.info("Configure ta clé API Anthropic pour activer l'extraction d'insights.")

st.divider()
st.markdown("### 🔬 Prochaines Étapes")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Modifier la stratégie ?**

    Retourne sur Configure pour ajuster les paramètres et relancer une simulation.
    """)
    st.page_link("pages/1_Configure.py", label="Modifier la Stratégie", icon="🔧")

with col2:
    st.markdown("""
    **Voir les connaissances accumulées ?**

    Consulte tous les insights découverts dans ta base de connaissances.
    """)
    st.page_link("pages/4_Knowledge.py", label="Base de Connaissances", icon="📚")
