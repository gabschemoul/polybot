"""Strategy configuration page - Simplified for prediction accuracy."""

import streamlit as st

from polybot.brain.models import IndicatorConfig, StrategyApproach, StrategyConfig
from polybot.config.presets import list_presets, get_preset
from polybot.tutor.prompts import TOOLTIPS
from polybot.ui.components.tooltips import render_tooltip, render_strategy_explanation

st.set_page_config(page_title="Configure - PolyBot", page_icon="🔧", layout="wide")

st.title("🔧 Configure ta Stratégie")

st.markdown("""
Configure les indicateurs et l'approche de ta stratégie.
Le **Backtest** testera ta capacité à prédire la direction (UP/DOWN).
Le **Paper Trading Live** simulera les gains réels avec les vrais odds Polymarket.
""")

# Initialize session state
if "strategy_config" not in st.session_state:
    st.session_state.strategy_config = None

saved_config = st.session_state.strategy_config

st.divider()

# Preset selection
st.subheader("📦 Stratégies Pré-configurées")
st.markdown("Choisis une stratégie de base ou personnalise entièrement.")

presets = list_presets()
preset_options = ["Personnalisé"] + [p["name"] for p in presets]

default_preset_index = 0
if saved_config:
    for i, p in enumerate(presets):
        if p["name"] == saved_config.name:
            default_preset_index = i + 1
            break

selected_preset = st.selectbox(
    "Commencer avec:",
    preset_options,
    index=default_preset_index,
    help="Les presets sont des configurations testées pour débuter."
)

if selected_preset != "Personnalisé":
    preset_id = next(p["id"] for p in presets if p["name"] == selected_preset)
    preset_config, preset_desc = get_preset(preset_id)
    st.info(f"💡 {preset_desc}")
else:
    preset_config = saved_config

st.divider()

# Strategy approach
st.subheader("📈 Approche de Trading")

col1, col2 = st.columns([2, 1])

with col1:
    approach_options = {
        "Mean Reversion": StrategyApproach.MEAN_REVERSION,
        "Momentum": StrategyApproach.MOMENTUM,
        "Auto (IA décide)": StrategyApproach.AUTO,
    }

    default_approach = "Mean Reversion"
    base_config = preset_config or saved_config
    if base_config:
        for name, val in approach_options.items():
            if val == base_config.approach:
                default_approach = name
                break

    selected_approach_name = st.radio(
        "Quelle philosophie de trading ?",
        list(approach_options.keys()),
        index=list(approach_options.keys()).index(default_approach),
        horizontal=True,
    )
    selected_approach = approach_options[selected_approach_name]

with col2:
    render_tooltip("approach")

with st.expander("📖 Comprendre cette approche", expanded=False):
    render_strategy_explanation(selected_approach.value)

st.divider()

# Thresholds (simplified - only EV and confidence for signal generation)
st.subheader("🎚️ Seuils de Signal")

col1, col2 = st.columns(2)

with col1:
    base_config = preset_config or saved_config
    default_ev = base_config.min_ev * 100 if base_config else 8.0
    min_ev = st.slider(
        "EV Minimum (%)",
        min_value=3.0,
        max_value=20.0,
        value=default_ev,
        step=1.0,
        help=TOOLTIPS["min_ev"]["simple"],
    )
    render_tooltip("min_ev")

with col2:
    default_conf = base_config.min_confidence * 100 if base_config else 65.0
    min_confidence = st.slider(
        "Confiance Minimum (%)",
        min_value=55.0,
        max_value=85.0,
        value=default_conf,
        step=5.0,
        help=TOOLTIPS["min_confidence"]["simple"],
    )
    render_tooltip("min_confidence")

st.divider()

# Indicators
st.subheader("📊 Indicateurs Techniques")
st.markdown("Active les indicateurs que tu veux utiliser. Plus d'indicateurs = plus de filtrage mais moins de signaux.")

def get_preset_indicator(name: str) -> tuple[bool, dict]:
    base_config = preset_config or saved_config
    if not base_config:
        return name in ["rsi", "macd"], {}
    for ind in base_config.indicators:
        if ind.name == name:
            return ind.enabled, ind.params
    return False, {}

col1, col2 = st.columns(2)

with col1:
    st.markdown("**RSI (Relative Strength Index)**")
    rsi_default, rsi_params = get_preset_indicator("rsi")
    rsi_enabled = st.checkbox("Activer RSI", value=rsi_default)
    if rsi_enabled:
        rsi_period = st.select_slider(
            "Période RSI",
            options=[7, 14, 21],
            value=rsi_params.get("period", 14),
            help="7=réactif, 14=standard, 21=lissé"
        )
    else:
        rsi_period = 14
    render_tooltip("rsi")

with col2:
    st.markdown("**MACD (Moving Average Convergence Divergence)**")
    macd_default, macd_params = get_preset_indicator("macd")
    macd_enabled = st.checkbox("Activer MACD", value=macd_default)
    render_tooltip("macd")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Bandes de Bollinger**")
    boll_default, boll_params = get_preset_indicator("bollinger")
    bollinger_enabled = st.checkbox("Activer Bollinger", value=boll_default)
    if bollinger_enabled:
        boll_period = st.select_slider(
            "Période Bollinger",
            options=[10, 20, 30],
            value=boll_params.get("period", 20),
        )
    else:
        boll_period = 20
    render_tooltip("bollinger")

with col2:
    st.markdown("**EMA Cross (Croisement de moyennes)**")
    ema_default, _ = get_preset_indicator("ema_cross")
    ema_enabled = st.checkbox("Activer EMA Cross", value=ema_default)

st.divider()

# Build config
indicators = []
if rsi_enabled:
    indicators.append(IndicatorConfig(name="rsi", enabled=True, params={"period": rsi_period}))
if macd_enabled:
    indicators.append(IndicatorConfig(name="macd", enabled=True, params={"fast": 12, "slow": 26, "signal": 9}))
if bollinger_enabled:
    indicators.append(IndicatorConfig(name="bollinger", enabled=True, params={"period": boll_period, "std": 2.0}))
if ema_enabled:
    indicators.append(IndicatorConfig(name="ema_cross", enabled=True, params={"fast": 9, "slow": 21}))

# Create config with defaults for money-related fields (used by Paper Trading)
strategy_config = StrategyConfig(
    name=selected_preset if selected_preset != "Personnalisé" else "Stratégie Personnalisée",
    approach=selected_approach,
    min_ev=min_ev / 100,
    min_confidence=min_confidence / 100,
    indicators=indicators,
    initial_capital=1000.0,  # Default for paper trading
    max_position_pct=0.02,   # Default 2%
)

# Summary
st.subheader("📋 Résumé de ta Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Approche", selected_approach_name)

with col2:
    st.metric("EV Minimum", f"{min_ev:.0f}%")

with col3:
    st.metric("Confiance Minimum", f"{min_confidence:.0f}%")

col1, col2, col3 = st.columns(3)

with col1:
    active_indicators = [i.name.upper() for i in indicators]
    st.metric("Indicateurs", ", ".join(active_indicators) or "Aucun")

# Warnings
if not indicators:
    st.warning("Aucun indicateur activé! Ta stratégie n'aura pas de signaux.")

if min_ev < 5:
    st.warning("EV très bas. Tu risques de générer beaucoup de signaux peu fiables.")

# Save button
st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("🎯 Sauvegarder et aller au Backtest", type="primary", use_container_width=True):
        st.session_state.strategy_config = strategy_config
        st.success("Configuration sauvegardée!")
        st.balloons()

with col2:
    if st.button("📈 Sauvegarder et aller au Paper Trading", type="secondary", use_container_width=True):
        st.session_state.strategy_config = strategy_config
        st.success("Configuration sauvegardée!")
        st.page_link("pages/6_Paper_Trading_Live.py", label="Aller au Paper Trading", icon="📈")
