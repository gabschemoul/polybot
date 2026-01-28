"""Main Streamlit application entry point."""

import streamlit as st

st.set_page_config(
    page_title="PolyBot - Trading Lab",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UX
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e7f3ff;
        border: 1px solid #b8daff;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application."""
    st.title("🎰 PolyBot")
    st.subheader("Laboratoire de Trading Pédagogique")

    st.markdown("""
    Bienvenue dans **PolyBot**, ton assistant pour apprendre le trading quantitatif
    sur les marchés de prédiction Polymarket.

    ### 🎯 Comment ça marche ?

    1. **Configure** ta stratégie avec les paramètres que tu veux tester
    2. **Simule** sur des données historiques (paper trading)
    3. **Apprends** grâce aux explications détaillées de l'IA
    4. **Itère** en testant de nouvelles hypothèses

    ### 📚 Navigation

    Utilise le menu à gauche pour naviguer entre les sections :
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **🔧 Configure**
        - Choisis une stratégie (Momentum, Mean Reversion, Auto)
        - Ajuste les indicateurs techniques (RSI, MACD, Bollinger...)
        - Définis tes seuils de risque

        **🚀 Simule**
        - Lance des backtests sur données historiques
        - Regarde les trades simulés en détail
        - Compare différentes configurations
        """)

    with col2:
        st.markdown("""
        **📊 Résultats**
        - Analyse tes performances
        - Comprends pourquoi ça a marché (ou pas)
        - Reçois des suggestions de l'IA

        **📚 Connaissances**
        - Consulte les insights découverts
        - Explore les expériences suggérées
        - Construis ta base de connaissances
        """)

    st.divider()

    # Quick stats if we have data
    from polybot.storage import get_simulation_store, get_insight_store

    try:
        sim_store = get_simulation_store()
        insight_store = get_insight_store()

        sim_stats = sim_store.get_stats()
        insight_stats = insight_store.get_stats()

        if sim_stats["total_simulations"] > 0:
            st.markdown("### 📈 Ton Parcours")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Simulations", sim_stats["total_simulations"])
            with col2:
                st.metric("Trades Simulés", sim_stats["total_trades"])
            with col3:
                st.metric("Insights Découverts", insight_stats["total_insights"])
            with col4:
                win_pct = sim_stats["win_rate"] * 100
                st.metric("Simulations Rentables", f"{win_pct:.0f}%")
        else:
            st.info("👋 Aucune simulation encore. Commence par configurer ta première stratégie !")

    except Exception:
        st.info("👋 Bienvenue ! Configure ta première stratégie pour commencer.")

    st.divider()
    st.caption("PolyBot v0.1.0 — Un projet éducatif. Ne pas utiliser pour du trading réel sans comprendre les risques.")


if __name__ == "__main__":
    main()
