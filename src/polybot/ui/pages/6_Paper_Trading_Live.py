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
    page_icon="💰",
    layout="wide"
)

st.title("💰 Paper Trading Live")
st.markdown("""
**Trade avec les VRAIS odds Polymarket** - Simule exactement ce que tu gagnerais/perdrais en réel.
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
col1, col2, col3 = st.columns(3)

# Check for active session
active_session = paper_store.get_active_session()

with col1:
    if active_session:
        st.success(f"Session active")
        if st.button("Stop Session", type="secondary"):
            active_session.status = "completed"
            paper_store.save(active_session)
            st.rerun()
    else:
        if st.button("Démarrer une Session", type="primary"):
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
        color = "normal" if active_session.total_pnl >= 0 else "inverse"
        st.metric("P&L Total", f"${active_session.total_pnl:+.2f}", delta_color=color)

st.divider()

# Main content when session is active
if active_session:
    # Fetch live data
    st.markdown("## 📊 Marché Polymarket en Direct")

    with st.spinner("Connexion à Polymarket..."):
        try:
            # Get BTC price
            with CryptoDataClient() as crypto:
                btc_price = crypto.get_current_price()
                df = crypto.get_historical_klines(
                    symbol="BTCUSDT",
                    interval="1m",
                    days=1,
                )

            # Get real Polymarket market
            market = None
            polymarket_available = False

            try:
                with PolymarketClient() as poly:
                    market = poly.get_current_btc_market()
                    if market:
                        polymarket_available = True
            except Exception as e:
                st.error(f"Erreur Polymarket: {e}")

        except Exception as e:
            st.error(f"Erreur données: {e}")
            st.stop()

    # Display market info
    if polymarket_available and market:
        st.success("**Connecté à Polymarket** - Vrais odds en temps réel")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Prix BTC", f"${btc_price:,.2f}")

        with col2:
            up_price = market.get("up_price", 0.50)
            st.metric("Odds UP", f"{up_price*100:.1f}%", help="Prix pour acheter 'Up' sur Polymarket")

        with col3:
            down_price = market.get("down_price", 0.50)
            st.metric("Odds DOWN", f"{down_price*100:.1f}%", help="Prix pour acheter 'Down' sur Polymarket")

        with col4:
            st.metric("Volume", f"${market.get('volume', 0):,.0f}")

        # Market question
        market_id = market.get("id", f"pm-{int(time.time())}")
        market_question = market.get("title", market.get("question", "BTC Up or Down?"))

        st.info(f"**Marché actif:** {market_question}")

        # Show how odds work
        with st.expander("Comment fonctionnent les odds Polymarket?"):
            st.markdown(f"""
            ### Calcul des Gains

            **Si tu achètes UP à {up_price*100:.1f}%:**
            - Mise: $100
            - Si BTC monte → Tu gagnes: **${100 * (1 - up_price) / up_price:.2f}**
            - Si BTC baisse → Tu perds: **-$100**

            **Si tu achètes DOWN à {down_price*100:.1f}%:**
            - Mise: $100
            - Si BTC baisse → Tu gagnes: **${100 * (1 - down_price) / down_price:.2f}**
            - Si BTC monte → Tu perds: **-$100**

            ### Exemple concret
            - Acheter UP à 0.60 (60%) avec $100
            - Si UP gagne: tu reçois $100/0.60 = $166.67, donc +$66.67 de profit
            - Si UP perd: tu perds tes $100
            """)

        market_price = up_price  # Use UP price as reference

    else:
        st.warning("**Polymarket indisponible** - Utilisation d'odds simulés 50/50")
        st.markdown("Les marchés BTC 15-min ne sont peut-être pas actifs en ce moment.")

        market_id = f"sim-{int(time.time())}"
        market_question = f"BTC sera-t-il UP dans 15 min?"
        market_price = 0.50
        up_price = 0.50
        down_price = 0.50

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Prix BTC", f"${btc_price:,.2f}")

        with col2:
            st.metric("Odds UP (simulé)", "50%")

        with col3:
            st.metric("Odds DOWN (simulé)", "50%")

    st.divider()

    # Generate signal
    st.markdown("## 🎯 Signal de ta Stratégie")

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

        direction_str = "UP 📈" if signal.direction == TradeDirection.UP else "DOWN 📉"

        with col1:
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
        st.markdown("## 💵 Exécuter un Paper Trade")

        if signal.should_trade:
            st.success(f"**Signal actif: {direction_str}** avec EV de {ev_delta:+.1f}%")

            col1, col2, col3 = st.columns(3)

            with col1:
                stake = st.number_input(
                    "Mise ($)",
                    min_value=10.0,
                    max_value=1000.0,
                    value=100.0,
                    step=10.0,
                    help="Combien tu veux miser sur ce trade"
                )

            with col2:
                # Entry price based on direction
                if signal.direction == TradeDirection.UP:
                    entry_odds = up_price
                    st.markdown(f"**Acheter UP à:** {entry_odds*100:.1f}%")
                else:
                    entry_odds = down_price
                    st.markdown(f"**Acheter DOWN à:** {entry_odds*100:.1f}%")

            with col3:
                # Calculate potential P&L
                potential_win = stake * (1 - entry_odds) / entry_odds
                st.markdown(f"""
                **Si correct:** +${potential_win:.2f}
                **Si faux:** -${stake:.2f}
                """)

            if st.button(f"🎰 Exécuter {direction_str}", type="primary", use_container_width=True):
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

                st.success(f"Position ouverte: {direction_str} à {entry_odds*100:.1f}%")
                st.balloons()
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Pas de signal de trade - conditions non remplies")
            st.write(f"Raison: {signal.reasoning_summary}")

    else:
        st.warning("Données insuffisantes pour les indicateurs")

    st.divider()

    # Open positions
    st.markdown("## 📂 Positions Ouvertes")

    open_positions = [p for p in active_session.positions if p.status == "open"]

    if open_positions:
        for pos in open_positions:
            direction_str = "UP 📈" if pos.direction == TradeDirection.UP else "DOWN 📉"
            potential_win = pos.stake * (1 - pos.entry_odds) / pos.entry_odds

            with st.container():
                st.markdown(f"""
                ### {direction_str} @ {pos.entry_odds*100:.1f}%
                - **Mise:** ${pos.stake:.2f}
                - **BTC à l'entrée:** ${pos.entry_btc_price:,.2f}
                - **Gain potentiel:** +${potential_win:.2f} | **Perte potentielle:** -${pos.stake:.2f}
                """)

                st.markdown("**Comment le marché s'est-il résolu?**")

                rcol1, rcol2 = st.columns(2)

                with rcol1:
                    if st.button(f"✅ BTC a MONTÉ", key=f"up_{pos.id}", use_container_width=True):
                        pos.resolution = "UP"
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
                    if st.button(f"❌ BTC a BAISSÉ", key=f"down_{pos.id}", use_container_width=True):
                        pos.resolution = "DOWN"
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

                st.divider()
    else:
        st.info("Aucune position ouverte - Exécute un trade ci-dessus!")

    # Position history
    st.markdown("## 📜 Historique des Positions")

    resolved = [p for p in active_session.positions if p.status == "resolved"]

    if resolved:
        history_data = []
        for pos in reversed(resolved):
            direction_str = "UP" if pos.direction == TradeDirection.UP else "DOWN"
            result_emoji = "✅" if pos.realized_pnl and pos.realized_pnl > 0 else "❌"
            history_data.append({
                "Heure": pos.resolved_at.strftime("%H:%M:%S") if pos.resolved_at else "-",
                "Direction": direction_str,
                "Odds Entrée": f"{pos.entry_odds*100:.1f}%",
                "Résolution": pos.resolution,
                "Mise": f"${pos.stake:.2f}",
                "P&L": f"${pos.realized_pnl:+.2f}" if pos.realized_pnl else "-",
                "Résultat": result_emoji,
            })

        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

        # Session summary
        st.markdown("### Résumé de la Session")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Positions Résolues", len(resolved))

        with col2:
            wins = len([p for p in resolved if p.realized_pnl and p.realized_pnl > 0])
            wr = wins / len(resolved) * 100 if resolved else 0
            st.metric("Win Rate", f"{wr:.1f}%")

        with col3:
            total_pnl = sum(p.realized_pnl for p in resolved if p.realized_pnl)
            color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("P&L Session", f"${total_pnl:+.2f}")

        with col4:
            avg_pnl = total_pnl / len(resolved) if resolved else 0
            st.metric("P&L Moyen", f"${avg_pnl:+.2f}")
    else:
        st.info("Aucune position résolue encore")

else:
    # No active session
    st.info("""
    **Démarre une session** pour commencer le paper trading avec les vrais odds Polymarket.

    Tu pourras:
    1. Voir les vrais odds des marchés BTC 15-min
    2. Exécuter des trades papier basés sur ta stratégie
    3. Résoudre les positions quand le marché se termine
    4. Voir exactement combien tu aurais gagné/perdu en réel
    """)

    # Show past sessions
    sessions = paper_store.list_sessions()
    if sessions:
        st.markdown("### Sessions Passées")

        session_data = []
        for s in sessions[:10]:
            wr = s["winning_positions"] / s["resolved_positions"] * 100 if s["resolved_positions"] > 0 else 0
            session_data.append({
                "Session": s["id"][:25] + "...",
                "Date": s["created_at"][:10],
                "Status": s["status"],
                "Trades": s["total_positions"],
                "Win Rate": f"{wr:.0f}%",
                "P&L": f"${s['total_pnl']:+.2f}",
            })

        st.dataframe(pd.DataFrame(session_data), use_container_width=True, hide_index=True)
