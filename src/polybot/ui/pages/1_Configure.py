"""Strategy configuration page."""

import streamlit as st

from polybot.brain.models import IndicatorConfig, PositionSizing, StrategyApproach, StrategyConfig
from polybot.config.presets import list_presets, get_preset
from polybot.tutor.prompts import TOOLTIPS
from polybot.ui.components.tooltips import render_tooltip, render_strategy_explanation

st.set_page_config(page_title="Configure - PolyBot", page_icon="🔧", layout="wide")

st.title("🔧 Configure ta Stratégie")

st.markdown("""
Configure les paramètres de ta stratégie de trading. Chaque paramètre a une
explication pour t'aider à comprendre son impact.
""")

# Initialize session state
if "strategy_config" not in st.session_state:
    st.session_state.strategy_config = None

st.divider()

# Preset selection
st.subheader("📦 Stratégies Pré-configurées")
st.markdown("Choisis une stratégie de base ou personnalise entièrement.")

presets = list_presets()
preset_options = ["Personnalisé"] + [p["name"] for p in presets]

selected_preset = st.selectbox(
    "Commencer avec:",
    preset_options,
    help="Les presets sont des configurations testées pour débuter. Tu peux les modifier ensuite."
)

# Load preset if selected
if selected_preset != "Personnalisé":
    preset_id = next(p["id"] for p in presets if p["name"] == selected_preset)
    preset_config, preset_desc = get_preset(preset_id)
    st.info(f"💡 {preset_desc}")
else:
    preset_config = None

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
    if preset_config:
        for name, val in approach_options.items():
            if val == preset_config.approach:
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

# Show approach explanation
with st.expander("📖 Comprendre cette approche", expanded=False):
    render_strategy_explanation(selected_approach.value)

st.divider()

# Thresholds
st.subheader("🎚️ Seuils de Décision")

col1, col2, col3 = st.columns(3)

with col1:
    default_ev = preset_config.min_ev * 100 if preset_config else 8.0
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
    default_conf = preset_config.min_confidence * 100 if preset_config else 65.0
    min_confidence = st.slider(
        "Confiance Minimum (%)",
        min_value=55.0,
        max_value=85.0,
        value=default_conf,
        step=5.0,
        help=TOOLTIPS["min_confidence"]["simple"],
    )
    render_tooltip("min_confidence")

with col3:
    default_pos = preset_config.max_position_pct * 100 if preset_config else 2.0
    max_position = st.slider(
        "Position Max (%)",
        min_value=1.0,
        max_value=10.0,
        value=default_pos,
        step=0.5,
        help=TOOLTIPS["max_position_pct"]["simple"],
    )
    render_tooltip("max_position_pct")

st.divider()

# Position Sizing Method
st.subheader("📐 Méthode de Position Sizing")

col1, col2 = st.columns([2, 1])

with col1:
    sizing_options = {
        "Kelly Criterion (Recommandé)": PositionSizing.KELLY,
        "Fixe": PositionSizing.FIXED,
        "Martingale (Dangereux!)": PositionSizing.MARTINGALE,
    }

    default_sizing = "Kelly Criterion (Recommandé)"
    if preset_config and hasattr(preset_config, 'position_sizing'):
        for name, val in sizing_options.items():
            if val == preset_config.position_sizing:
                default_sizing = name
                break

    selected_sizing_name = st.radio(
        "Comment calculer la taille des positions ?",
        list(sizing_options.keys()),
        index=list(sizing_options.keys()).index(default_sizing),
        horizontal=True,
    )
    selected_sizing = sizing_options[selected_sizing_name]

with col2:
    render_tooltip("position_sizing")

# Martingale warning and base position
martingale_base = 1.0
if selected_sizing == PositionSizing.MARTINGALE:
    st.warning("""
    ⚠️ **ATTENTION: La Martingale est extrêmement risquée !**

    Cette méthode double ta mise après chaque perte. Une série de 6 pertes
    consécutives avec une base de 1% nécessite 64% de ton capital sur un seul trade !

    **Utilise uniquement pour comprendre pourquoi cette stratégie échoue.**
    """)

    martingale_base = st.slider(
        "Position de base Martingale (%)",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.5,
        help="La mise initiale. Après chaque perte, elle est doublée."
    )
    render_tooltip("martingale")

st.divider()

# Indicators
st.subheader("📊 Indicateurs Techniques")
st.markdown("Active les indicateurs que tu veux utiliser. Plus d'indicateurs = plus de filtrage mais moins de trades.")

# Get default indicator settings from preset
def get_preset_indicator(name: str) -> tuple[bool, dict]:
    if not preset_config:
        return name in ["rsi", "macd"], {}
    for ind in preset_config.indicators:
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

# Capital
st.subheader("💰 Capital de Simulation")

default_capital = preset_config.initial_capital if preset_config else 1000.0
initial_capital = st.number_input(
    "Capital initial ($)",
    min_value=100.0,
    max_value=100000.0,
    value=default_capital,
    step=100.0,
    help="Le capital fictif pour ta simulation. Commence petit pour apprendre."
)

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

strategy_config = StrategyConfig(
    name=selected_preset if selected_preset != "Personnalisé" else "Stratégie Personnalisée",
    approach=selected_approach,
    min_ev=min_ev / 100,
    min_confidence=min_confidence / 100,
    indicators=indicators,
    initial_capital=initial_capital,
    max_position_pct=max_position / 100,
    position_sizing=selected_sizing,
    martingale_base_pct=martingale_base / 100,
)

# Summary
st.subheader("📋 Résumé de ta Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Approche", selected_approach_name)
    st.metric("EV Minimum", f"{min_ev:.0f}%")

with col2:
    st.metric("Confiance Minimum", f"{min_confidence:.0f}%")
    st.metric("Position Max", f"{max_position:.1f}%")

with col3:
    st.metric("Capital", f"${initial_capital:,.0f}")
    sizing_display = {
        PositionSizing.KELLY: "Kelly",
        PositionSizing.FIXED: "Fixe",
        PositionSizing.MARTINGALE: "Martingale ⚠️",
    }
    st.metric("Position Sizing", sizing_display[selected_sizing])

# Additional row for indicators
st.markdown("")  # spacer
col1, col2, col3 = st.columns(3)
with col1:
    active_indicators = [i.name.upper() for i in indicators]
    st.metric("Indicateurs", ", ".join(active_indicators) or "Aucun")

# Warnings
if not indicators:
    st.warning("⚠️ Aucun indicateur activé ! Ta stratégie n'aura pas de signaux.")

if min_ev < 5:
    st.warning("⚠️ EV très bas. Tu risques de trader sur du bruit statistique.")

# Save button
st.divider()

if st.button("✅ Sauvegarder et Continuer vers Simulation", type="primary", use_container_width=True):
    st.session_state.strategy_config = strategy_config
    st.success("Configuration sauvegardée ! Va sur la page Simulation pour lancer un backtest.")
    st.balloons()
