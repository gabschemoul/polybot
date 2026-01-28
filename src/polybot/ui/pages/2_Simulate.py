"""Simulation execution page."""

import streamlit as st
from datetime import datetime, timezone, timedelta
import pandas as pd

from polybot.brain.models import (
    PositionSizing,
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
# Real BTC data only - no fake Polymarket simulation needed
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
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Stratégie", config.name[:20])
with col2:
    st.metric("Approche", config.approach.value)
with col3:
    st.metric("EV Min", f"{config.min_ev*100:.0f}%")
with col4:
    sizing_labels = {
        PositionSizing.KELLY: "Kelly",
        PositionSizing.FIXED: "Fixe",
        PositionSizing.MARTINGALE: "Martingale",
    }
    current_sizing = getattr(config, 'position_sizing', PositionSizing.KELLY)
    st.metric("Position", sizing_labels.get(current_sizing, "Kelly"))
with col5:
    st.metric("Capital", f"${config.initial_capital:,.0f}")

# Martingale warning
if getattr(config, 'position_sizing', None) == PositionSizing.MARTINGALE:
    st.warning("⚠️ **Mode Martingale actif** — Cette simulation va démontrer pourquoi la martingale est dangereuse. Observe le comportement du capital !")

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
        help="Sur combien de jours historiques tester la stratégie (max 90 jours)"
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

        with CryptoDataClient() as crypto:
            df = crypto.get_historical_klines(
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

        # DEBUG: Show what's being used
        st.info(f"🔧 DEBUG - Approche: **{config.approach.value}** | Indicateurs: **{[ind['name'] for ind in indicator_configs]}**")

        # Step 3: Simulate market windows (every 15 minutes)
        progress_bar.progress(40, text="Simulation des trades...")

        # Using real BTC data with simple 50/50 binary bets

        # Initialize simulation
        sim_store = get_simulation_store()
        sim_id = sim_store.generate_id()

        # DEBUG: Track signal directions
        debug_signals_up = 0
        debug_signals_down = 0
        debug_signals_neutral = 0
        debug_sample_signals = []
        debug_direction_choices = []  # Track why direction was chosen

        trades: list[Trade] = []
        capital = config.initial_capital
        trade_count = 0

        # Martingale state
        consecutive_losses = 0
        martingale_multiplier = 1
        max_consecutive_losses = 0
        max_position_used = 0.0

        def calculate_position_size(signal_size: float, current_capital: float) -> float:
            """Calculate position size based on strategy method."""
            # Get position sizing method with fallback for old configs
            sizing = getattr(config, 'position_sizing', PositionSizing.KELLY)
            if isinstance(sizing, str):
                try:
                    sizing = PositionSizing(sizing)
                except ValueError:
                    sizing = PositionSizing.KELLY

            if sizing == PositionSizing.KELLY:
                # Kelly: use signal's suggested size, capped by max_position_pct
                return min(signal_size, current_capital * config.max_position_pct)

            elif sizing == PositionSizing.FIXED:
                # Fixed: always use max_position_pct of INITIAL capital (no compounding)
                # More realistic: you don't reinvest gains immediately
                return config.initial_capital * config.max_position_pct

            elif sizing == PositionSizing.MARTINGALE:
                # Martingale: base * 2^consecutive_losses
                base_pct = getattr(config, 'martingale_base_pct', 0.01)
                base_position = current_capital * base_pct
                position = base_position * martingale_multiplier
                # Cap at remaining capital
                return min(position, current_capital * 0.9)  # Never bet more than 90%

            # Fallback: use signal size capped by max position
            return min(signal_size, current_capital * config.max_position_pct)

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

            # DEBUG: Track indicator signals
            for sig in signals:
                if sig.direction_bias == TradeDirection.UP:
                    debug_signals_up += 1
                elif sig.direction_bias == TradeDirection.DOWN:
                    debug_signals_down += 1
                else:
                    debug_signals_neutral += 1

            # Capture first few signals for display
            if len(debug_sample_signals) < 5 and signals:
                debug_sample_signals.append([f"{s.name}:{s.direction_bias.value if s.direction_bias else 'NEUTRAL'}({s.value})" for s in signals])

            # Get current BTC price
            btc_price = window_df["close"].iloc[-1]

            # Simple 50/50 market - like a real binary bet
            # No need to simulate fake Polymarket odds
            market_price = 0.50  # Fair odds: win = double your money, lose = lose it all

            # Generate signal
            signal = generate_signal(
                market_id=f"btc-15min-{i}",
                market_name=f"BTC > ${btc_price:,.0f} dans 15 min?",
                btc_price=btc_price,
                market_price=market_price,
                indicator_signals=signals,
                config=config,
                timestamp=window_df["timestamp"].iloc[-1],
            )

            # DEBUG: Track direction choices
            if signal.should_trade and len(debug_direction_choices) < 10:
                debug_direction_choices.append(f"{signal.direction.value}: {signal.reasoning_summary[:50]}")

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

                    # Calculate position size based on method
                    position = calculate_position_size(signal.position_size, capital)
                    max_position_used = max(max_position_used, position)

                    # Check if take profit is enabled
                    take_profit_enabled = getattr(config, 'take_profit_enabled', False)
                    take_profit_pct = getattr(config, 'take_profit_pct', 0.90)
                    fee_rate = getattr(config, 'fee_pct', 0.01)

                    # Apply slippage: you buy at a worse price than mid-market
                    # Slippage increases with position size (market impact)
                    import random
                    base_slippage = fee_rate  # Same as fee setting
                    size_impact = (position / capital) * 0.02  # Larger positions = more slippage
                    random_slippage = random.uniform(0, 0.01)  # Market noise
                    total_slippage = base_slippage + size_impact + random_slippage

                    # Adjust entry price for slippage (we pay more than mid-market)
                    if signal.direction == TradeDirection.UP:
                        effective_entry = min(0.95, market_price * (1 + total_slippage))
                    else:
                        effective_entry = max(0.05, (1 - market_price) * (1 + total_slippage))

                    if take_profit_enabled:
                        # Simulate take profit: exit at take_profit_pct instead of waiting for resolution
                        if signal.direction == TradeDirection.UP:
                            exit_price = take_profit_pct if won else 0.0
                        else:
                            exit_price = (1 - take_profit_pct) if won else 0.0

                        if won:
                            if signal.direction == TradeDirection.UP:
                                # Bought YES at effective_entry, exit at take_profit
                                gross_pnl = position * (exit_price - effective_entry) / effective_entry
                            else:
                                # Bought NO at effective_entry, exit at (1 - exit_price)
                                gross_pnl = position * ((1 - exit_price) - effective_entry) / effective_entry
                            pnl = max(0, gross_pnl)  # Can't lose more than position on a "win"
                            result = TradeResult.WIN if pnl > 0 else TradeResult.LOSS
                        else:
                            pnl = -position
                            result = TradeResult.LOSS
                    else:
                        # Hold until resolution (0 or 1)
                        if won:
                            if signal.direction == TradeDirection.UP:
                                # Bought YES at effective_entry, resolves to 1.0
                                gross_pnl = position * (1.0 - effective_entry) / effective_entry
                            else:
                                # Bought NO at effective_entry, resolves to 1.0
                                gross_pnl = position * (1.0 - effective_entry) / effective_entry
                            pnl = gross_pnl * (1 - fee_rate)
                            result = TradeResult.WIN
                        else:
                            pnl = -position
                            result = TradeResult.LOSS

                    capital += pnl
                    trade_count += 1

                    # Update martingale state
                    if won:
                        consecutive_losses = 0
                        martingale_multiplier = 1
                    else:
                        consecutive_losses += 1
                        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                        martingale_multiplier = 2 ** consecutive_losses

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
            max_consecutive_losses=max_consecutive_losses,
            max_position_used=max_position_used,
        )

        # Step 5: Create and save simulation
        saved_strategy_id = st.session_state.get('saved_strategy_id', None)

        simulation = Simulation(
            id=sim_id,
            created_at=datetime.now(timezone.utc),
            strategy=config,
            saved_strategy_id=saved_strategy_id,
            start_time=df["timestamp"].iloc[0],
            end_time=df["timestamp"].iloc[-1],
            initial_capital=config.initial_capital,
            final_capital=capital,
            trades=trades,
            metrics=metrics,
        )

        sim_store.save(simulation)

        # Update strategy stats if linked to a saved strategy
        if saved_strategy_id:
            from polybot.storage import get_strategy_store
            strategy_store = get_strategy_store()
            strategy_store.update_stats_from_simulation(saved_strategy_id, simulation)

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

        # DEBUG: Show signal breakdown
        st.markdown("#### 🔧 DEBUG - Signaux bruts des indicateurs")
        st.write(f"Signaux UP: {debug_signals_up} | Signaux DOWN: {debug_signals_down} | Signaux NEUTRES: {debug_signals_neutral}")
        st.write(f"Exemples de signaux: {debug_sample_signals[:3]}")
        st.write(f"Exemples de décisions: {debug_direction_choices[:5]}")

        st.markdown("#### 🔧 DEBUG - Trades exécutés")
        st.write(f"Total trades: {len(trades)}")

        # Direction stats
        up_trades = [t for t in trades if t.direction == TradeDirection.UP]
        down_trades = [t for t in trades if t.direction == TradeDirection.DOWN]
        st.write(f"Trades UP: {len(up_trades)} | Trades DOWN: {len(down_trades)}")

        if trades:
            st.markdown("#### 📊 Répartition des Directions")
            dcol1, dcol2, dcol3, dcol4 = st.columns(4)
            with dcol1:
                st.metric("Trades UP 📈", len(up_trades))
            with dcol2:
                up_wins = len([t for t in up_trades if t.result == TradeResult.WIN])
                up_wr = up_wins / len(up_trades) * 100 if up_trades else 0
                st.metric("Win Rate UP", f"{up_wr:.0f}%")
            with dcol3:
                st.metric("Trades DOWN 📉", len(down_trades))
            with dcol4:
                down_wins = len([t for t in down_trades if t.result == TradeResult.WIN])
                down_wr = down_wins / len(down_trades) * 100 if down_trades else 0
                st.metric("Win Rate DOWN", f"{down_wr:.0f}%")

        # Martingale specific metrics
        if getattr(config, 'position_sizing', None) == PositionSizing.MARTINGALE:
            st.markdown("### ⚠️ Analyse Martingale")
            mcol1, mcol2, mcol3 = st.columns(3)

            with mcol1:
                st.metric("Pertes Consécutives Max", metrics.max_consecutive_losses)
            with mcol2:
                max_pos_pct = (metrics.max_position_used / config.initial_capital) * 100
                st.metric("Position Max Utilisée", f"${metrics.max_position_used:.2f}", f"{max_pos_pct:.1f}%")
            with mcol3:
                # What would happen with one more loss
                next_position = config.initial_capital * config.martingale_base_pct * (2 ** (metrics.max_consecutive_losses + 1))
                st.metric("Prochaine Position si Perte", f"${next_position:.2f}")

            if metrics.max_consecutive_losses >= 4:
                st.error(f"""
                🚨 **Danger démontré !** Tu as eu {metrics.max_consecutive_losses} pertes consécutives.

                Avec une base de {config.martingale_base_pct*100:.1f}%, la position a grimpé jusqu'à
                ${metrics.max_position_used:.2f} ({max_pos_pct:.1f}% du capital).

                **Leçon**: Une série de 6-7 pertes (statistiquement probable sur le long terme)
                peut vider complètement ton capital !
                """)
            elif metrics.total_pnl < 0:
                st.warning("""
                📉 La martingale n'a pas réussi à récupérer les pertes dans cette simulation.
                Imagine ce qui se passe sur une période plus longue...
                """)

        # Quick trade list
        if trades:
            st.markdown("### 📝 Derniers Trades")

            trade_data = []
            for t in trades[-10:]:
                row = {
                    "Date": t.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Direction": "📈 UP" if t.direction == TradeDirection.UP else "📉 DOWN",
                    "EV Attendue": f"{t.expected_value*100:.1f}%",
                    "Résultat": "✅ Win" if t.result == TradeResult.WIN else "❌ Loss",
                    "P&L": f"${t.pnl:+.2f}",
                }
                # Add position size for martingale to show escalation
                if getattr(config, 'position_sizing', None) == PositionSizing.MARTINGALE:
                    row["Position"] = f"${t.position_size:.2f}"
                trade_data.append(row)

            st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)

        st.divider()
        st.page_link("pages/3_Results.py", label="Voir l'Analyse Détaillée", icon="📊")

    except Exception as e:
        st.error(f"Erreur pendant la simulation: {str(e)}")
        raise e
