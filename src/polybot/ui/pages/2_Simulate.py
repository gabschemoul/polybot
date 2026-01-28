"""Simulation execution page - Prediction Accuracy Only."""

import streamlit as st
from datetime import datetime, timezone
import pandas as pd

from polybot.brain.models import (
    Simulation,
    SimulationMetrics,
    StrategyConfig,
    Trade,
    TradeDirection,
    TradeResult,
)
from polybot.brain.indicators import calculate_indicators
from polybot.brain.ev_calculator import generate_signal
from polybot.data.crypto_data import CryptoDataClient
from polybot.storage import get_simulation_store

st.set_page_config(page_title="Backtest - PolyBot", page_icon="🎯", layout="wide")

st.title("🎯 Backtest (Prediction Accuracy)")

st.markdown("""
Ce backtest teste **uniquement ta capacité à prédire la direction** (UP ou DOWN).
Pas de simulation d'argent - juste "ai-je bien deviné?".

Pour simuler des gains réels avec les vrais odds Polymarket, utilise **Paper Trading Live**.
""")

# Check for config
if "strategy_config" not in st.session_state or st.session_state.strategy_config is None:
    st.warning("Aucune stratégie configurée. Configure d'abord ta stratégie.")
    st.page_link("pages/1_Configure.py", label="Aller à Configure", icon="🔧")
    st.stop()

config: StrategyConfig = st.session_state.strategy_config

# Show current config summary
st.markdown("### Configuration Active")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Stratégie", config.name[:25])
with col2:
    st.metric("Approche", config.approach.value)
with col3:
    indicators_str = ", ".join([i.name.upper() for i in config.indicators]) or "Aucun"
    st.metric("Indicateurs", indicators_str[:20])

st.divider()

# Simulation parameters
st.markdown("### Paramètres de Simulation")

col1, col2 = st.columns(2)

with col1:
    days_back = st.slider(
        "Période de backtest (jours)",
        min_value=1,
        max_value=90,
        value=7,
        help="Sur combien de jours historiques tester la stratégie"
    )

with col2:
    interval = st.selectbox(
        "Intervalle des données",
        options=["1m", "5m", "15m"],
        index=0,
        help="Granularité des bougies. 1m = plus précis"
    )

st.divider()

# Run simulation button
if st.button("🎯 Lancer le Backtest", type="primary", use_container_width=True):

    progress_bar = st.progress(0, text="Initialisation...")

    try:
        # Step 1: Fetch BTC data
        progress_bar.progress(10, text="Récupération des données BTC...")

        with CryptoDataClient() as crypto:
            df = crypto.get_historical_klines(
                symbol="BTCUSDT",
                interval=interval,
                days=days_back,
            )

        if df.empty:
            st.error("Impossible de récupérer les données BTC. Vérifie ta connexion.")
            st.stop()

        st.success(f"{len(df)} bougies récupérées")

        # Step 2: Prepare indicator configs
        progress_bar.progress(30, text="Calcul des indicateurs...")

        indicator_configs = [ind.model_dump() for ind in config.indicators]

        # Step 3: Simulate predictions
        progress_bar.progress(40, text="Test des prédictions...")

        sim_store = get_simulation_store()
        sim_id = sim_store.generate_id()

        trades: list[Trade] = []
        trade_count = 0

        # Process data in 15-minute windows
        window_size = 15 if interval == "1m" else (3 if interval == "5m" else 1)

        for i in range(window_size, len(df), window_size):
            # Get data up to this point
            window_df = df.iloc[max(0, i-100):i].copy()

            if len(window_df) < 20:
                continue

            # Calculate indicators
            signals = calculate_indicators(window_df, indicator_configs)

            # Get current BTC price
            btc_price = window_df["close"].iloc[-1]

            # Generate signal (market_price doesn't matter for accuracy test)
            signal = generate_signal(
                market_id=f"btc-15min-{i}",
                market_name=f"BTC > ${btc_price:,.0f} dans 15 min?",
                btc_price=btc_price,
                market_price=0.50,
                indicator_signals=signals,
                config=config,
                timestamp=window_df["timestamp"].iloc[-1],
            )

            # If signal says trade, check if prediction was correct
            if signal.should_trade:
                if i + window_size < len(df):
                    future_price = df.iloc[i + window_size - 1]["close"]

                    # Did the price actually go up or down?
                    price_went_up = future_price > btc_price

                    # Was our prediction correct?
                    if signal.direction == TradeDirection.UP:
                        prediction_correct = price_went_up
                    else:
                        prediction_correct = not price_went_up

                    result = TradeResult.WIN if prediction_correct else TradeResult.LOSS
                    trade_count += 1

                    # Record trade (pnl = 1 if correct, 0 if wrong)
                    trade = Trade(
                        id=f"{sim_id}-T{trade_count:04d}",
                        timestamp=signal.timestamp,
                        simulation_id=sim_id,
                        market_id=signal.market_id,
                        market_name=signal.market_name,
                        direction=signal.direction,
                        entry_price=0.50,
                        exit_price=1.0 if prediction_correct else 0.0,
                        model_probability=signal.model_probability,
                        expected_value=signal.expected_value,
                        confidence=signal.confidence,
                        position_size=1.0,
                        position_pct=0.0,
                        result=result,
                        pnl=1.0 if prediction_correct else 0.0,
                        pnl_pct=0.0,
                        indicator_signals=signal.indicator_signals,
                    )
                    trades.append(trade)

            # Update progress
            progress = 40 + int(50 * (i / len(df)))
            progress_bar.progress(progress, text=f"Test... {len(trades)} prédictions")

        # Step 4: Calculate metrics
        progress_bar.progress(90, text="Calcul des métriques...")

        correct_predictions = len([t for t in trades if t.result == TradeResult.WIN])
        total_predictions = len(trades)
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0

        metrics = SimulationMetrics(
            total_trades=total_predictions,
            winning_trades=correct_predictions,
            losing_trades=total_predictions - correct_predictions,
            win_rate=accuracy,
            avg_win=1.0,
            avg_loss=0.0,
            total_pnl=float(correct_predictions),
            total_pnl_pct=accuracy,
            avg_ev_expected=sum(t.expected_value for t in trades) / len(trades) if trades else 0,
            avg_ev_realized=accuracy - 0.5,
            max_consecutive_losses=0,
            max_position_used=0.0,
        )

        # Step 5: Create and save simulation
        simulation = Simulation(
            id=sim_id,
            created_at=datetime.now(timezone.utc),
            strategy=config,
            saved_strategy_id=st.session_state.get('saved_strategy_id', None),
            start_time=df["timestamp"].iloc[0],
            end_time=df["timestamp"].iloc[-1],
            initial_capital=0.0,
            final_capital=float(correct_predictions),
            trades=trades,
            metrics=metrics,
        )

        sim_store.save(simulation)
        progress_bar.progress(100, text="Terminé!")

        st.session_state.last_simulation_id = sim_id

        # Show results summary
        st.success(f"Backtest terminé! ID: {sim_id}")

        st.divider()
        st.markdown("### 🎯 Résultats - Accuracy")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            accuracy_pct = accuracy * 100
            delta_vs_random = accuracy_pct - 50
            st.metric(
                "Accuracy",
                f"{accuracy_pct:.1f}%",
                f"{delta_vs_random:+.1f}% vs random",
            )

        with col2:
            st.metric("Prédictions Correctes", correct_predictions)

        with col3:
            st.metric("Prédictions Totales", total_predictions)

        with col4:
            st.metric("Prédictions Incorrectes", total_predictions - correct_predictions)

        # Direction breakdown
        if trades:
            st.markdown("### 📊 Accuracy par Direction")

            up_trades = [t for t in trades if t.direction == TradeDirection.UP]
            down_trades = [t for t in trades if t.direction == TradeDirection.DOWN]

            up_correct = len([t for t in up_trades if t.result == TradeResult.WIN])
            down_correct = len([t for t in down_trades if t.result == TradeResult.WIN])

            dcol1, dcol2, dcol3, dcol4 = st.columns(4)

            with dcol1:
                st.metric("Prédictions UP", len(up_trades))
            with dcol2:
                up_acc = up_correct / len(up_trades) * 100 if up_trades else 0
                st.metric("Accuracy UP", f"{up_acc:.1f}%")
            with dcol3:
                st.metric("Prédictions DOWN", len(down_trades))
            with dcol4:
                down_acc = down_correct / len(down_trades) * 100 if down_trades else 0
                st.metric("Accuracy DOWN", f"{down_acc:.1f}%")

            # Interpretation
            st.divider()
            if accuracy > 0.55:
                st.success(f"""
                **Bon signal!** Ton accuracy de {accuracy_pct:.1f}% est supérieure au hasard (50%).

                Tes indicateurs semblent capturer quelque chose.
                Teste maintenant avec **Paper Trading Live** pour voir si ça se traduit en gains réels.
                """)
            elif accuracy > 0.48:
                st.info(f"""
                **Résultat neutre.** Ton accuracy de {accuracy_pct:.1f}% est proche du hasard.

                Les indicateurs ne donnent pas un edge clair sur cette période.
                Essaie d'autres combinaisons ou une période différente.
                """)
            else:
                st.warning(f"""
                **Signal inversé?** Ton accuracy de {accuracy_pct:.1f}% est inférieure au hasard.

                Tes prédictions sont souvent fausses. Peut-être que l'approche inverse fonctionnerait?
                Ou les indicateurs ne sont pas adaptés à cette période.
                """)

        # Recent predictions
        if trades:
            st.markdown("### 📝 Dernières Prédictions")

            trade_data = []
            for t in trades[-15:]:
                trade_data.append({
                    "Date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Prédiction": "📈 UP" if t.direction == TradeDirection.UP else "📉 DOWN",
                    "EV Attendue": f"{t.expected_value*100:.1f}%",
                    "Résultat": "✅ Correct" if t.result == TradeResult.WIN else "❌ Faux",
                })

            st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.page_link("pages/3_Results.py", label="Voir l'Analyse Détaillée", icon="📊")
        with col2:
            st.page_link("pages/6_Paper_Trading_Live.py", label="Paper Trading Live", icon="📈")

    except Exception as e:
        st.error(f"Erreur pendant le backtest: {str(e)}")
        raise e
