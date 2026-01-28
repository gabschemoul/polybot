"""Strategy leaderboard page."""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Classement - PolyBot", page_icon="🏆", layout="wide")


def get_strategy_store():
    """Lazy import to avoid circular imports."""
    from polybot.storage.strategies import StrategyStore
    return StrategyStore()

st.title("🏆 Classement des Stratégies")

st.markdown("""
Compare les performances des stratégies sauvegardées par toi et tes amis.
Le classement est basé sur le **P&L moyen (%)** des simulations.
""")

st.divider()

# Load strategies
store = get_strategy_store()
leaderboard = store.get_leaderboard()

if not leaderboard:
    st.info("📭 Aucune stratégie sauvegardée encore !")
    st.markdown("""
    Pour ajouter une stratégie au classement :
    1. Va sur **Configure**
    2. Configure ta stratégie
    3. Clique sur **"Sauvegarder pour le Classement"**
    4. Lance des simulations pour voir les performances !
    """)
    st.page_link("pages/1_Configure.py", label="Créer une stratégie", icon="🔧")
    st.stop()

# Podium for top 3
st.markdown("### 🥇 Podium")

if len(leaderboard) >= 1:
    cols = st.columns(3)

    # Second place (left)
    if len(leaderboard) >= 2:
        with cols[0]:
            s = leaderboard[1]
            st.markdown("#### 🥈 2ème")
            st.metric(s["name"], f"{s['avg_pnl_pct']:+.1f}%", f"{s['simulations']} sims")
            st.caption(f"par {s['author']}")

    # First place (center)
    with cols[1]:
        s = leaderboard[0]
        st.markdown("#### 🥇 1er")
        st.metric(s["name"], f"{s['avg_pnl_pct']:+.1f}%", f"{s['simulations']} sims")
        st.caption(f"par {s['author']}")

    # Third place (right)
    if len(leaderboard) >= 3:
        with cols[2]:
            s = leaderboard[2]
            st.markdown("#### 🥉 3ème")
            st.metric(s["name"], f"{s['avg_pnl_pct']:+.1f}%", f"{s['simulations']} sims")
            st.caption(f"par {s['author']}")

st.divider()

# Full leaderboard table
st.markdown("### 📊 Classement Complet")

df = pd.DataFrame(leaderboard)
df = df.rename(columns={
    "rank": "Rang",
    "name": "Stratégie",
    "author": "Auteur",
    "approach": "Approche",
    "simulations": "Simulations",
    "avg_pnl_pct": "P&L Moyen (%)",
    "best_pnl_pct": "Meilleur P&L (%)",
    "total_trades": "Trades Total",
    "win_rate": "Win Rate",
})

# Format columns
df["P&L Moyen (%)"] = df["P&L Moyen (%)"].apply(lambda x: f"{x:+.2f}%")
df["Meilleur P&L (%)"] = df["Meilleur P&L (%)"].apply(lambda x: f"{x:+.2f}%")
df["Win Rate"] = df["Win Rate"].apply(lambda x: f"{x*100:.1f}%")

# Select columns to display
display_cols = ["Rang", "Stratégie", "Auteur", "Approche", "Simulations", "P&L Moyen (%)", "Meilleur P&L (%)", "Win Rate"]
st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

st.divider()

# Strategy details
st.markdown("### 🔍 Détails d'une Stratégie")

strategy_names = {s["name"]: s["id"] for s in leaderboard}
selected_name = st.selectbox("Sélectionne une stratégie", list(strategy_names.keys()))

if selected_name:
    strategy = store.load(strategy_names[selected_name])
    if strategy:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Configuration:**")
            st.write(f"- Approche: {strategy.config.approach.value}")
            st.write(f"- EV Minimum: {strategy.config.min_ev * 100:.0f}%")
            st.write(f"- Confiance Minimum: {strategy.config.min_confidence * 100:.0f}%")
            st.write(f"- Position Max: {strategy.config.max_position_pct * 100:.1f}%")

            indicators = [i.name.upper() for i in strategy.config.indicators]
            st.write(f"- Indicateurs: {', '.join(indicators) or 'Aucun'}")

        with col2:
            st.markdown("**Paramètres avancés:**")
            sizing = getattr(strategy.config, 'position_sizing', None)
            st.write(f"- Position Sizing: {sizing.value if sizing else 'Kelly'}")
            fee = getattr(strategy.config, 'fee_pct', 0.01) * 100
            st.write(f"- Frais/Slippage: {fee:.1f}%")
            tp_enabled = getattr(strategy.config, 'take_profit_enabled', False)
            if tp_enabled:
                tp_pct = getattr(strategy.config, 'take_profit_pct', 0.9) * 100
                st.write(f"- Take Profit: {tp_pct:.0f}%")
            else:
                st.write("- Take Profit: Désactivé")

        # Option to load this strategy
        if st.button("📥 Charger cette stratégie dans Configure"):
            st.session_state.strategy_config = strategy.config
            st.session_state.saved_strategy_id = strategy.id
            st.success(f"Stratégie '{strategy.name}' chargée ! Va sur Configure pour la modifier ou Simulate pour la tester.")

st.divider()

# Actions
st.markdown("### ⚡ Actions Rapides")

col1, col2 = st.columns(2)

with col1:
    st.page_link("pages/1_Configure.py", label="Créer une nouvelle stratégie", icon="🔧")

with col2:
    st.page_link("pages/2_Simulate.py", label="Lancer une simulation", icon="🚀")
