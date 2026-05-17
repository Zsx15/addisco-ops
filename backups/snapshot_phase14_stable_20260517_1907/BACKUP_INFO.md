# BACKUP_INFO — Snapshot Phase 14 Stable

## Identification

| Champ              | Valeur                                          |
|--------------------|--------------------------------------------------|
| Date               | 2026-05-17                                       |
| Heure              | 19:07                                            |
| Commit Git (short) | `0169d9c`                                        |
| Commit Git (full)  | `0169d9c24926c20fc705f9287fcc358fced4408b`       |
| Branche            | `main`                                           |
| Tests validés      | **168 tests — 0 régression**                    |
| État               | Phase 14 complète — stable — prête Phase 15      |

---

## Résumé Phase 14

Phase 14 = 4 TASKs livrées sur le moteur adaptatif :

### TASK-048 — Plan de session adaptatif (build_session_plan)
- `build_session_plan()` — fonction pure dans `adaptive_engine.py`
- `get_next_session_plan()` — wrapper DB dans `database.py`
- 12 objectifs pédagogiques, durée estimée, priority scoring

### TASK-049 — Profil apprenant enrichi
- `compute_momentum()` — élan récent (fenêtre 7 jours)
- `compute_learning_velocity()` — vitesse d'apprentissage (pente de progression)
- `compute_consistency_score()` — régularité des sessions

### TASK-050 — Plan de session complet
- `_OBJECTIVES` (12 objectifs) + `_DURATION_BY_MASTERY`
- `_compute_priority_score()` — score de priorité par chunk
- Plan adaptatif complet avec durée estimée et objectifs associés

### TASK-051 — Métriques de rétention J+1/J+7/J+30
- `_RETENTION_WINDOWS` — fenêtres temporelles de rétention
- `compute_retention_metrics()` — fonction pure
- `get_retention_metrics()` — wrapper DB

### Correctifs inclus
- **BUG-1** : `get_topic_stats` — `AND score IS NOT NULL` manquant → NaN avg_score → crash `.astype(int)`
- **BUG-2** : `classify_mastery` — guard `if df.empty: return df` (pandas 2.x apply sur 0 colonnes)
- **BUG-3** : `_days_until` — `pd.NaT is None` = False → crash. Corrigé avec `pd.isna()` + try/except
- **11 tests anti-régression** ajoutés (`TestAntiRegressionPhase15`)

---

## Dernières TASKs réalisées (ordre chronologique)

1. TASK-048 : `build_session_plan` + `get_next_session_plan`
2. TASK-049 : `compute_momentum`, `compute_learning_velocity`, `compute_consistency_score`
3. TASK-050 : plan de session adaptatif complet
4. TASK-051 : métriques de rétention pédagogique J+1/J+7/J+30
5. Fix runtime : `_days_until` crash pandas 2.x NaT
6. Audit anti-régression Phase 15 : 2 bugs corrigés + 11 tests ajoutés

---

## Modules clés

| Fichier               | Rôle                                                          |
|-----------------------|---------------------------------------------------------------|
| `app.py`              | Point d'entrée Streamlit                                      |
| `database.py`         | SQLite, analytics, répétition espacée, wrappers DB           |
| `adaptive_engine.py`  | Moteur adaptatif pur (classify_mastery, plan, rétention)     |
| `ai_service.py`       | RAG, embeddings, LLM, types de questions, correction         |
| `rag_service.py`      | Pipeline RAG, recherche vectorielle                           |
| `document_service.py` | Ingestion, chunking, seed démo                               |
| `auth_service.py`     | Authentification utilisateurs                                 |
| `ui_helpers.py`       | Helpers UI (rapport, recommandations, formatage)             |
| `tabs/`               | Onglets Streamlit (trainer, dashboard, documents, history…)  |
| `test_regression.py`  | Suite de tests (168 tests)                                   |

---

## Architecture adaptive_engine.py (état snapshot)

```
classify_mastery, _adaptive_interval          — répétition espacée
_choose_question_type, explain_type_choice    — sélection type de question
compute_momentum                              — élan récent (7j)
compute_learning_velocity                     — vitesse d'apprentissage
compute_consistency_score                     — régularité sessions
_OBJECTIVES, _DURATION_BY_MASTERY            — plan de session
_compute_priority_score, build_session_plan   — plan adaptatif
_RETENTION_WINDOWS, compute_retention_metrics — métriques J+1/J+7/J+30
```

---

## Commandes de restauration

```bash
# 1. Décompresser le ZIP
unzip snapshot_phase14_stable_20260517_1907.zip -d addisco_restore/
cd addisco_restore/

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Vérifier la compilation
python -m py_compile app.py database.py adaptive_engine.py

# 5. Lancer les tests
python test_regression.py

# 6. Lancer l'application
streamlit run app.py
```

---

## Commandes minimales de lancement

```bash
# Démarrage rapide (env déjà configuré)
streamlit run app.py

# Tests uniquement
python test_regression.py

# Vérification syntaxe
python -m py_compile app.py database.py adaptive_engine.py ai_service.py auth_service.py ui_helpers.py
```

---

## Dépendances principales

| Package       | Usage                                      |
|---------------|--------------------------------------------|
| streamlit     | Interface web                              |
| openai        | LLM + embeddings                           |
| pandas        | DataFrames analytics                       |
| numpy         | Calculs vectoriels                         |
| sqlite3       | Base de données (stdlib Python)            |
| python-dotenv | Variables d'environnement (.env)           |

---

## Bases de données incluses

| Fichier        | Taille   | Contenu                               |
|----------------|----------|---------------------------------------|
| `database.db`  | ~116 KB  | Données principales (chunks, attempts)|
| `revision.db`  | 4 KB     | Données de révision                   |

---

## Remarques et points de vigilance

### Compatibilité pandas 2.x
- `pd.NaT is None` retourne `False` — toujours utiliser `pd.isna()` pour tester les valeurs nulles datetime.
- `df.apply(func, axis=1)` sur un DataFrame sans colonnes retourne un DataFrame, pas une Series.
- Guard obligatoire : `if df.empty: return df` avant tout `df.apply()`.

### Annotations de type
- Utiliser `Optional[str]` (from typing) jamais `str | None` (incompatible Streamlit 1.x + Python 3.9).

### Base SQLite
- Pas de DELETE + INSERT : utiliser UPDATE ciblé pour préserver les IDs stables.
- Les IDs `attempts.chunk_id` sont référencés par le système de mémoire pédagogique et répétition espacée.

---

## Points de vigilance Phase 15

Phase 15 prévue = **support multi-documents**.

Risques à surveiller :
1. **Isolation utilisateur** : chaque utilisateur doit voir uniquement ses chunks/attempts.
2. **Stabilité des IDs** : toute migration de schéma doit préserver les `chunk_id` existants.
3. **Performance** : avec plusieurs documents, les requêtes analytics peuvent ralentir — indexer si nécessaire.
4. **Fallback mode** : si les embeddings échouent sur un nouveau document, le fallback texte brut doit rester actif.
5. **Tests de régression** : les 168 tests actuels doivent tous passer après chaque modification de Phase 15.
6. **`adaptive_engine.py` est une fonction pure** : aucun import projet — cette contrainte doit être préservée.

---

*Snapshot généré automatiquement — ADDISCO OPS — Phase 14 complète*
