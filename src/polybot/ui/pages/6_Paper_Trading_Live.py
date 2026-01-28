"""Paper Trading with Real Polymarket Odds."""

import streamlit as st
from datetime import datetime, timezone
import time
import pandas as pd

from polybot.brain.models import (
    PaperPosition,
    PaperTradingSession,
    StrategyConfig,
    TradeDirection,
)
from polybot.brain.indicators import calculate_indicators
from polybot.brain.ev_calculator import generate_signal
from polybot.data.crypto_data import CryptoDataClient
from polybot.data.polymarket import PolymarketClient
from polybot.storage.paper_trading import PaperTradingStore

st.set_page_config(
    page_title="Paper Trading Live - PolyBot",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Paper Trading Live")
st.markdown("""
Trade avec les **VRAIS odds Polymarket** sans risquer d'argent réel.
Vois exactement combien tu aurais gagné ou perdu.
""")

# Initialize store
paper_store = PaperTradingStore()

# Check for strategy config
if "strategy_config" not in st.session_state or st.session_state.strategy_config is None:
    st.warning("Configure une stratégie d'abord!")
    st.page_link("pages/1_Configure.py", label="Aller à Configure", icon="🔧")
    st.stop()

config: StrategyConfig = st.session_state.strategy_config

st.divider()

# Session management
st.markdown("### Session Control")

col1, col2, col3 = st.columns(3)

# Check for active session
active_session = paper_store.get_active_session()

with col1:
    if active_session:
        st.success(f"Session active: {active_session.id[:20]}...")
        if st.button("Stop Session", type="secondary"):
            active_session.status = "completed"
            paper_store.save(active_session)
            st.rerun()
    else:
        if st.button("Start New Session", type="primary"):
            new_session = PaperTradingSession(
                id=paper_store.generate_session_id(),
                created_at=datetime.now(timezone.utc),
                strategy=config,
                status="active",
            )
            paper_store.save(new_session)
            st.rerun()

with col2:
    if active_session:
        open_count = len([p for p in active_session.positions if p.status == "open"])
        st.metric("Positions Ouvertes", open_count)

with col3:
    if active_session:
        st.metric("P&L Total", f"${active_session.total_pnl:+.2f}")

st.divider()

# Main content when session is active
if active_session:
    # Fetch live data
    st.markdown("### Données Live")

    with st.spinner("Récupération des données..."):
        try:
            with CryptoDataClient() as crypto:
                btc_price = crypto.get_current_price()
                df = crypto.get_historical_klines(
                    symbol="BTCUSDT",
                    interval="1m",
                    days=1,
                )

            # Try to get Polymarket odds
            market_id = None
            market_question = None
            market_price = 0.50
            polymarket_available = False

            try:
                with PolymarketClient() as poly:
                    btc_markets = poly.search_btc_15min_markets()

                    if btc_markets:
                        market = btc_markets[0]
                        market_id = market.get("id", f"pm-{int(time.time())}")
                        market_question = market.get("question", f"BTC > ${btc_price:,.0f}?")

                        prices = market.get("outcomePrices", ["0.50", "0.50"])
                        yes_price = float(prices[0]) if prices else 0.50
                        market_price = yes_price
                        polymarket_available = True
            except Exception:
                pass

            if not polymarket_available:
                market_id = f"sim-{int(time.time())}"
                market_question = f"BTC sera-t-il > ${btc_price:,.0f} dans 15 min?"
                market_price = 0.50
                st.warning("Polymarket API indisponible - utilisation d'odds simulés 50/50")

        except Exception as e:
            st.error(f"Erreur: {e}")
            st.stop()

    # Display live data
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Prix BTC", f"${btc_price:,.2f}")

    with col2:
        st.metric("Odds YES", f"{market_price*100:.1f}%")

    with col3:
        st.metric("Odds NO", f"{(1-market_price)*100:.1f}%")

    with col4:
        source = "Polymarket" if polymarket_available else "Simulé"
        st.metric("Source", source)

    st.info(f"**Marché:** {market_question}")

    st.divider()

    # Generate signal
    st.markdown("### Signal de ta Stratégie")

    if len(df) >= 20:
        indicator_configs = [ind.model_dump() for ind in config.indicators]
        signals = calculate_indicators(df.iloc[-100:], indicator_configs)

        signal = generate_signal(
            market_id=market_id,
            market_name=market_question,
            btc_price=btc_price,
            market_price=market_price,
            indicator_signals=signals,
            config=config,
            timestamp=datetime.now(timezone.utc),
        )

        # Display signal
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            direction_str = "UP" if signal.direction == TradeDirection.UP else "DOWN"
            st.metric("Direction", direction_str)

        with col2:
            st.metric("Probabilité Modèle", f"{signal.model_probability*100:.1f}%")

        with col3:
            ev_delta = signal.expected_value * 100
            st.metric("Expected Value", f"{ev_delta:+.1f}%")

        with col4:
            st.metric("Confiance", f"{signal.confidence*100:.0f}%")

        # Show indicator details
        with st.expander("Détail des Indicateurs"):
            for ind in signal.indicator_signals:
                bias = ind.direction_bias.value.upper() if ind.direction_bias else "NEUTRAL"
                st.write(f"**{ind.name}**: {ind.interpretation} ({bias}, force: {ind.strength:.2f})")

        # Trade execution
        st.divider()
        st.markdown("### Exécuter un Paper Trade")

        if signal.should_trade:
            st.success(f"Signal: **{direction_str}** avec EV de {ev_delta:+.1f}%")

            col1, col2 = st.columns(2)

            with col1:
                stake = st.number_input("Mise ($)", min_value=10.0, max_value=1000.0, value=100.0, step=10.0)

            with col2:
                # Calculate entry price based on direction
                if signal.direction == TradeDirection.UP:
                    entry_odds = market_price
                    st.write(f"**Acheter YES à:** ${entry_odds:.4f}")
                else:
                    entry_odds = 1 - market_price
                    st.write(f"**Acheter NO à:** ${entry_odds:.4f}")

            # Show potential P&L
            potential_win = stake * (1 - entry_odds) / entry_odds
            st.write(f"**Si correct:** +${potential_win:.2f} | **Si faux:** -${stake:.2f}")

            if st.button(f"Exécuter {direction_str}", type="primary"):
                position = PaperPosition(
                    id=paper_store.generate_position_id(),
                    session_id=active_session.id,
                    created_at=datetime.now(timezone.utc),
                    market_id=market_id,
                    market_question=market_question,
                    direction=signal.direction,
                    entry_odds=entry_odds,
                    entry_btc_price=btc_price,
                    stake=stake,
                    model_probability=signal.model_probability,
                    expected_value=signal.expected_value,
                    confidence=signal.confidence,
                    indicator_signals=signal.indicator_signals,
                    status="open",
                )

                active_session.positions.append(position)
                active_session.total_positions += 1
                paper_store.save(active_session)

                st.success(f"Position ouverte: {direction_str} à ${entry_odds:.4f}")
                st.balloons()
                st.rerun()
        else:
            st.warning("Pas de signal de trade - conditions non remplies")
            st.write(f"Raison: {signal.reasoning_summary}")

    else:
        st.warning("Données insuffisantes pour les indicateurs")

    st.divider()

    # Open positions
    st.markdown("### Positions Ouvertes")

    open_positions = [p for p in active_session.positions if p.status == "open"]

    if open_positions:
        for pos in open_positions:
            direction_str = "UP" if pos.direction == TradeDirection.UP else "DOWN"

            with st.expander(f"{direction_str} @ ${pos.entry_odds:.4f} - Mise: ${pos.stake:.2f}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Entrée:** ${pos.entry_odds:.4f}")
                    st.write(f"**BTC à l'entrée:** ${pos.entry_btc_price:,.2f}")
                    st.write(f"**EV à l'entrée:** {pos.expected_value*100:+.1f}%")

                with col2:
                    potential_win = pos.stake * (1 - pos.entry_odds) / pos.entry_odds
                    st.write(f"**Gain potentiel:** +${potential_win:.2f}")
                    st.write(f"**Perte potentielle:** -${pos.stake:.2f}")

                st.markdown("**Résoudre cette position:**")
                rcol1, rcol2 = st.columns(2)

                with rcol1:
                    if st.button(f"Résolu YES", key=f"yes_{pos.id}"):
                        pos.resolution = "YES"
                        pos.resolved_at = datetime.now(timezone.utc)
                        pos.status = "resolved"

                        if pos.direction == TradeDirection.UP:
                            pos.realized_pnl = pos.stake * (1 - pos.entry_odds) / pos.entry_odds
                        else:
                            pos.realized_pnl = -pos.stake

                        pos.realized_pnl_pct = pos.realized_pnl / pos.stake * 100

                        active_session.resolved_positions += 1
                        if pos.realized_pnl > 0:
                            active_session.winning_positions += 1
                        active_session.total_pnl += pos.realized_pnl
                        paper_store.save(active_session)
                        st.rerun()

                with rcol2:
                    if st.button(f"Résolu NO", key=f"no_{pos.id}"):
                        pos.resolution = "NO"
                        pos.resolved_at = datetime.now(timezone.utc)
                        pos.status = "resolved"

                        if pos.direction == TradeDirection.DOWN:
                            pos.realized_pnl = pos.stake * (1 - pos.entry_odds) / pos.entry_odds
                        else:
                            pos.realized_pnl = -pos.stake

                        pos.realized_pnl_pct = pos.realized_pnl / pos.stake * 100

                        active_session.resolved_positions += 1
                        if pos.realized_pnl > 0:
                            active_session.winning_positions += 1
                        active_session.total_pnl += pos.realized_pnl
                        paper_store.save(active_session)
                        st.rerun()
    else:
        st.info("Aucune position ouverte")

    # Position history
    st.divider()
    st.markdown("### Historique des Positions")

    resolved = [p for p in active_session.positions if p.status == "resolved"]

    if resolved:
        history_data = []
        for pos in reversed(resolved):
            direction_str = "UP" if pos.direction == TradeDirection.UP else "DOWN"
            result_str = "Correct" if pos.realized_pnl and pos.realized_pnl > 0 else "Faux"
            history_data.append({
                "Heure": pos.resolved_at.strftime("%H:%M:%S") if pos.resolved_at else "-",
                "Direction": direction_str,
                "Entrée": f"${pos.entry_odds:.4f}",
                "Résolution": pos.resolution,
                "Mise": f"${pos.stake:.2f}",
                "P&L": f"${pos.realized_pnl:+.2f}" if pos.realized_pnl else "-",
                "Résultat": result_str,
            })

        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

        # Session summary
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Positions Résolues", len(resolved))

        with col2:
            wins = len([p for p in resolved if p.realized_pnl and p.realized_pnl > 0])
            wr = wins / len(resolved) * 100 if resolved else 0
            st.metric("Win Rate", f"{wr:.1f}%")

        with col3:
            total_pnl = sum(p.realized_pnl for p in resolved if p.realized_pnl)
            st.metric("P&L Session", f"${total_pnl:+.2f}")

        with col4:
            avg_pnl = total_pnl / len(resolved) if resolved else 0
            st.metric("P&L Moyen", f"${avg_pnl:+.2f}")
    else:
        st.info("Aucune position résolue")

else:
    # No active session
    st.info("Démarre une session pour commencer le paper trading avec les vrais odds Polymarket.")

    # Show past sessions
    sessions = paper_store.list_sessions()
    if sessions:
        st.markdown("### Sessions Passées")

        session_data = []
        for s in sessions[:10]:
            wr = s["winning_positions"] / s["resolved_positions"] * 100 if s["resolved_positions"] > 0 else 0
            session_data.append({
                "Session": s["id"][:25] + "...",
                "Créée": s["created_at"][:19],
                "Status": s["status"],
                "Positions": s["total_positions"],
                "Win Rate": f"{wr:.0f}%",
                "P&L": f"${s['total_pnl']:+.2f}",
            })

        st.dataframe(pd.DataFrame(session_data), use_container_width=True, hide_index=True)
