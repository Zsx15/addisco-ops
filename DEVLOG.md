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
- TASK-005 : variation pédagogique dans la génération de questions.

---

## 2026-05-12 — TASK-005 : Variation pédagogique dans la génération de questions

**Milestone :** Résoudre la répétition de questions identiques en introduisant 6 types de questions et une rotation par historique de chunk.

**Actions :**
- Ajout de `get_chunk_question_history(chunk_id, limit)` dans `database.py` : lit `pedagogy_type` comme `question_type` sur les dernières tentatives d'un chunk (colonne existante, aucune migration).
- Ajout dans `ai_service.py` : `import random`, `QUESTION_TYPES` (6 types), `_TYPE_PROMPTS` (dict clé→instruction LLM), `_choose_question_type(used_types)` (rotation équitable, aléatoire en cas d'égalité).
- Modification de `generate_question()` : lookup historique sur `chunk_ids[0]` après retrieval RAG, choix du type par rotation, prompt enrichi avec l'instruction du type + anti-doublon (2 dernières questions du chunk), retour `tuple[str, list[int], str]` (+question_type).
- Mise à jour `app.py` : session_state `question_type` initialisé, dépaquetage 3-tuple, `pedagogy_type=question_type` passé à `save_attempt()`.

**Types de questions implémentés :**
1. question_directe, 2. cas_pratique, 3. vrai_faux, 4. question_piege, 5. reformulation, 6. consequence

**Invariants préservés :**
- Fallback texte brut intact : si chunk_ids=[], type aléatoire, pas de lookup DB.
- Pipeline RAG inchangé. Embeddings inchangés.
- Aucune nouvelle dépendance (random = stdlib).
- Aucune migration SQLite (pedagogy_type existait déjà, était toujours NULL).
- `correct_answer()` non modifié.

**Validation :**
- `py_compile database.py / ai_service.py / app.py` → OK (3/3)
- `_choose_question_type([])` → type valide ✓
- `_choose_question_type(["question_directe"]*4)` → rotation correcte ✓
- `_choose_question_type([tous sauf consequence])` → consequence ✓
- `get_chunk_question_history(99999)` → [] ✓
- Streamlit headless port 8504 → démarrage sans erreur ✓

**Prochaine étape :**
- TASK-006 : répétition espacée légère.

---

## 2026-05-12 — TASK-006 : Répétition espacée légère

**Milestone :** Ajouter une dimension temporelle au moteur pédagogique — chaque chunk a désormais une date de prochaine révision calculée dynamiquement.

**Actions :**
- Ajout `from datetime import datetime, timedelta` dans `database.py`.
- Ajout constante `REVIEW_INTERVALS` (Fragile=1j, En consolidation=3j, Maîtrisé=7j) à la racine de `database.py` avec note de synchronisation avec le SQL.
- `get_chunk_stats()` : ajout `MAX(a.created_at) AS last_attempt_date` dans le SELECT.
- `classify_mastery(df)` : ajout de 3 colonnes calculées en Python pur : `next_review` (datetime), `days_until_review` (int), `review_status` (En retard / Aujourd'hui / Dans N jour(s) / —).
- `get_revision_suggestion()` : ORDER BY mis à jour — chunks en retard de révision priorisés via `datetime(MAX(created_at), '+N days') <= datetime('now')` en SQLite inline.
- `app.py` Dashboard "Analytics par chunk" : colonnes `Statut révision` et `Prochaine révision` ajoutées au tableau.
- `app.py` "Priorités de révision" : indicateur "⚠ Révision en retard" sur les lignes en retard.

**Règles de calcul :**
- next_review = last_attempt_date + REVIEW_INTERVALS[mastery_class]
- days_until_review = (next_review.date() - today).days
- Négatif = en retard, 0 = aujourd'hui, positif = dans N jours

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts. Fallback intact.
- Toutes les fonctions TASK-001 à TASK-005 non modifiées dans leur comportement.
- `classify_mastery()` retourne toujours `mastery_class` et `trend` (colonnes existantes inchangées).

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Tests helpers : Fragile 2j ago → En retard ✓ | Fragile 1j ago → Aujourd'hui ✓ | Consolidation 1j ago → Dans 2 jours ✓ | Consolidation 4j ago → En retard ✓ | Maîtrisé 6j ago → Dans 1 jour ✓ | last_attempt_date=None → pas de crash ✓
- Streamlit headless port 8505 → démarrage sans erreur ✓
- git status → 2 fichiers modifiés uniquement ✓

**Prochaine étape :**
- TASK-007 : contenu de démo préchargé, seed idempotente au démarrage.

---

## 2026-05-12 — TASK-007 : Contenu de démo préchargé

**Milestone :** L'application n'est plus vide au premier lancement — un document de démonstration SNCF est inséré automatiquement et de façon idempotente.

**Actions :**
- Ajout de `has_documents() -> bool` dans `database.py` : COUNT(*) sur documents, O(1).
- Ajout import `has_documents` dans `document_service.py`.
- Ajout de `_DEMO_TITLE`, `_DEMO_TEXT` (~3 200 chars, 4 sections : accueil, perturbations, PMR, traçabilité) et `seed_demo_document()` dans `document_service.py`.
- `seed_demo_document()` : guard `has_documents()` → idempotente, appel `ingest_document()` avec try/except non bloquant, embeddings tentés si API key présente sinon NULL.
- Ajout import `seed_demo_document` dans `app.py` + appel après `init_db()`.

**Contenu du document de démo :**
Procédure fictive "Accueil et orientation des voyageurs en gare" — 4 sections pédagogiquement riches activant les 6 types de questions (délais, priorités, conditions d'exclusion, traçabilité, PMR). 4 chunks créés au découpage.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts.
- Seed sans effet si un document existe déjà (idempotente).
- Startup non bloquant : si seed échoue → logger.warning, app démarre quand même.
- Toutes les fonctions TASK-001 à TASK-006 non modifiées.

**Validation :**
- `py_compile database.py / document_service.py / app.py` → OK (3/3)
- `has_documents()` base vide → False ✓
- `has_documents()` après seed → True ✓
- Idempotence (2 appels) → 1 document en base ✓
- Chunks créés → 4 ✓
- Streamlit headless port 8506 → démarrage sans erreur ✓
- git status → 3 fichiers code modifiés uniquement ✓

**Prochaine étape :**
- TASK-008 : dashboard reformaté pour utilisateur final (labels lisibles, masquage champs techniques).

---

## 2026-05-12 — TASK-008 : Dashboard reformaté pour utilisateur final

**Milestone :** Supprimer tous les termes techniques visibles par un utilisateur final lors d'une démonstration SNCF.

**Actions :**
- `database.py` : remplacement de `'Chunk #' || c.chunk_index` par `'Section ' || (c.chunk_index + 1)` dans `get_chunk_stats()` et `get_revision_suggestion()`. Les sections s'affichent désormais "Section 1", "Section 2"… (1-indexé).
- `app.py` : ajout de `active_document_title` dans les clés session_state initialisées.
- `app.py` : `_make_use_callback` reçoit un paramètre `doc_title` et le stocke dans `active_document_title`.
- `app.py` Entraînement : caption `"Source : document importé (ID X)"` → `"Source : {titre du document}"`.
- `app.py` Dashboard : titre `"Analytics par chunk"` → `"Progression par section"`.
- `app.py` Documents — label expander : `"chunk"` → `"section"`.
- `app.py` Documents — métrique : `"Chunks"` → `"Sections"`.
- `app.py` Documents — bouton reindex : `"chunk(s) manquant(s)"` → `"section(s) manquante(s)"`.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance.
- Clé `section_label` inchangée dans les dicts retournés — seule la valeur change.
- RAG intact. Embeddings intacts. Fallback intact.
- Toutes les fonctions TASK-001 à TASK-007 non modifiées dans leur comportement.

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Streamlit headless port 8507 → démarrage sans erreur

**Prochaine étape :**
- TASK-009 : détection automatique de section_title dans le chunker.

---

## 2026-05-12 — TASK-009 : Détection automatique de section_title dans le chunker

**Milestone :** Peupler la colonne `section_title` des chunks pour les documents ayant une structure numérotée ou markdown, sans migration SQLite ni nouvelle dépendance.

**Actions :**
- Ajout de la constante `_SECTION_RE` dans `document_service.py` : regex détectant les titres numérotés (`1. Titre`, `2) Titre`) et markdown (`## Titre`), avec limite de 120 chars anti-faux-positifs.
- Ajout du helper `_detect_section_title(para) -> str | None` : pure function, retourne le paragraphe s'il est un titre, None sinon.
- Modification de `_create_chunks()` : ajout de `current_section: str | None = None` ; `flush()` utilise `current_section` comme `section_title` ; boucle principale détecte les titres (flush + reset overlap + nouveau buffer) ; chemin hard-split hérite aussi de `current_section`.

**Comportement :**
- Document avec sections numérotées → `section_title` peuplé, titre inclus dans le chunk pour la qualité RAG.
- Document sans structure → `section_title = None` pour tous les chunks, fallback "Section N+1" inchangé (aucune régression).
- Chemin hard-split (paragraphe > 1000 chars) → hérite du `current_section` actif.

**Non fait intentionnellement :**
- Pas de réinitialisation de la base → chunks existants (dont le document de démo) conservent `section_title=NULL`. Seuls les nouveaux imports bénéficieront des vrais titres.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts. Fallback intact.
- `ingest_document()`, `reindex_document()`, pipeline complet non modifiés.

**Validation :**
- `py_compile document_service.py` → OK
- 8/8 tests OK : détection numérotée, markdown, trop long, paragraphe ordinaire, sections peuplées, sans structure, 4 sections démo, hard-split.
- Streamlit headless port 8508 → démarrage sans erreur.
- git status → 1 fichier code modifié uniquement.

**Prochaine étape :**
- TASK-010 : guide de démo + README utilisateur.

---

## 2026-05-12 — TASK-010 : Guide de démo + README utilisateur

**Milestone :** Rendre le projet présentable à un jury SNCF et installable par un tiers sans accompagnement.

**Actions :**
- `README.md` réécrit intégralement : description réelle du projet, prérequis, installation, configuration API key + fallback explicité, lancement, architecture réelle (5 fichiers), stack technique, commande de réinitialisation de la base.
- `DEMO.md` créé : scénario 7 étapes ordonnées (Documents → Entraînement → correction → Dashboard → suggestion → boucle fermée → fallback optionnel), actions claires + script de parole jury, tableau récapitulatif des points clés, conseil de préparation préalable.

**Invariants préservés :**
- Aucune modification de code. Aucun changement de schéma. Pipeline intact.

**Prochaine étape :**
- À définir selon priorités : reset démo avec vrais titres de section, amélioration RAG, ou nouvelle fonctionnalité pédagogique.

---
