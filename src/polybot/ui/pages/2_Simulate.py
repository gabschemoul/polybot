"""Simulation execution page."""

import streamlit as st
from datetime import datetime, timezone, timedelta
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
from polybot.data.binance import BinanceClient
from polybot.data.polymarket import MockPolymarketClient
from polybot.storage import get_simulation_store

st.set_page_config(page_title="Simulate - PolyBot", page_icon="🚀", layout="wide")

st.title("🚀 Simulation (Backtest)")

# Check for config
if "strategy_config" not in st.session_state or st.session_state.strategy_config is None:
    st.warning("⚠️ Aucune stratégie configurée. Retourne sur la page Configure d'abord.")
    st.page_link("pages/1_Configure.py", label="Aller à Configure", icon="🔧")
    st.stop()

config: StrategyConfig = st.session_state.strategy_config

# Show current config summary
st.markdown("### Configuration Active")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Stratégie", config.name[:20])
with col2:
    st.metric("Approche", config.approach.value)
with col3:
    st.metric("EV Min", f"{config.min_ev*100:.0f}%")
with col4:
    st.metric("Capital", f"${config.initial_capital:,.0f}")

st.divider()

# Simulation parameters
st.markdown("### Paramètres de Simulation")

col1, col2 = st.columns(2)

with col1:
    days_back = st.slider(
        "Période de backtest (jours)",
        min_value=1,
        max_value=30,
        value=7,
        help="Sur combien de jours historiques tester la stratégie"
    )

with col2:
    interval = st.selectbox(
        "Intervalle des données",
        options=["1m", "5m", "15m"],
        index=0,
        help="Granularité des bougies. 1m = plus précis mais plus lent"
    )

st.divider()

# Run simulation button
if st.button("🚀 Lancer la Simulation", type="primary", use_container_width=True):

    progress_bar = st.progress(0, text="Initialisation...")

    try:
        # Step 1: Fetch BTC data
        progress_bar.progress(10, text="Récupération des données BTC...")

        with BinanceClient() as binance:
            df = binance.get_historical_klines(
                symbol="BTCUSDT",
                interval=interval,
                days=days_back,
            )

        if df.empty:
            st.error("Impossible de récupérer les données BTC. Vérifie ta connexion.")
            st.stop()

        st.success(f"✅ {len(df)} bougies récupérées")

        # Step 2: Prepare indicator configs
        progress_bar.progress(30, text="Calcul des indicateurs...")

        indicator_configs = [ind.model_dump() for ind in config.indicators]

        # Step 3: Simulate market windows (every 15 minutes)
        progress_bar.progress(40, text="Simulation des trades...")

        # Mock Polymarket client for testing
        polymarket = MockPolymarketClient()

        # Initialize simulation
        sim_store = get_simulation_store()
        sim_id = sim_store.generate_id()

        trades: list[Trade] = []
        capital = config.initial_capital
        trade_count = 0

        # Process data in 15-minute windows
        window_size = 15 if interval == "1m" else (3 if interval == "5m" else 1)
        total_windows = len(df) // window_size

        for i in range(window_size, len(df), window_size):
            # Get data up to this point
            window_df = df.iloc[max(0, i-100):i].copy()  # Last 100 candles for indicators

            if len(window_df) < 20:  # Need enough data for indicators
                continue

            # Calculate indicators
            signals = calculate_indicators(window_df, indicator_configs)

            # Get current BTC price
            btc_price = window_df["close"].iloc[-1]

            # Generate mock market (simulating Polymarket)
            mock_market = polymarket.generate_mock_market(btc_price)
            market_price = float(mock_market["outcomePrices"][0])

            # Generate signal
            signal = generate_signal(
                market_id=mock_market["id"],
                market_name=mock_market["question"],
                btc_price=btc_price,
                market_price=market_price,
                indicator_signals=signals,
                config=config,
                timestamp=window_df["timestamp"].iloc[-1],
            )

            # If signal says trade
            if signal.should_trade and capital > 0:
                # Determine outcome (simplified: look at next candle)
                if i + window_size < len(df):
                    future_price = df.iloc[i + window_size - 1]["close"]
                    price_went_up = future_price > btc_price

                    # Did we win?
                    if signal.direction == TradeDirection.UP:
                        won = price_went_up
                    else:
                        won = not price_went_up

                    # Calculate P&L
                    position = min(signal.position_size, capital * config.max_position_pct)

                    if won:
                        pnl = position * (1 - market_price) / market_price
                        result = TradeResult.WIN
                    else:
                        pnl = -position
                        result = TradeResult.LOSS

                    capital += pnl
                    trade_count += 1

                    # Record trade
                    trade = Trade(
                        id=f"{sim_id}-T{trade_count:04d}",
                        timestamp=signal.timestamp,
                        simulation_id=sim_id,
                        market_id=signal.market_id,
                        market_name=signal.market_name,
                        direction=signal.direction,
                        entry_price=market_price,
                        exit_price=1.0 if won else 0.0,
                        model_probability=signal.model_probability,
                        expected_value=signal.expected_value,
                        confidence=signal.confidence,
                        position_size=position,
                        position_pct=position / config.initial_capital,
                        result=result,
                        pnl=pnl,
                        pnl_pct=pnl / position if position > 0 else 0,
                        indicator_signals=signal.indicator_signals,
                    )
                    trades.append(trade)

            # Update progress
            progress = 40 + int(50 * (i / len(df)))
            progress_bar.progress(progress, text=f"Simulation... {len(trades)} trades")

        # Step 4: Calculate metrics
        progress_bar.progress(90, text="Calcul des métriques...")

        winning_trades = [t for t in trades if t.result == TradeResult.WIN]
        losing_trades = [t for t in trades if t.result == TradeResult.LOSS]

        metrics = SimulationMetrics(
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=len(winning_trades) / len(trades) if trades else 0,
            avg_win=sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            avg_loss=sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            total_pnl=capital - config.initial_capital,
            total_pnl_pct=(capital - config.initial_capital) / config.initial_capital,
            avg_ev_expected=sum(t.expected_value for t in trades) / len(trades) if trades else 0,
            avg_ev_realized=(capital - config.initial_capital) / config.initial_capital / len(trades) if trades else 0,
        )

        # Step 5: Create and save simulation
        simulation = Simulation(
            id=sim_id,
            created_at=datetime.now(timezone.utc),
            strategy=config,
            start_time=df["timestamp"].iloc[0],
            end_time=df["timestamp"].iloc[-1],
            initial_capital=config.initial_capital,
            final_capital=capital,
            trades=trades,
            metrics=metrics,
        )

        sim_store.save(simulation)

        progress_bar.progress(100, text="Terminé!")

        # Store in session for results page
        st.session_state.last_simulation_id = sim_id

        # Show results summary
        st.success(f"✅ Simulation terminée ! ID: {sim_id}")

        st.divider()
        st.markdown("### 📊 Résultats Rapides")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            pnl = capital - config.initial_capital
            pnl_color = "green" if pnl >= 0 else "red"
            st.metric(
                "P&L Total",
                f"${pnl:+,.2f}",
                f"{metrics.total_pnl_pct*100:+.1f}%",
            )

        with col2:
            st.metric("Trades", metrics.total_trades)

        with col3:
            st.metric("Win Rate", f"{metrics.win_rate*100:.1f}%")

        with col4:
            st.metric("Capital Final", f"${capital:,.2f}")

        # Quick trade list
        if trades:
            st.markdown("### 📝 Derniers Trades")

            trade_data = []
            for t in trades[-10:]:
                trade_data.append({
                    "Date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Direction": "📈 UP" if t.direction == TradeDirection.UP else "📉 DOWN",
                    "EV Attendue": f"{t.expected_value*100:.1f}%",
                    "Résultat": "✅ Win" if t.result == TradeResult.WIN else "❌ Loss",
                    "P&L": f"${t.pnl:+.2f}",
                })

            st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)

        st.divider()
        st.page_link("pages/3_Results.py", label="Voir l'Analyse Détaillée", icon="📊")

    except Exception as e:
        st.error(f"Erreur pendant la simulation: {str(e)}")
        raise e
