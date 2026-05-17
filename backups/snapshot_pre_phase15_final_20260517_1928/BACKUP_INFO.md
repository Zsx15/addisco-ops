# BACKUP_INFO — Snapshot Final Pré-Phase 15

## Identification

| Champ              | Valeur                                          |
|--------------------|--------------------------------------------------|
| Date               | 2026-05-17                                       |
| Heure              | 19:28                                            |
| Commit Git (short) | `36306ca`                                        |
| Commit Git (full)  | `36306caec78b3ec57973f5a4e63757fd5da9e341`       |
| Branche            | `main`                                           |
| Tests validés      | **168 tests — 0 régression**                    |
| Statut             | Phase 14 complète — Audit UX intégré — Pré-Phase 15 |

---

## Résumé des corrections incluses depuis Phase 14

### TASK-051 — Métriques de rétention pédagogique J+1/J+7/J+30
- `_RETENTION_WINDOWS`, `compute_retention_metrics()`, `get_retention_metrics()`

### Corrections anti-régression Pandas / SQLite
- `_days_until()` : guard `pd.isna()` contre crash NaT pandas 2.x
- `get_topic_stats()` : `AND score IS NOT NULL` — empêche avg_score NaN → crash astype(int)
- `classify_mastery()` : `if df.empty: return df` — guard DataFrame vide

### Audit UX pré-Phase 15 (commit 36306ca)
- **UX-01 (CRITIQUE)** : Logout nettoie toutes les clés pédagogiques — empêche la fuite de session entre utilisateurs
- **UX-02 (SÉRIEUX)** : `answer_input` effacé à la génération d'une nouvelle question
- **UX-03 (MODÉRÉ)** : État vide "Pas encore de données d'évolution" sur le graphe scores
- **UX-04 (MODÉRÉ)** : Spinner sur "Calculer le profil" — feedback visuel pendant le calcul

### Suite de tests renforcée
- 11 tests anti-régression Phase 15 (`TestAntiRegressionPhase15`)
- Tests NaT pandas 2.x, DataFrame vide, isolation utilisateur, retention metrics
- Total : 168 tests

---

## Commits récents importants

```
36306ca fix: audit UX pré-Phase 15 — 4 corrections (UX-01 à UX-04)
82c8b55 chore: snapshot Phase 14 stable — backup restaurable pré-Phase 15
0169d9c fix: audit anti-régression Phase 15 — 2 bugs + 11 tests
eaf6e07 fix: classify_mastery — _days_until crash pandas 2.x NaT
e18680e qa: TASK-051 Conseil — guard int(chunk_id) + test correspondant
b6d4248 feat: TASK-051 — métriques de rétention pédagogique J+1/J+7/J+30
```

---

## Modules principaux inclus

| Fichier               | Rôle                                                          |
|-----------------------|---------------------------------------------------------------|
| `app.py`              | Point d'entrée Streamlit — auth, routing, sidebar            |
| `database.py`         | SQLite, analytics, répétition espacée, wrappers DB           |
| `adaptive_engine.py`  | Moteur adaptatif pur (classify_mastery, plan, rétention)     |
| `ai_service.py`       | RAG, embeddings, LLM, types de questions, correction         |
| `rag_service.py`      | Pipeline RAG, recherche vectorielle cosinus                  |
| `document_service.py` | Ingestion, chunking, seed démo                               |
| `auth_service.py`     | Authentification, rôles (apprenant/formateur/admin)         |
| `ui_helpers.py`       | Helpers UI, rapport, recommandations, explainability         |
| `tabs/`               | Onglets Streamlit (trainer, dashboard, documents, history…)  |
| `test_regression.py`  | Suite de 168 tests                                           |
| `seed_demo_attempts.py` | Seed données démo                                          |
| `logger.py`           | Configuration logging                                        |

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

**Contrainte architecturale critique** : `adaptive_engine.py` est une fonction pure — zéro import projet. Cette contrainte DOIT être préservée en Phase 15.

---

## Bases de données incluses

| Fichier        | Taille   | Copie via          |
|----------------|----------|--------------------|
| `database.db`  | ~116 KB  | `sqlite3.backup()` |
| `revision.db`  | 4 KB     | `sqlite3.backup()` |

---

## Commandes de restauration

```bash
# 1. Décompresser
unzip snapshot_pre_phase15_final_20260517_1928.zip -d addisco_restore/
cd addisco_restore/

# 2. Environnement virtuel
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Dépendances
pip install -r requirements.txt

# 4. Vérification syntaxe
python -m py_compile app.py database.py adaptive_engine.py ai_service.py auth_service.py ui_helpers.py

# 5. Tests
python test_regression.py

# 6. Lancement
streamlit run app.py
```

---

## Commandes minimales de lancement

```bash
streamlit run app.py          # démarrage application
python test_regression.py     # validation 168 tests
```

---

## Dépendances principales

| Package       | Usage                              |
|---------------|------------------------------------|
| streamlit     | Interface web                      |
| openai        | LLM + embeddings                   |
| pandas        | DataFrames analytics               |
| numpy         | Calculs vectoriels (embeddings)    |
| plotly        | Graphiques dashboard               |
| sqlite3       | Base de données (stdlib Python)    |
| python-dotenv | Variables d'environnement (.env)   |

---

## Points de vigilance Phase 15 (multi-documents)

### Technique
1. **`adaptive_engine.py` = module pur** — aucun import projet, contrainte à préserver absolument.
2. **Stabilité des IDs** — toute migration de schéma doit préserver `attempts.chunk_id` et `chunks.id`. Pas de DELETE + INSERT.
3. **Guard `if df.empty: return df`** dans `classify_mastery()` — ne pas retirer.
4. **`pd.isna()` obligatoire** pour tester les valeurs nulles datetime (pandas 2.x).
5. **`Optional[str]`** (from typing) — ne jamais utiliser `str | None` (incompatible Streamlit 1.x + Python 3.9).

### Session state
6. **UX-01 résolu** — le logout nettoie toutes les clés pédagogiques. En Phase 15, tout nouveau state pédagogique doit être ajouté à la liste de nettoyage dans `app.py`.
7. **Isolation utilisateur** — les nouveaux endpoints DB Phase 15 doivent filtrer par `user_id`.

### Tests
8. **168 tests doivent tous passer après chaque modification Phase 15** — zéro régression acceptable.
9. **Tests d'isolation utilisateur** (`TestAntiRegressionPhase15.test_user_isolation_full_pipeline`) — critiques pour Phase 15 multi-documents.

### Fallback
10. **Si les embeddings échouent sur un nouveau document**, le mode texte brut doit rester actif — `fallback_mode` dans `ai_service.py`.

---

## Observations UX documentées (non corrigées — design)

- **UX-05** : Demo mode voit tous les onglets — intentionnel pour la démo.
- **UX-06** : Mini-timeline newest→oldest (L→R) — cosmétique.
- **UX-07** : Messages d'erreur API bruts — acceptable MVP.
- **UX-09** : Tab "Formateur" = vue self, pas superviseur multi-apprenants — design documenté.

---

*Snapshot généré automatiquement — ADDISCO OPS — Phase 14 complète + Audit UX — Pré-Phase 15*
