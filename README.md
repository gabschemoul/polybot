# PolyBot 🎰

**Laboratoire de Trading Pédagogique pour Polymarket**

PolyBot est un outil d'apprentissage du trading quantitatif sur les marchés de prédiction Polymarket (créneaux Bitcoin 15 minutes).

## 🎯 Objectif

Apprendre le trading quantitatif en :
- Configurant et testant des stratégies sur données historiques
- Comprenant les résultats grâce à des explications IA
- Accumulant des insights dans une base de connaissances

## 🚀 Installation

### Prérequis
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommandé) ou pip

### Installation avec uv

```bash
# Cloner le projet
cd PolyBot

# Créer l'environnement et installer les dépendances
uv sync

# Copier le fichier de configuration
cp .env.example .env
```

### Configuration

Édite le fichier `.env` :

```bash
# Obligatoire pour les explications IA
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optionnel
POLYMARKET_API_KEY=
```

## 📖 Utilisation

### Lancer l'interface

```bash
uv run streamlit run src/polybot/ui/app.py
```

Puis ouvre http://localhost:8501 dans ton navigateur.

### Navigation

1. **🔧 Configure** — Choisis ta stratégie et paramètres
2. **🚀 Simulate** — Lance un backtest sur données historiques
3. **📊 Results** — Analyse les résultats avec l'IA
4. **📚 Knowledge** — Consulte ta base de connaissances

## 🧪 Concepts Clés

### Expected Value (EV)

```
EV = (Probabilité de Gagner × Gain) - (Probabilité de Perdre × Mise)
```

Une EV positive signifie un avantage mathématique sur le long terme.

### Indicateurs Techniques

| Indicateur | Ce qu'il mesure |
|------------|-----------------|
| **RSI** | Suracheté (>70) ou survendu (<30) |
| **MACD** | Changements de momentum |
| **Bollinger** | Volatilité et extrêmes |
| **EMA Cross** | Tendance court terme |

### Stratégies

- **Momentum** — Suivre la tendance ("ce qui monte continue")
- **Mean Reversion** — Parier sur les corrections ("les excès se corrigent")
- **Auto** — L'IA choisit selon les conditions

## 🧪 Tests

```bash
uv run pytest
```

## 📁 Structure du Projet

```
polybot/
├── src/polybot/
│   ├── brain/          # Logique de trading (indicateurs, EV)
│   ├── data/           # Clients API (Binance, Polymarket)
│   ├── storage/        # Persistance (simulations, insights)
│   ├── tutor/          # IA pédagogique (Claude)
│   ├── ui/             # Interface Streamlit
│   └── config/         # Configuration
├── data/               # Données (simulations, cache)
└── tests/              # Tests unitaires
```

## ⚠️ Avertissement

Ce projet est **uniquement éducatif**. Ne pas utiliser pour du trading réel sans :
- Comprendre les risques financiers
- Valider les stratégies sur un échantillon statistiquement significatif
- Avoir du capital que vous pouvez vous permettre de perdre

## 📄 Licence

MIT — Projet éducatif personnel
