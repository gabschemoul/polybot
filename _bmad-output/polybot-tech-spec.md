# PolyBot — Spécification Technique

**Version:** 1.0
**Date:** 2026-01-28
**Auteurs:** Winston (Architect), Mary (Analyst), Paige (Tech Writer)
**Statut:** Draft — En attente de validation

---

## 1. Vision du Produit

### 1.1 Résumé Exécutif

**PolyBot** est un laboratoire de trading pédagogique pour les marchés de prédiction Polymarket (créneaux Bitcoin 15 minutes). L'outil permet à trois utilisateurs privés de :

- Configurer et tester des stratégies de trading quantitatif
- Apprendre les concepts de trading via une interface pédagogique
- Accumuler des insights dans une base de connaissances persistante
- Identifier des opportunités à Expected Value (EV) positive

### 1.2 Utilisateurs Cibles

| Utilisateur | Profil | Besoin Principal |
|-------------|--------|------------------|
| Gab | Débutant en trading, tech-savvy | Apprendre + valider des stratégies |
| Ami 1 | Trader amateur | Tester des hypothèses |
| Ami 2 | Trader amateur | Optimiser ses décisions |

### 1.3 Philosophie Clé

> "Ne pas deviner le futur, mais calculer des probabilités et laisser les données décider."

---

## 2. Fonctionnalités

### 2.1 Modes de Fonctionnement

| Mode | Description | Priorité | Phase |
|------|-------------|----------|-------|
| **Test (Paper Trading)** | Paris simulés avec capital fictif | HAUTE | MVP |
| **Conseil** | Signaux affichés, décision manuelle | MOYENNE | Phase 2 |
| **Auto** | Exécution automatique des trades | BASSE | Phase 3+ |

### 2.2 Fonctionnalités MVP (Phase 1)

#### 2.2.1 Configuration de Stratégie

```
┌─────────────────────────────────────────────────────────┐
│  STRATEGY CONFIGURATOR                                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📖 Approche Générale                          [?]      │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ○ Momentum — "Ce qui monte continue"            │    │
│  │ ○ Mean Reversion — "Les excès se corrigent"    │    │
│  │ ● Auto (AI décide) — Recommandé pour débuter   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  📊 Seuil EV Minimum                           [?]      │
│  │ Tooltip: "Ne considérer que les paris avec un  │     │
│  │ avantage mathématique supérieur à ce %"        │     │
│  [━━━━━━━●━━━] 8%                                       │
│                                                          │
│  🎯 Confiance Minimum                          [?]      │
│  │ Tooltip: "Probabilité minimum que le modèle    │     │
│  │ doit avoir pour émettre un signal"             │     │
│  [━━━━━━●━━━━] 65%                                      │
│                                                          │
│  📈 Indicateurs Techniques                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │ [✓] RSI (Relative Strength Index)        [?]   │    │
│  │     Période: [14 ▼]                             │    │
│  │     "Détecte les conditions suracheté/survendu" │    │
│  │                                                  │    │
│  │ [✓] MACD (Moving Average Convergence)    [?]   │    │
│  │     "Identifie les changements de momentum"     │    │
│  │                                                  │    │
│  │ [ ] Bollinger Bands                       [?]   │    │
│  │     "Mesure la volatilité et les extrêmes"     │    │
│  │                                                  │    │
│  │ [ ] EMA Cross (9/21)                      [?]   │    │
│  │     "Signal de tendance court terme"            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  💰 Gestion du Risque                                   │
│  │ Capital de départ: [1000] $                    │     │
│  │ Mise max par pari: [2%] du capital             │     │
│                                                          │
│  [        🚀 Lancer la Simulation        ]              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### 2.2.2 Moteur de Calcul (Brain Engine)

**Entrées:**
- Prix BTC temps réel (via Binance API)
- Cotes Polymarket (via Polymarket CLOB API)
- Paramètres de stratégie configurés

**Processus:**
```
1. COLLECTE DES DONNÉES
   ├── Récupérer prix BTC (OHLCV 1min, 5min, 15min)
   ├── Calculer indicateurs techniques sélectionnés
   └── Récupérer cotes actuelles Polymarket

2. CALCUL DE PROBABILITÉ
   ├── Appliquer le modèle (momentum ou mean reversion)
   ├── Combiner les signaux des indicateurs
   └── Générer probabilité estimée (0-100%)

3. CALCUL DE L'EDGE
   ├── Comparer probabilité estimée vs prix marché
   ├── Calculer Expected Value
   └── Appliquer seuils configurés

4. DÉCISION
   ├── EV >= seuil ET confiance >= seuil → SIGNAL
   └── Sinon → PAS DE SIGNAL
```

**Sortie:**
```json
{
  "timestamp": "2026-01-28T14:30:00Z",
  "market": "BTC-15MIN-UP",
  "market_price": 0.45,
  "model_probability": 0.62,
  "expected_value": 0.152,
  "confidence": 0.72,
  "signal": "BUY",
  "reasoning": {
    "rsi": {"value": 28, "interpretation": "Survendu"},
    "macd": {"value": -0.02, "interpretation": "Divergence haussière"}
  }
}
```

#### 2.2.3 Interface de Résultats Pédagogique

```
┌─────────────────────────────────────────────────────────┐
│  📊 RÉSULTATS — Simulation #47                          │
│  Stratégie: Mean Reversion + RSI(14) + MACD             │
│  Période: 7 jours | 142 créneaux analysés               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  💰 PERFORMANCE                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Capital initial:     1,000.00 $                 │    │
│  │ Capital final:       1,082.30 $                 │    │
│  │ Profit/Perte:        +82.30 $ (+8.23%)         │    │
│  │                                                  │    │
│  │ Paris effectués:     23                         │    │
│  │ Gagnants:            15 (65.2%)                 │    │
│  │ Perdants:            8 (34.8%)                  │    │
│  │ EV moyenne réalisée: +7.8%                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  📖 POURQUOI CES RÉSULTATS?                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ✓ Le RSI à 14 a correctement identifié 12      │    │
│  │   retournements sur 15 signaux (80% précision)  │    │
│  │                                                  │    │
│  │ ✗ 3 faux signaux quand la volatilité était     │    │
│  │   élevée (ATR > 2.5%). Le modèle n'intègre     │    │
│  │   pas encore de filtre de volatilité.           │    │
│  │                                                  │    │
│  │ ⚠️ Performance dégradée entre 22h-02h UTC       │    │
│  │   (marché moins liquide, plus de bruit)         │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  💡 CE QUE VOUS AVEZ APPRIS                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. Mean reversion + RSI(14) = combo efficace   │    │
│  │    sur ce type de marché                        │    │
│  │                                                  │    │
│  │ 2. Votre seuil EV de 8% filtre bien le bruit   │    │
│  │    (vs 5% qui aurait généré 12 trades perdants) │    │
│  │                                                  │    │
│  │ 3. La volatilité impacte la fiabilité des      │    │
│  │    signaux — piste d'amélioration identifiée    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  🔬 EXPÉRIENCES SUGGÉRÉES                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Basé sur ces résultats, testez:                 │    │
│  │                                                  │    │
│  │ [▶️ Lancer] Ajouter filtre volatilité < 2%      │    │
│  │            Hypothèse: +3-5% de précision        │    │
│  │                                                  │    │
│  │ [▶️ Lancer] Exclure créneaux 22h-02h UTC        │    │
│  │            Hypothèse: éviter 60% des pertes     │    │
│  │                                                  │    │
│  │ [▶️ Lancer] Tester RSI période 21 (plus lissé)  │    │
│  │            Hypothèse: moins de faux signaux     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  [📚 Sauvegarder dans Base de Connaissances]            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### 2.2.4 Base de Connaissances

**Structure des données:**

```
/_bmad-output/polybot-data/
├── simulations/
│   ├── SIM-001.json
│   ├── SIM-002.json
│   └── ...
├── insights/
│   ├── insights.json      # Liste des insights découverts
│   └── experiments.json   # Expériences suggérées/réalisées
├── config/
│   └── presets.json       # Stratégies pré-configurées
└── knowledge-base.db      # SQLite pour requêtes complexes
```

**Schéma Insight:**
```json
{
  "id": "INS-047",
  "discovered_at": "2026-01-28T15:00:00Z",
  "category": "indicator_performance",
  "title": "RSI 14 optimal pour mean reversion",
  "description": "Le RSI période 14 capture les retournements sur 15min mieux que période 7 (trop réactif) ou 21 (trop lent).",
  "evidence": {
    "simulation_ids": ["SIM-012", "SIM-023", "SIM-031"],
    "sample_size": 147,
    "confidence": 0.78,
    "metrics": {
      "win_rate": 0.68,
      "avg_ev": 0.072
    }
  },
  "tags": ["rsi", "mean-reversion", "validated"],
  "suggested_experiments": [
    "Combiner avec Bollinger Bands",
    "Tester sur créneaux nuit vs jour"
  ]
}
```

---

## 3. Architecture Technique

### 3.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                         POLYBOT ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   EXTERNAL APIS                      CORE APPLICATION            │
│  ┌─────────────┐                    ┌──────────────────────┐    │
│  │  Binance    │───── BTC Price ───▶│                      │    │
│  │  API        │                    │    DATA COLLECTOR    │    │
│  └─────────────┘                    │    (data/)           │    │
│                                     │                      │    │
│  ┌─────────────┐                    │  • fetch_btc_data()  │    │
│  │ Polymarket  │─── Market Odds ───▶│  • fetch_polymarket()│    │
│  │  CLOB API   │                    │  • cache_manager()   │    │
│  └─────────────┘                    └──────────┬───────────┘    │
│                                                 │                │
│                                                 ▼                │
│                                     ┌──────────────────────┐    │
│                                     │                      │    │
│                                     │    BRAIN ENGINE      │    │
│                                     │    (brain/)          │    │
│                                     │                      │    │
│                                     │  • indicators.py     │    │
│                                     │  • probability.py    │    │
│                                     │  • ev_calculator.py  │    │
│                                     │  • strategy.py       │    │
│                                     └──────────┬───────────┘    │
│                                                 │                │
│                                                 ▼                │
│  ┌─────────────┐                    ┌──────────────────────┐    │
│  │   Claude    │◀── Explanations ──│                      │    │
│  │    API      │                    │    AI TUTOR          │    │
│  │             │─── Analysis ──────▶│    (tutor/)          │    │
│  └─────────────┘                    │                      │    │
│                                     │  • explain_results() │    │
│                                     │  • generate_insights()│   │
│                                     │  • suggest_next()    │    │
│                                     └──────────┬───────────┘    │
│                                                 │                │
│                                                 ▼                │
│                                     ┌──────────────────────┐    │
│                                     │                      │    │
│                                     │    KNOWLEDGE BASE    │    │
│                                     │    (storage/)        │    │
│                                     │                      │    │
│                                     │  • simulations.py    │    │
│                                     │  • insights.py       │    │
│                                     │  • sqlite + json     │    │
│                                     └──────────┬───────────┘    │
│                                                 │                │
│                                                 ▼                │
│                                     ┌──────────────────────┐    │
│   USER                              │                      │    │
│  ┌─────────────┐                    │    DASHBOARD         │    │
│  │   Gab &     │◀═══ Interface ════▶│    (ui/)             │    │
│  │   Friends   │                    │                      │    │
│  └─────────────┘                    │  • Streamlit app     │    │
│                                     │  • Config panels     │    │
│                                     │  • Results views     │    │
│                                     │  • Knowledge browser │    │
│                                     └──────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Stack Technique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Langage** | Python 3.11+ | Écosystème TA/ML riche, accessibilité |
| **Indicateurs TA** | pandas-ta | Librairie complète, bien maintenue |
| **Data Processing** | pandas, numpy | Standard industrie |
| **API HTTP** | httpx (async) | Performance, simplicité |
| **Base de données** | SQLite | Léger, portable, SQL standard |
| **Stockage JSON** | json natif | Configurations, exports lisibles |
| **AI Tutor** | Claude API (Anthropic) | Qualité des explications |
| **Dashboard** | Streamlit | Prototypage rapide, interactif |
| **Environnement** | uv + pyproject.toml | Gestion moderne des dépendances |

### 3.3 Structure du Projet

```
polybot/
├── pyproject.toml           # Dépendances et config projet
├── README.md                # Documentation utilisateur
│
├── src/
│   └── polybot/
│       ├── __init__.py
│       │
│       ├── data/            # Collecte de données
│       │   ├── __init__.py
│       │   ├── binance.py   # Client API Binance
│       │   ├── polymarket.py # Client API Polymarket
│       │   └── cache.py     # Gestion du cache local
│       │
│       ├── brain/           # Moteur de calcul
│       │   ├── __init__.py
│       │   ├── indicators.py # RSI, MACD, Bollinger, etc.
│       │   ├── probability.py # Modèles de probabilité
│       │   ├── ev_calculator.py # Calcul Expected Value
│       │   └── strategy.py  # Momentum, Mean Reversion, etc.
│       │
│       ├── tutor/           # AI pédagogique
│       │   ├── __init__.py
│       │   ├── explainer.py # Génération d'explications
│       │   ├── insights.py  # Extraction d'insights
│       │   └── prompts.py   # Templates de prompts Claude
│       │
│       ├── storage/         # Persistance
│       │   ├── __init__.py
│       │   ├── database.py  # SQLite wrapper
│       │   ├── simulations.py # CRUD simulations
│       │   └── knowledge.py # CRUD insights
│       │
│       ├── ui/              # Interface utilisateur
│       │   ├── __init__.py
│       │   ├── app.py       # Point d'entrée Streamlit
│       │   ├── pages/
│       │   │   ├── 1_configure.py  # Configuration stratégie
│       │   │   ├── 2_simulate.py   # Lancer simulation
│       │   │   ├── 3_results.py    # Voir résultats
│       │   │   └── 4_knowledge.py  # Base de connaissances
│       │   └── components/
│       │       ├── tooltips.py     # Textes pédagogiques
│       │       └── charts.py       # Visualisations
│       │
│       └── config/          # Configuration
│           ├── __init__.py
│           ├── settings.py  # Settings applicatifs
│           └── presets.py   # Stratégies pré-définies
│
├── data/                    # Données persistées
│   ├── cache/               # Cache API (gitignored)
│   ├── simulations/         # Résultats des simulations
│   ├── insights/            # Insights découverts
│   └── polybot.db           # Base SQLite
│
└── tests/
    ├── test_indicators.py
    ├── test_probability.py
    ├── test_ev_calculator.py
    └── test_strategy.py
```

---

## 4. APIs Externes

### 4.1 Binance API (Données BTC)

**Endpoint:** `GET /api/v3/klines`

**Usage:**
```python
# Récupérer les 100 dernières bougies 1-minute
params = {
    "symbol": "BTCUSDT",
    "interval": "1m",
    "limit": 100
}
response = httpx.get("https://api.binance.com/api/v3/klines", params=params)
```

**Rate Limits:** 1200 requêtes/minute (largement suffisant)

**Données retournées:**
- Open, High, Low, Close (OHLC)
- Volume
- Timestamp

### 4.2 Polymarket CLOB API

**Documentation:** https://docs.polymarket.com/

**Endpoints clés:**
- `GET /markets` — Liste des marchés actifs
- `GET /markets/{id}/orderbook` — Carnet d'ordres
- `GET /prices` — Prix actuels

**Authentification:** API Key requise pour trading, lecture publique pour les prix

**Note:** Vérifier les rate limits spécifiques et les conditions d'utilisation.

### 4.3 Claude API (AI Tutor)

**Modèle:** claude-sonnet-4-20250514 (bon rapport qualité/coût)

**Usage type:**
```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": EXPLAIN_RESULTS_PROMPT.format(results=simulation_results)
    }]
)
```

---

## 5. Modèles de Données

### 5.1 Simulation

```python
@dataclass
class Simulation:
    id: str                          # "SIM-001"
    created_at: datetime
    strategy: StrategyConfig

    # Résultats
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int

    # Détails
    trades: list[Trade]
    metrics: SimulationMetrics

@dataclass
class Trade:
    timestamp: datetime
    market_id: str
    direction: Literal["UP", "DOWN"]
    entry_price: float
    model_probability: float
    expected_value: float
    result: Literal["WIN", "LOSS"]
    pnl: float
    reasoning: dict  # Détails des indicateurs
```

### 5.2 Configuration de Stratégie

```python
@dataclass
class StrategyConfig:
    # Approche
    approach: Literal["momentum", "mean_reversion", "hybrid", "auto"]

    # Seuils
    min_ev: float = 0.08         # 8% minimum
    min_confidence: float = 0.65  # 65% minimum

    # Indicateurs
    indicators: list[IndicatorConfig]

    # Risk management
    initial_capital: float = 1000.0
    max_position_pct: float = 0.02  # 2% max par trade

@dataclass
class IndicatorConfig:
    name: str                    # "rsi", "macd", "bollinger"
    enabled: bool
    params: dict                 # {"period": 14} pour RSI
```

### 5.3 Insight

```python
@dataclass
class Insight:
    id: str
    discovered_at: datetime
    category: str               # "indicator", "timing", "risk"
    title: str
    description: str

    # Preuves
    evidence_simulation_ids: list[str]
    sample_size: int
    confidence: float

    # Métriques associées
    metrics: dict

    # Suggestions
    tags: list[str]
    suggested_experiments: list[str]

    # Statut
    validated: bool = False
    validation_count: int = 0
```

---

## 6. Contenu Pédagogique

### 6.1 Glossaire Intégré (Tooltips)

| Terme | Explication Simple |
|-------|---------------------|
| **Expected Value (EV)** | L'avantage mathématique d'un pari. EV +10% signifie qu'en moyenne, vous gagnez 10 centimes par dollar misé sur le long terme. |
| **RSI** | Le "Relative Strength Index" mesure si un actif est suracheté (>70, risque de baisse) ou survendu (<30, potentiel de hausse). |
| **MACD** | Compare deux moyennes mobiles pour détecter les changements de momentum. Un croisement vers le haut = signal d'achat potentiel. |
| **Mean Reversion** | Stratégie basée sur l'idée que les prix extrêmes tendent à revenir vers leur moyenne. "Ce qui monte trop redescend." |
| **Momentum** | Stratégie basée sur l'idée que les tendances persistent. "Ce qui monte continue de monter." |
| **Confiance** | Le degré de certitude du modèle dans sa prédiction. 65% = le modèle pense avoir raison 65 fois sur 100. |
| **Kelly Criterion** | Formule mathématique pour déterminer la taille optimale d'un pari en fonction de l'edge et du risque. |

### 6.2 Templates d'Explication (AI Tutor)

**Prompt — Expliquer les résultats:**
```
Tu es un tuteur de trading quantitatif. Explique ces résultats de simulation
à un débutant de manière claire et pédagogique.

RÉSULTATS:
{simulation_json}

INSTRUCTIONS:
1. Résume la performance en termes simples
2. Explique POURQUOI la stratégie a fonctionné ou échoué
3. Identifie 2-3 apprentissages clés
4. Suggère 2-3 expériences à tester ensuite
5. Utilise des analogies quand c'est utile
6. Évite le jargon ou explique-le

FORMAT: Markdown structuré avec sections claires
```

---

## 7. Roadmap de Développement

### Phase 1 — MVP (Le Cerveau qui Apprend)

**Objectif:** Valider qu'on peut calculer un edge et tracker les résultats

| Tâche | Description | Priorité |
|-------|-------------|----------|
| Setup projet | pyproject.toml, structure, CI basique | P0 |
| Client Binance | Récupération données BTC OHLCV | P0 |
| Client Polymarket | Récupération cotes marchés 15min | P0 |
| Indicateurs TA | RSI, MACD (autres optionnels) | P0 |
| Calcul probabilité | Modèles momentum et mean reversion | P0 |
| Calcul EV | Comparaison prob vs prix marché | P0 |
| Backtesting | Simulation sur données historiques | P0 |
| Stockage résultats | JSON + SQLite basique | P0 |
| UI Configuration | Streamlit - écran de config avec tooltips | P1 |
| UI Résultats | Streamlit - affichage résultats basique | P1 |

### Phase 2 — Le Tuteur

**Objectif:** Rendre les résultats compréhensibles et actionables

| Tâche | Description | Priorité |
|-------|-------------|----------|
| Intégration Claude | API setup + prompts | P0 |
| Explications auto | Génération d'explications après simulation | P0 |
| Extraction insights | Identification patterns récurrents | P1 |
| Suggestions | Propositions d'expériences suivantes | P1 |
| Base de connaissances | UI pour naviguer les insights | P1 |

### Phase 3 — Paper Trading Temps Réel

**Objectif:** Tester en conditions réelles sans risque

| Tâche | Description | Priorité |
|-------|-------------|----------|
| Mode temps réel | Websocket Binance + polling Polymarket | P0 |
| Signaux live | Notifications quand opportunité détectée | P0 |
| Tracking P&L live | Dashboard temps réel | P1 |
| Comparaison stratégies | Tester plusieurs configs en parallèle | P2 |

### Phase 4+ — Auto Trading (Futur)

**Objectif:** Exécution automatique (quand confiance établie)

| Tâche | Description | Priorité |
|-------|-------------|----------|
| Intégration wallet | Connexion Polygon/Polymarket | P0 |
| Exécution trades | Logique d'achat/vente automatique | P0 |
| Safeguards | Limites de pertes, circuit breakers | P0 |
| Monitoring | Alertes et dashboard de suivi | P1 |

---

## 8. Risques et Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| API Polymarket change | Élevé | Moyenne | Abstraction client, tests d'intégration |
| Edge n'existe pas | Élevé | Moyenne | Phase 1 valide l'hypothèse avant investissement temps |
| Latence trop haute | Moyen | Faible | Cache agressif, optimisation si nécessaire |
| Coûts API Claude | Faible | Faible | Sonnet = économique, limiter appels |
| Complexité UI | Moyen | Moyenne | Streamlit = itération rapide, feedback early |

---

## 9. Critères de Succès

### Phase 1
- [ ] Peut exécuter une simulation backtest sur 7 jours de données
- [ ] Interface de configuration fonctionnelle avec tous les tooltips
- [ ] Résultats sauvegardés et consultables

### Phase 2
- [ ] Explications AI générées automatiquement après chaque simulation
- [ ] Au moins 10 insights dans la base de connaissances après 20 simulations
- [ ] Suggestions d'expériences pertinentes

### Validation Business
- [ ] Après 100 simulations paper trading, identifier si un edge statistiquement significatif existe
- [ ] Si oui, win rate > 55% avec EV positive sur échantillon représentatif

---

## 10. Questions Ouvertes

1. **Polymarket API:** Confirmer les rate limits et l'accès aux données historiques des cotes
2. **Données historiques BTC:** Quelle profondeur nécessaire ? (30 jours minimum suggéré)
3. **Fréquence des simulations:** Combien de créneaux 15min par jour sont réellement tradables sur Polymarket ?
4. **Multi-user:** Les 3 utilisateurs partagent-ils la même base de connaissances ou chacun la sienne ?

---

**Document rédigé par l'équipe BMAD**
🏗️ Winston (Architecture) | 📊 Mary (Requirements) | 📚 Paige (Rédaction)

*En attente de validation par Gab avant passage à l'implémentation.*
