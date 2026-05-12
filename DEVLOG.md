# DEVLOG — AI Révision Métier

Journal de développement chronologique du projet.

Format par entrée :
- Date
- Tâche / milestone
- Actions réalisées
- Décisions prises
- Problèmes rencontrés
- Prochaine étape

---

## 2026-05-12 — Intégration App Factory

**Milestone :** Fusion organisationnelle App Factory + AI-V2.

**Actions :**
- Ajout de `task.mjs` (App Factory v2.2) à la racine.
- Ajout de `taskrc.schema.json` à la racine.
- Création de `.taskrc.json` adapté Python/Streamlit (py_compile comme review minimale).
- Création de `DEVLOG.md` (ce fichier).
- Ajout section "APP FACTORY + DEVLOG POLICY" dans `CLAUDE.md`.

**Décisions :**
- Stack de review minimaliste : `py_compile` uniquement (pas de mypy/ruff — non installés).
- Aucune modification du code métier existant.
- App Factory sert uniquement de couche de pilotage, pas de refonte.

**Invariants préservés :**
- `app.py`, `ai_service.py`, `database.py`, `document_service.py` non modifiés.
- Pipeline RAG inchangé.
- Structure SQLite inchangée.
- Fallback texte brut inchangé.

**Prochaine étape :**
- Continuer sur les priorités existantes : tracking pédagogique, stabilisation RAG.

---

## 2026-05-12 — TASK-002 : Analytics pédagogiques par chunk

**Milestone :** Exploitation de `attempts.chunk_id` (TASK-001) pour produire des analytics de progression par chunk source.

**Actions :**
- Ajout de `get_chunk_stats()` dans `database.py` : requête SQL joingnant `attempts → chunks → documents`, filtrée sur `chunk_id IS NOT NULL`, groupée par chunk, avec sous-requête corrélée pour l'erreur dominante.
- Ajout d'une section "Analytics par chunk" dans l'onglet Dashboard de `app.py` : tableau `st.dataframe` (Document, Section, Score moyen, Tentatives, Niveau, Erreur dominante) + liste des chunks fragiles (< 60 %).
- Import de `get_chunk_stats` dans `app.py`.

**Décisions :**
- Pas de graphique pour l'instant (scope validé) : tableau uniquement.
- Pas de filtre par document pour l'instant.
- Fallback `COALESCE(section_title, 'Chunk #' || chunk_index)` : aucune dépendance à `section_title`.
- Les 4 sections Dashboard existantes sont intactes.
- Section conditionnelle : si aucune tentative RAG, un message d'info s'affiche sans crash.

**Invariants préservés :**
- `ai_service.py` non modifié.
- `document_service.py` non modifié.
- Pipeline RAG inchangé.
- Système embeddings inchangé.
- Fallback texte brut inchangé.
- Schéma SQLite inchangé (aucune migration).

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- `git status` → 2 fichiers modifiés uniquement.

**Prochaine étape :**
- TASK-003 : score de maîtrise par chunk (classification Fragile / En consolidation / Maîtrisé + tendance).

---

## 2026-05-12 — TASK-003 : Score de maîtrise par chunk

**Milestone :** Transformation des analytics bruts (TASK-002) en indicateur pédagogique exploitable.

**Actions :**
- Ajout d'une sous-requête corrélée `last_score` dans `get_chunk_stats()` (database.py) : dernière tentative scorée par chunk, triée par `created_at DESC`.
- Ajout de `classify_mastery(df)` dans `database.py` : helper Python pur enrichissant le DataFrame avec `mastery_class` (Fragile / En consolidation / Maîtrisé) et `trend` (Amélioration / Stable / Dégradation / N/A).
- Remplacement de la section "Analytics par chunk" dans `app.py` : tableau enrichi (Maîtrise + Tendance) + liste de révision prioritaire (Fragile → En consolidation → caption Maîtrisé).
- Import de `classify_mastery` dans `app.py`.

**Règles de classification :**
- Maîtrisé : avg_score ≥ 0.8 ET attempts_count ≥ 3
- Fragile : avg_score < 0.6 (quel que soit le nombre de tentatives)
- En consolidation : tout le reste

**Règles de tendance :**
- N/A si une seule tentative
- Amélioration : last_score > avg_score + 0.1
- Dégradation : last_score < avg_score − 0.1
- Stable : écart ≤ 0.1

**Invariants préservés :**
- `ai_service.py`, `document_service.py` non modifiés.
- Pipeline RAG inchangé. Embeddings inchangés. Fallback inchangé.
- Schéma SQLite inchangé (aucune migration).
- Les 4 sections Dashboard existantes intactes.

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Streamlit headless port 8502 → démarrage sans erreur
- `git status` → 2 fichiers modifiés uniquement

**Prochaine étape :**
- TASK-004 : suggestion de révision dans l'onglet Entraînement (fermeture de la boucle pédagogique).

---

## 2026-05-12 — TASK-004 : Suggestion de révision dans l'onglet Entraînement

**Milestone :** Fermeture de la boucle pédagogique — passer de l'observation (Dashboard) à l'action directe (Entraînement).

**Actions :**
- Ajout de `get_revision_suggestion()` dans `database.py` : requête SQL autonome, JOIN attempts→chunks→documents, HAVING exclut les chunks Maîtrisés, ORDER BY priorité Fragile → ancienneté → score faible, LIMIT 1, retourne dict ou None.
- Ajout de `from datetime import datetime` dans `app.py`.
- Ajout de `get_revision_suggestion` dans les imports database de `app.py`.
- Ajout du bloc "Révision suggérée" dans l'onglet Entraînement (avant la zone de texte) : section, document, score, tentatives, ancienneté, bouton "Réviser ce chunk →" via `_make_use_callback`.

**Règles de priorité :**
1. Fragile (avg_score < 0.6) avant En consolidation
2. Tentative la plus ancienne (MAX(created_at) ASC)
3. Score le plus faible (AVG(score) ASC)

**Invariants préservés :**
- Bloc conditionnel : absent si aucun chunk éligible (aucune tentative RAG ou tout maîtrisé).
- `ai_service.py`, `document_service.py` non modifiés.
- Pipeline RAG, embeddings, fallback inchangés.
- Schéma SQLite inchangé.
- Onglet Entraînement existant intact sous le bloc.

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Streamlit headless port 8503 → démarrage sans erreur
- `git status` → 2 fichiers modifiés uniquement

**Prochaine étape :**
- TASK-005 : mémoire pédagogique persistée (error_patterns, notions fragiles, répétition espacée).

---
