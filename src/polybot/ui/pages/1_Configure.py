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

# Use saved config as base if available
saved_config = st.session_state.strategy_config

st.divider()

# Preset selection
st.subheader("📦 Stratégies Pré-configurées")
st.markdown("Choisis une stratégie de base ou personnalise entièrement.")

presets = list_presets()
preset_options = ["Personnalisé"] + [p["name"] for p in presets]

# Default to saved config name if it matches a preset
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
    help="Les presets sont des configurations testées pour débuter. Tu peux les modifier ensuite."
)

# Load preset if selected, otherwise use saved config
if selected_preset != "Personnalisé":
    preset_id = next(p["id"] for p in presets if p["name"] == selected_preset)
    preset_config, preset_desc = get_preset(preset_id)
    st.info(f"💡 {preset_desc}")
else:
    preset_config = saved_config  # Use saved config as base

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

# Show approach explanation
with st.expander("📖 Comprendre cette approche", expanded=False):
    render_strategy_explanation(selected_approach.value)

st.divider()

# Thresholds
st.subheader("🎚️ Seuils de Décision")

col1, col2, col3 = st.columns(3)

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

with col3:
    default_pos = base_config.max_position_pct * 100 if base_config else 2.0
    max_position = st.slider(
        "Position Max (%)",
        min_value=1.0,
        max_value=10.0,
        value=default_pos,
        step=0.5,
        help=TOOLTIPS["max_position_pct"]["simple"],
    )
    render_tooltip("max_position_pct")

# Fees/slippage
st.markdown("#### Frais & Slippage")
col1, col2 = st.columns([2, 1])
with col1:
    default_fee = (base_config.fee_pct * 100) if (base_config and hasattr(base_config, 'fee_pct')) else 1.0
    fee_pct = st.slider(
        "Frais/Slippage (%)",
        min_value=0.0,
        max_value=5.0,
        value=default_fee,
        step=0.5,
        help="Pourcentage déduit des gains pour simuler les frais de trading et le slippage (entrée à un prix moins favorable)."
    )
with col2:
    st.info("💡 Sur Polymarket, compte ~1-2% de slippage + frais. Mets 0% pour un backtest optimiste.")

# Take Profit
st.markdown("#### Take Profit (Sortie anticipée)")
col1, col2 = st.columns([2, 1])
with col1:
    default_tp_enabled = (base_config.take_profit_enabled) if (base_config and hasattr(base_config, 'take_profit_enabled')) else False
    take_profit_enabled = st.checkbox(
        "Activer Take Profit",
        value=default_tp_enabled,
        help="Sortir du trade quand le prix atteint un certain niveau au lieu d'attendre la résolution"
    )

    default_tp_pct = (base_config.take_profit_pct * 100) if (base_config and hasattr(base_config, 'take_profit_pct')) else 90.0
    take_profit_pct = default_tp_pct
    if take_profit_enabled:
        take_profit_pct = st.slider(
            "Niveau de sortie (%)",
            min_value=60.0,
            max_value=99.0,
            value=default_tp_pct,
            step=5.0,
            help="Sortir quand le prix du marché atteint ce niveau (ex: 90% = vendre quand le YES atteint $0.90)"
        )
with col2:
    if take_profit_enabled:
        st.info(f"💡 Tu sortiras quand le prix atteint {take_profit_pct:.0f}% au lieu d'attendre 100% (résolution).")

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
    base_config = preset_config or saved_config
    if base_config and hasattr(base_config, 'position_sizing'):
        for name, val in sizing_options.items():
            if val == base_config.position_sizing:
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
default_martingale = 1.0
if base_config and hasattr(base_config, 'martingale_base_pct'):
    default_martingale = base_config.martingale_base_pct * 100

martingale_base = default_martingale
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
        value=default_martingale,
        step=0.5,
        help="La mise initiale. Après chaque perte, elle est doublée."
    )
    render_tooltip("martingale")

st.divider()

# Indicators
st.subheader("📊 Indicateurs Techniques")
st.markdown("Active les indicateurs que tu veux utiliser. Plus d'indicateurs = plus de filtrage mais moins de trades.")

# Get default indicator settings from preset or saved config
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

# Capital
st.subheader("💰 Capital de Simulation")

base_config = preset_config or saved_config
default_capital = base_config.initial_capital if base_config else 1000.0
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
    fee_pct=fee_pct / 100,
    take_profit_enabled=take_profit_enabled,
    take_profit_pct=take_profit_pct / 100,
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
    st.metric("Frais/Slippage", f"{fee_pct:.1f}%")

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

col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Sauvegarder et Continuer vers Simulation", type="primary", use_container_width=True):
        st.session_state.strategy_config = strategy_config
        st.success("Configuration sauvegardée ! Va sur la page Simulation pour lancer un backtest.")
        st.balloons()

with col2:
    with st.expander("💾 Sauvegarder dans le Classement"):
        st.markdown("Donne un nom à ta stratégie pour la sauvegarder et la comparer avec d'autres.")

        strategy_name = st.text_input(
            "Nom de la stratégie",
            value=strategy_config.name,
            placeholder="Ex: Ma Stratégie Momentum Aggressive"
        )
        author_name = st.text_input(
            "Ton pseudo",
            placeholder="Ex: TraderPro42"
        )

        if st.button("💾 Sauvegarder pour le Classement", use_container_width=True):
            if strategy_name and author_name:
                from polybot.storage import get_strategy_store
                store = get_strategy_store()
                saved = store.create_from_config(strategy_config, strategy_name, author_name)
                st.session_state.strategy_config = strategy_config
                st.session_state.saved_strategy_id = saved.id
                st.success(f"✅ Stratégie '{strategy_name}' sauvegardée ! ID: {saved.id}")
            else:
                st.warning("Remplis le nom et ton pseudo.")
