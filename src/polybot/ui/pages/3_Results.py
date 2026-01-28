"""Results analysis page - Prediction Accuracy focus."""

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
    st.info("Aucune simulation disponible. Lance un backtest d'abord!")
    st.page_link("pages/2_Simulate.py", label="Aller au Backtest", icon="🎯")
    st.stop()

# Simulation selector
st.markdown("### Sélectionne une Simulation")

default_index = 0
if "last_simulation_id" in st.session_state:
    for i, sim in enumerate(simulations):
        if sim["id"] == st.session_state.last_simulation_id:
            default_index = i
            break

# Format options to show accuracy instead of P&L
sim_options = []
for s in simulations:
    win_rate = s.get('win_rate', s.get('pnl_pct', 0))
    if isinstance(win_rate, (int, float)):
        win_rate_pct = win_rate * 100 if win_rate <= 1 else win_rate
    else:
        win_rate_pct = 50.0
    sim_options.append(f"{s['id']} | {s['strategy_name']} | Accuracy: {win_rate_pct:.1f}%")

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

# Summary metrics - Accuracy focused
st.markdown("### 🎯 Prediction Accuracy")

col1, col2, col3, col4, col5 = st.columns(5)

accuracy = simulation.metrics.win_rate
correct = simulation.metrics.winning_trades
total = simulation.metrics.total_trades
wrong = simulation.metrics.losing_trades

with col1:
    delta_vs_random = (accuracy - 0.5) * 100
    st.metric(
        "Accuracy",
        f"{accuracy*100:.1f}%",
        f"{delta_vs_random:+.1f}% vs random",
        delta_color="normal" if delta_vs_random >= 0 else "inverse",
    )

with col2:
    st.metric("Prédictions Correctes", correct)

with col3:
    st.metric("Prédictions Totales", total)

with col4:
    st.metric("Prédictions Fausses", wrong)

with col5:
    st.metric("EV Moyenne Attendue", f"{simulation.metrics.avg_ev_expected*100:.1f}%")

st.divider()

# Charts
st.markdown("### 📉 Visualisations")

tab1, tab2, tab3 = st.tabs(["Accuracy Cumulative", "Distribution", "Détail Prédictions"])

with tab1:
    # Cumulative accuracy over time
    if simulation.trades:
        correct_count = 0
        total_count = 0
        accuracy_history = []
        timestamps = []

        for trade in simulation.trades:
            total_count += 1
            if trade.result == TradeResult.WIN:
                correct_count += 1
            accuracy_history.append(correct_count / total_count * 100)
            timestamps.append(trade.timestamp)

        fig = go.Figure()

        # Accuracy line
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=accuracy_history,
            mode='lines',
            name='Accuracy Cumulative',
            line=dict(color='blue', width=2),
        ))

        # 50% baseline (random)
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="gray",
            annotation_text="Random (50%)"
        )

        fig.update_layout(
            title="Évolution de l'Accuracy Cumulative",
            xaxis_title="Date",
            yaxis_title="Accuracy (%)",
            hovermode="x unified",
            yaxis=dict(range=[0, 100]),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Interpretation
        final_accuracy = accuracy_history[-1] if accuracy_history else 50
        if final_accuracy > 55:
            st.success(f"Ton accuracy finale de {final_accuracy:.1f}% est supérieure au hasard!")
        elif final_accuracy > 48:
            st.info(f"Ton accuracy finale de {final_accuracy:.1f}% est proche du hasard.")
        else:
            st.warning(f"Ton accuracy finale de {final_accuracy:.1f}% est inférieure au hasard.")
    else:
        st.info("Aucune prédiction à afficher")

with tab2:
    if simulation.trades:
        col1, col2 = st.columns(2)

        with col1:
            # Correct/Wrong distribution
            result_data = {
                "Résultat": ["Correct", "Faux"],
                "Nombre": [correct, wrong],
            }
            fig = px.pie(
                result_data,
                values="Nombre",
                names="Résultat",
                color="Résultat",
                color_discrete_map={"Correct": "green", "Faux": "red"},
                title="Répartition Correct/Faux",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Direction distribution
            up_trades = [t for t in simulation.trades if t.direction == TradeDirection.UP]
            down_trades = [t for t in simulation.trades if t.direction == TradeDirection.DOWN]

            dir_data = {
                "Direction": ["UP", "DOWN"],
                "Nombre": [len(up_trades), len(down_trades)],
            }
            fig = px.pie(
                dir_data,
                values="Nombre",
                names="Direction",
                color="Direction",
                color_discrete_map={"UP": "blue", "DOWN": "orange"},
                title="Répartition des Prédictions",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Accuracy by direction
        st.markdown("#### Accuracy par Direction")

        up_correct = len([t for t in up_trades if t.result == TradeResult.WIN])
        down_correct = len([t for t in down_trades if t.result == TradeResult.WIN])

        up_acc = up_correct / len(up_trades) * 100 if up_trades else 0
        down_acc = down_correct / len(down_trades) * 100 if down_trades else 0

        dir_acc_data = {
            "Direction": ["UP", "DOWN"],
            "Accuracy (%)": [up_acc, down_acc],
            "Correct": [up_correct, down_correct],
            "Total": [len(up_trades), len(down_trades)],
        }

        fig = px.bar(
            dir_acc_data,
            x="Direction",
            y="Accuracy (%)",
            color="Direction",
            color_discrete_map={"UP": "blue", "DOWN": "orange"},
            title="Accuracy par Direction",
            text="Accuracy (%)",
        )
        fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Random")
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    if simulation.trades:
        trade_data = []
        for t in simulation.trades:
            trade_data.append({
                "Date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Prédiction": "UP" if t.direction == TradeDirection.UP else "DOWN",
                "Probabilité Modèle": f"{t.model_probability*100:.1f}%",
                "EV Attendue": f"{t.expected_value*100:+.1f}%",
                "Confiance": f"{t.confidence*100:.0f}%",
                "Résultat": "Correct" if t.result == TradeResult.WIN else "Faux",
            })

        df = pd.DataFrame(trade_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            "Télécharger CSV",
            csv,
            f"predictions_{simulation.id}.csv",
            "text/csv",
        )

st.divider()

# AI Explanation
st.markdown("### 🤖 Analyse IA")

has_valid_explanation = simulation.ai_explanation and "API Claude n'est pas configurée" not in simulation.ai_explanation

if has_valid_explanation:
    st.markdown(simulation.ai_explanation)
    if st.button("Régénérer l'analyse", type="secondary"):
        st.rerun()
else:
    if st.button("Générer l'Analyse IA", type="primary"):
        with st.spinner("L'IA analyse tes résultats..."):
            try:
                explanation = explainer.explain_simulation(simulation)
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

if st.button("Extraire des Insights"):
    with st.spinner("Recherche de patterns..."):
        try:
            new_insights = explainer.generate_insights(simulation, insight_store)
            if new_insights:
                st.success(f"{len(new_insights)} nouveaux insights découverts!")
                for insight in new_insights:
                    with st.expander(f"💡 {insight.title}"):
                        st.markdown(f"**Catégorie:** {insight.category}")
                        st.markdown(insight.description)
                        if insight.suggested_experiments:
                            st.markdown("**Expériences suggérées:**")
                            for exp in insight.suggested_experiments:
                                st.markdown(f"- {exp}")
            else:
                st.info("Pas de nouveaux insights pour cette simulation.")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")
            st.info("Configure ta clé API Anthropic pour activer l'extraction d'insights.")

st.divider()
st.markdown("### 🔬 Prochaines Étapes")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Modifier la stratégie ?**

    Retourne sur Configure pour ajuster les paramètres et relancer un backtest.
    """)
    st.page_link("pages/1_Configure.py", label="Modifier la Stratégie", icon="🔧")

with col2:
    st.markdown("""
    **Tester en conditions réelles ?**

    Lance le Paper Trading Live pour tester avec les vrais odds Polymarket.
    """)
    st.page_link("pages/6_Paper_Trading_Live.py", label="Paper Trading Live", icon="📈")
