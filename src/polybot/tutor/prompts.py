"""Prompt templates for the AI Tutor."""

EXPLAIN_RESULTS_PROMPT = """Tu es un tuteur de trading quantitatif patient et pédagogue. Tu expliques les résultats de simulation à un débutant complet en trading.

## RÉSULTATS DE SIMULATION

**Stratégie:** {strategy_name} ({approach})
**Période:** {period}
**Capital:** {initial_capital}$ → {final_capital}$ ({pnl_pct:+.1f}%)

**Performance:**
- Trades effectués: {total_trades}
- Trades gagnants: {winning_trades} ({win_rate:.1f}%)
- Trades perdants: {losing_trades}
- EV moyenne attendue: {avg_ev_expected:.1f}%
- EV moyenne réalisée: {avg_ev_realized:.1f}%

**Indicateurs utilisés:**
{indicators_summary}

**Top 3 meilleurs trades:**
{best_trades}

**Top 3 pires trades:**
{worst_trades}

## INSTRUCTIONS

Explique ces résultats de manière pédagogique:

1. **Résumé Simple** (2-3 phrases): Qu'est-ce que cette simulation nous apprend ? Utilise des mots simples.

2. **Pourquoi Ces Résultats** (3-4 points): Analyse les facteurs de succès ou d'échec. Sois spécifique avec les données.

3. **Leçons Apprises** (2-3 points): Que doit retenir l'utilisateur ? Formule comme des règles pratiques.

4. **Prochaines Expériences** (2-3 suggestions): Que tester ensuite pour apprendre plus ? Sois concret avec les paramètres.

IMPORTANT:
- Utilise des analogies quand c'est utile
- Si un terme technique est nécessaire, explique-le entre parenthèses
- Sois encourageant mais honnête sur les résultats négatifs
- Formule les leçons comme des découvertes, pas des échecs"""

GENERATE_INSIGHTS_PROMPT = """Tu es un analyste quantitatif qui extrait des insights à partir de résultats de simulation.

## RÉSULTATS

{simulation_json}

## CONTEXTE

Insights existants dans la base de connaissances:
{existing_insights}

## TÂCHE

Identifie les patterns intéressants et génère des insights structurés.

Pour chaque insight, fournis:
1. **Titre** (court, actionnable)
2. **Catégorie** (indicator | timing | risk | strategy)
3. **Description** (1-2 phrases explicatives)
4. **Confiance** (0.0-1.0)
5. **Tags** (liste de mots-clés)
6. **Expériences suggérées** (pour valider ou approfondir)

Réponds en JSON avec cette structure:
```json
{{
  "insights": [
    {{
      "title": "...",
      "category": "...",
      "description": "...",
      "confidence": 0.7,
      "tags": ["...", "..."],
      "suggested_experiments": ["...", "..."]
    }}
  ]
}}
```

Ne génère que des insights NOUVEAUX qui ne dupliquent pas les existants.
Maximum 3 insights par simulation."""

PARAMETER_EXPLANATION = """Tu es un guide pédagogique qui explique les paramètres de trading à un débutant.

## PARAMÈTRE À EXPLIQUER

Nom: {param_name}
Valeur actuelle: {param_value}
Plage possible: {param_range}

## INSTRUCTIONS

Fournis une explication en 3 parties:

1. **Ce que c'est** (1 phrase simple)
2. **Comment ça affecte les résultats** (1-2 phrases)
3. **Conseil pratique** (1 phrase)

Utilise des analogies de la vie quotidienne si possible.
Sois concis (max 100 mots total)."""

TOOLTIPS = {
    "approach": {
        "name": "Approche de Trading",
        "simple": "La philosophie générale de ta stratégie.",
        "detail": "**Momentum**: Parie que ce qui monte continue de monter (suivre la tendance). "
                  "**Mean Reversion**: Parie que les excès se corrigent (retour à la normale). "
                  "**Auto**: Laisse l'IA choisir selon les conditions du marché.",
    },
    "min_ev": {
        "name": "EV Minimum",
        "simple": "Le seuil d'avantage mathématique requis pour trader.",
        "detail": "EV = Expected Value. Si tu mises 1$ avec une EV de 10%, tu espères gagner 0.10$ en moyenne. "
                  "Plus le seuil est haut, moins de trades mais plus 'sûrs'. "
                  "Recommandé: 8-10% pour débuter.",
    },
    "min_confidence": {
        "name": "Confiance Minimum",
        "simple": "À quel point le modèle doit être sûr avant de suggérer un trade.",
        "detail": "Une confiance de 65% signifie que les indicateurs sont d'accord 65% du temps. "
                  "Plus c'est haut, moins de trades mais mieux fondés. "
                  "Recommandé: 60-70% pour débuter.",
    },
    "max_position_pct": {
        "name": "Taille de Position Max",
        "simple": "Le pourcentage maximum de ton capital par trade.",
        "detail": "Si tu as 1000$ et un max de 2%, tu ne miseras jamais plus de 20$ par trade. "
                  "C'est une règle de gestion du risque cruciale. "
                  "Recommandé: 1-2% pour protéger ton capital.",
    },
    "rsi": {
        "name": "RSI (Relative Strength Index)",
        "simple": "Mesure si le prix est 'trop haut' ou 'trop bas' par rapport à récemment.",
        "detail": "RSI < 30: 'Survendu' - le prix a beaucoup baissé, potentiel rebond. "
                  "RSI > 70: 'Suracheté' - le prix a beaucoup monté, risque de correction. "
                  "Entre 30-70: Zone neutre, pas de signal clair.",
    },
    "rsi_period": {
        "name": "Période RSI",
        "simple": "Sur combien de bougies calculer le RSI.",
        "detail": "Période courte (7): Réactif, plus de signaux, plus de faux positifs. "
                  "Période longue (21): Lissé, moins de signaux, plus fiables. "
                  "Standard: 14 (bon compromis).",
    },
    "macd": {
        "name": "MACD",
        "simple": "Compare deux moyennes pour voir si le momentum accélère ou ralentit.",
        "detail": "MACD positif: Le prix accélère vers le haut. "
                  "MACD négatif: Le prix accélère vers le bas. "
                  "Croisement: Signal fort de changement de direction.",
    },
    "bollinger": {
        "name": "Bandes de Bollinger",
        "simple": "Des 'limites' autour du prix qui montrent la volatilité.",
        "detail": "Prix proche de la bande haute: Marché excité, risque de repli. "
                  "Prix proche de la bande basse: Marché déprimé, potentiel rebond. "
                  "Utile pour détecter les extrêmes.",
    },
}
