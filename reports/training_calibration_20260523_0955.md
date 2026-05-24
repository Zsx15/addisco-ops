# Training & Calibration Suite — ADDISCO OPS

> Généré le 23 mai 2026 à 09:56:29

## 1. Résumé exécutif

| Champ | Valeur |
| --- | --- |
| Date | 23 mai 2026 09:56 |
| Utilisateur | Guilhem |
| Mode simulation | API |
| Attempts simulés | 10 |
| Régression | oui |
| Durée totale | 55.1s |
| **Verdict global** | **WARNING** |

> ⚠️ **WARNING** — Des signaux anormaux ont été détectés. Analyser avant de continuer.

### Avertissements

- ⚠️ Simulation : verdict WARNING

## 2. Résultats simulation

| Métrique | Valeur | Statut |
| --- | --- | --- |
| Attempts créées | 10/10 | ✅ |
| Score moyen (après) | 0.513 |  |
| Delta score | -0.147 | ✅ |
| Fallback rate | 0.0% | ✅ |
| Curriculum alignment | 100.0% | ✅ |
| Coût estimé | $0.002955 |  |
| Latence moy. | 3558 ms |  |
| Non évaluables | 0 |  |
| Verdict simulation | WARNING | ⚠️ |

### Distribution des erreurs simulées

| Type d'erreur | Occurrences |
| --- | --- |
| reponse_vague | 8 |
| hors_sujet | 2 |
| non_evaluable | 0 |

### Rapport simulation détaillé (COPY_FOR_ANALYSIS)

```
=== COPY_FOR_ANALYSIS_START ===
# Rapport simulation ADDISCO OPS — 2026-05-23 07:56 UTC
- User    : Guilhem
- Mode    : api
- N       : 10 entrées | seed=42
- Verdict : **WARNING**

## État AVANT
- Score moyen  : 0.660
- Fragile      : resolution_problemes, synthese_reformulation, comprehension_procedure, evaluation_critique
- Persistants  : reponse_vague, hors_sujet, oubli_etape
- Curriculum   : question_directe

## Delta session
- Score        : -0.147
- Saved        : 10/10
- Fallback     : 0.0%
- Alignment    : 100.0%
- Coût         : $0.002955
- Latence moy  : 3558 ms
- non_evaluable: 0

## Distribution error_type
- reponse_vague: 8
- hors_sujet: 2

## État APRÈS
- Score moyen  : 0.513
- Fragile      : resolution_problemes, synthese_reformulation, comprehension_procedure, evaluation_critique
- Persistants  : reponse_vague, hors_sujet, oubli_etape
- Curriculum   : question_directe

## Tableau session (10 premiers)
| Q | doc | qtype | profil | score | error_type | cur | latency |
|---|-----|-------|--------|-------|------------|-----|---------|
| Q01 | 4 | question_directe | correct      | 0.20 | reponse_vague | ✓ | 3560ms |
| Q02 | 4 | question_directe | correct      | 0.20 | reponse_vague | ✓ | 3572ms |
| Q03 | 4 | cas_pratique | correct      | 0.40 | reponse_vague | ✓ | 4552ms |
| Q04 | 4 | question_directe | correct      | 0.20 | reponse_vague | ✓ | 2837ms |
| Q05 | 4 | question_directe | correct      | 0.20 | reponse_vague | ✓ | 3684ms |
| Q06 | 4 | cas_pratique | partielle    | 0.40 | reponse_vague | ✓ | 4367ms |
| Q07 | 4 | question_directe | correct      | 0.00 | hors_sujet | ✓ | 2844ms |
| Q08 | 4 | question_directe | partielle    | 0.20 | reponse_vague | ✓ | 3116ms |
| Q09 | 4 | cas_pratique | partielle    | 0.50 | reponse_vague | ✓ | 4265ms |
| Q10 | 14 | question_directe | oubli_etape  | 0.20 | hors_sujet | ✓ | 2781ms |
=== COPY_FOR_ANALYSIS_END ===
```

## 3. Résultats calibration moteur

Tous les scripts de calibration opèrent en read-only sur des DB temporaires. `engine/thresholds.py` n'est jamais modifié.

| Paramètre | Valeur actuelle | Script | Résultat |
| --- | --- | --- | --- |
| `MASTERY_MIN_ATTEMPTS` | 5 | `mastery_threshold` | ✅ PASS |
| `MASTERY_FRAGILE` | 0.60 | `mastery_boundaries` | ✅ PASS |
| `MASTERY_MASTERED` | 0.80 | `mastery_boundaries` | ✅ PASS |
| `ADAPTIVE_FORCE_EASY` | 0.40 | `adaptive_difficulty` | ✅ PASS |
| `ADAPTIVE_ALLOW_HARD` | 0.65 | `adaptive_difficulty` | ✅ PASS |
| `REVIEW_INTERVALS` | 1/3/7 j | `review_intervals` | ✅ PASS |

### Détail : mastery_threshold

**Statut :** ✅ OK

**Sortie (fin) :**
```
ERY_FRAGILE    : 0.6
- MASTERY_MASTERED   : 0.8

## Résultats comparatifs

| MIN_ATTEMPTS | Fragile→En cours | En cours→Acquis | Verdict |
|---|---|---|---|
| 3 | Q1 | Q3 | TOO_FAST |
| 5 ← actuel | Q1 | Q5 | OK |
| 8 | Q1 | Q8 | OK |

## Interprétation
- ← (Fragile→En cours) : première tentative avec score >= 0.6
- ★ (En cours→Acquis)  : score >= 0.8 ET n >= MIN_ATTEMPTS

## Recommandation
MASTERY_MIN_ATTEMPTS = 8 recommandé : 'Acquis' atteint à Q8 — équilibre réactivité / robustesse.

## Risques
- TOO_FAST : l'apprenant est déclaré 'Acquis' après trop peu de tentatives
  → risque de sous-entraînement, révision espacée trop rare
- TOO_SLOW : l'apprenant reste 'En cours' longtemps malgré de bons scores
  → risque de démotivation, curriculum trop conservateur
=== COPY_FOR_ANALYSIS_END ===
```

### Détail : mastery_boundaries

**Statut :** ✅ OK

**Sortie (fin) :**
```
F | F | C | C | C | C | C | C |
| 0.60 ← | F | F | F | F | C | C | C | C |
| 0.65 | F | F | F | F | F | F | C | C |

## SECTION B — MASTERY_MASTERED
| MASTERY_MASTERED | s=0.70 | s=0.74 | s=0.77 | s=0.79 | s=0.81 | s=0.83 | s=0.87 | s=0.92 |
|---|---|---|---|---|---|---|---|---|
| 0.75 | C | C | A | A | A | A | A | A |
| 0.78 | C | C | C | A | A | A | A | A |
| 0.80 ← | C | C | C | C | A | A | A | A |
| 0.83 | C | C | C | C | C | A | A | A |
| 0.85 | C | C | C | C | C | C | A | A |

## SECTION C — DB pipeline
| Score | n | Attendu | Observé | Résultat |
|---|---|---|---|---|
| 0.58 | 5 | Fragile | Fragile | PASS |
| 0.62 | 5 | En cours | En cours | PASS |
| 0.79 | 5 | En cours | En cours | PASS |
| 0.82 | 5 | Acquis | Acquis | PASS |

DB pipeline : 4/4 PASS

=== COPY_FOR_ANALYSIS_END ===
```

### Détail : adaptive_difficulty

**Statut :** ✅ OK

**Sortie (fin) :**
```
APTIVE_ALLOW_HARD actuel : 0.65
- Contexte test : mastery=Maîtrisé, graph_level=2

## SECTION A — ADAPTIVE_FORCE_EASY
| FORCE_EASY | avg=0.28 | avg=0.33 | avg=0.37 | avg=0.40 | avg=0.43 | avg=0.47 | avg=0.52 | avg=0.57 |
|---|---|---|---|---|---|---|---|---|
| 0.35 | E | E | M | M | M | M | M | M |
| 0.40 ← | E | E | E | M | M | M | M | M |
| 0.45 | E | E | E | E | E | M | M | M |
| 0.50 | E | E | E | E | E | E | M | M |

## SECTION B — ADAPTIVE_ALLOW_HARD
| ALLOW_HARD | avg=0.55 | avg=0.60 | avg=0.63 | avg=0.65 | avg=0.68 | avg=0.70 | avg=0.75 | avg=0.82 |
|---|---|---|---|---|---|---|---|---|
| 0.60 | M | H | H | H | H | H | H | H |
| 0.65 ← | M | M | M | H | H | H | H | H |
| 0.70 | M | M | M | M | M | H | H | H |
| 0.75 | M | M | M | M | M | M | H | H |

=== COPY_FOR_ANALYSIS_END ===
```

### Détail : review_intervals

**Statut :** ✅ OK

**Sortie (fin) :**
```
complets

| Mastery | Amélioration | Stable | Dégradation | N/A |
|---|---|---|---|---|
| Fragile | 2j | 1j | 1j | 1j |
| En consolidation | 5j | 3j | 2j | 3j |
| Maîtrisé | 7j | 7j | 7j | 7j |

## SECTION C — Sensibilité (corpus 10 chunks)

| Intervalle set | T+0j | T+3j | T+7j | T+14j |
|---|---|---|---|---|
| 1/3/7  (actuel) | 5/10 | 9/10 | 10/10 | 10/10 |
| 1/5/14 | 4/10 | 7/10 | 8/10 | 10/10 |
| 2/7/21 | 2/10 | 5/10 | 7/10 | 8/10 |

## Conclusion
- 1/3/7 : pression de révision élevée (5/10 en retard dès T=0)
- 1/5/14 : intermédiaire (4/10)
- 2/7/21 : pression faible (2/10) — adapté aux apps hebdomadaires
- 1/3/7 aligne avec le système Leitner (formation professionnelle quotidienne)
- Optimisation fine requiert données de rétention réelles (>30j d'usage)
=== COPY_FOR_ANALYSIS_END ===
```

## 4. Résultats tests de régression

**Statut :** ✅ OK

| Champ | Valeur |
| --- | --- |
| Tests exécutés | 254 |
| Résultat | OK |
| Durée | 4.1s |


## 5. Signaux à surveiller

- ✅ Score qui chute fortement (< -0.15)
- ✅ Fallback > 20%
- ✅ Alignment curriculum < 20%
- ✅ Aucun attempt sauvegardé
- ✅ Tests régression KO

> Aucun signal anormal détecté.

## 6. Recommandation finale

Des signaux anormaux ont été détectés mais aucune défaillance bloquante.

**Actions recommandées :**
- Analyser les avertissements listés en section 1
- Reproduire manuellement sur les sections concernées
- Ne pas bloquer le merge, mais surveiller en production

---
*Rapport généré par `run_training_calibration_suite.py` — ADDISCO OPS · 23 mai 2026*