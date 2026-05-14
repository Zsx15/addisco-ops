# DEVLOG — AI Révision Métier

Journal de développement chronologique du projet.

---

## 2026-05-14 — TASK-019 : Filtrage user_id — fondation multi-utilisateur

**Milestone :** Préparation multi-utilisateur minimale (Phase 10).

**Actions :**
- Ajout paramètre `user_id: str = "default"` sur 8 fonctions dans `database.py` : `save_attempt`, `get_attempts`, `get_score_evolution`, `get_error_frequency`, `get_topic_stats`, `get_chunk_stats`, `get_chunk_mastery`, `get_revision_suggestion`.
- Toutes les requêtes SQL filtrées par `AND user_id = ?`. Sous-requêtes corrélées dans `get_chunk_stats()` également filtrées.
- `app.py` : init `session_state["user_id"] = "default"` + `st.sidebar.text_input(key="user_id")`.
- 10 points d'appel dans `app.py` mis à jour.
- `get_chunk_question_history` inchangée (appelée depuis `ai_service.py` — moteur protégé).

**Décisions :**
- `user_id="default"` comme valeur par défaut : rétrocompatibilité totale, aucune migration de données nécessaire.
- Sidebar text_input : testable sans authentication, non intrusif dans le flux principal.
- Moteur `ai_service.py` non touché : la question history reste cross-user pour l'instant (rotation chunk).

**Invariants préservés :**
- `ai_service.py`, `document_service.py` non modifiés.
- Fallback texte brut inchangé.
- Pipeline RAG inchangé.
- py_compile 2/2 OK. AST check 10/10 call sites OK.

**Prochaine étape :**
- TASK-020 : Table `user_learning_profile` (migration douce, `database.py` uniquement).

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

## 2026-05-12 — TASK-011 : Adaptation pédagogique par niveau de maîtrise

**Milestone :** Le moteur de questions adapte le type pédagogique au niveau de maîtrise de la section, pas seulement à l'historique de rotation.

**Actions :**
- Ajout de `get_chunk_mastery(chunk_id) -> str | None` dans `database.py` : requête `AVG(score), COUNT(*)` ciblée, retourne Fragile / En consolidation / Maîtrisé ou None. Mêmes règles que `classify_mastery()`.
- Ajout de `_MASTERY_BIAS` dans `ai_service.py` : dict Fragile → [reformulation, consequence, cas_pratique] / Maîtrisé → [question_piege, cas_pratique, consequence].
- Modification de `_choose_question_type(used_types, mastery_class=None)` : le biais est appliqué sur les candidats équitables (intersection). Si le biais ne recoupe aucun candidat équitable, rotation standard — aucune régression possible.
- Modification de `generate_question()` : lookup `get_chunk_mastery(chunk_ids[0])` après retrieval RAG, passé à `_choose_question_type`. Protégé par try/except — non bloquant.
- Import de `get_chunk_mastery` ajouté dans `ai_service.py`.

**Comportement sur la démo :**
- Section Posture (Fragile) : reformulation, consequence, cas_pratique favorisés.
- Sections Perturbations / PMR (En consolidation) : rotation équitable inchangée.
- Section Traçabilité (Maîtrisé) : question_piege, cas_pratique, consequence favorisés.
- Fallback texte brut (chunk_ids=[]) : mastery=None → rotation équitable inchangée.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts. Fallback intact.
- Signature de `generate_question()` inchangée (tuple[str, list[int], str]).
- `correct_answer()` non modifié. `app.py` non modifié.

**Validation :**
- `py_compile database.py / ai_service.py` → OK
- 9/9 tests OK : biais Fragile/Maîtrisé, saturation → fallback, En consolidation libre, get_chunk_mastery (None / Fragile / Maîtrisé).
- Streamlit headless port 8511 → démarrage sans erreur.
- git status → 2 fichiers code modifiés uniquement.

**Prochaine étape :**
- À définir.

---

## 2026-05-12 — TASK-012 : Sélecteur de document inline dans l'onglet Entraînement

**Milestone :** FRONTEND/UX — éliminer la navigation entre onglets pour sélectionner un document.

**Actions :**
- Ajout d'un `st.selectbox` "Document de travail" dans l'onglet Entraînement, avant la zone de texte source. Options : "— Texte libre (sans RAG)" + liste des documents importés.
- Sur changement de sélection : charge `cleaned_text` + met à jour `active_document_id`, `active_document_title`, `source_text_input` en session_state, réinitialise question et résultat, appelle `st.rerun()`.
- Le sélecteur se pré-positionne sur le document actif (lecture de `active_document_id`). Si le document actif est changé via la suggestion de révision (`_make_use_callback`), le sélecteur se resynchronise au prochain rerun.
- Correction du libellé `"Réviser ce chunk →"` → `"Réviser cette section →"` (oubli TASK-008).

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Aucune modification du moteur critique. RAG, embeddings, scoring, répétition espacée intacts.
- Onglet Documents inchangé. `_make_use_callback` inchangé.
- Si aucun document en base : sélecteur masqué, comportement identique à l'existant.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8512 → démarrage sans erreur.
- git status → 1 fichier modifié uniquement.

**Prochaine étape :**
- À définir.

---

## 2026-05-12 — TASK-013 : Export du rapport de progression

**Milestone :** FRONTEND/UX — générer et télécharger un rapport texte structuré depuis le Dashboard.

**Actions :**
- Ajout de `_build_report(df_all, df_topics, df_chunks) -> str` dans `app.py` : rapport texte brut 60 colonnes avec synthèse globale, maîtrise par section et priorités de révision.
- Ajout d'un `st.download_button` à la fin du bloc Dashboard (df_chunks non vide) : génère `rapport_progression_YYYYMMDD.txt` encodé UTF-8.
- Correction `"Tous les chunks sont maîtrisés"` → `"Toutes les sections sont maîtrisées"`.
- Correction caption `"chunk maîtrisé"` → `"section maîtrisée"` (accord féminin).
- Format choisi : texte brut structuré (robustesse, zéro dépendance, compatibilité maximale).

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Aucune modification du moteur critique. RAG, embeddings, scoring, répétition espacée intacts.
- `_build_report()` est un formateur de présentation pur — aucun accès DB direct.
- Bouton visible seulement si df_chunks non vide (données RAG disponibles).

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8509 → démarrage sans erreur (HTTP 200).

**Prochaine étape :**
- À définir.

---

## 2026-05-12 — TASK-014 : Dashboard pédagogique visuel moderne

**Milestone :** FRONTEND/UX — refonte visuelle complète du Dashboard pour démonstration jury.

**Actions :**
- Ajout `import pandas as pd` (nécessaire pour `pd.concat` dans les cartes section).
- Zone 1 — KPIs enrichis : remplacement "Meilleure notion / Notion fragile" par "Sections maîtrisées X/N" et "Révisions en retard N".
- Zone 2 — Card révision prioritaire : `st.container(border=True)` mettant en avant la section la plus urgente (Fragile → En consolidation), immédiatement visible en haut du Dashboard.
- Zone 3 — Cartes de section : remplacement du dataframe 9 colonnes + liste st.error/warning par des cartes visuelles avec badge couleur (🔴/🟡/🟢), `st.progress()` (barre de score), tentatives et statut révision.
- Zone 4 — Graphiques conservés : évolution des scores, score par notion, types d'erreurs. Supprimés : "Notions fragiles" (redondant) et "Tentatives par notion" (faible valeur).
- Zone 5 — Bloc IA adaptative : `st.info()` texte fixe explicitant le mécanisme de biais pédagogique au jury.
- Zone 6 — Export : bouton de téléchargement conservé.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Aucune modification du moteur critique. Aucune nouvelle requête DB. Données réutilisées depuis `df_all`, `df_topics`, `df_chunks`.
- `classify_mastery()` déplacée avant les métriques (reorder, pas de changement logique).

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8511 → démarrage sans erreur (HTTP 200).

**Prochaine étape :**
- À définir.

---

## 2026-05-13 — TASK-015 : Mode démo guidée / Storytelling produit

**Milestone :** FRONTEND/UX — transformer le MVP technique en démonstration produit convaincante pour un décideur non-tech.

**Actions :**
- Import de `get_chunk_mastery` dans `app.py` (lecture seule, moteur inchangé).
- Header HTML : titre + tagline + banner 7 pills pipeline (Document → RAG → Question → Réponse → Correction → Mémoire → Révision prioritaire).
- Ajout de `question_mastery` dans session_state initialisé.
- 5ème onglet `tab_engine` "Moteur IA".
- Dicts `_TYPE_EXPLANATIONS` (6 types → explication pédagogique) et `_MASTERY_BIAS_LABELS` (3 niveaux → label lisible).
- Expander "Pourquoi cette question ?" dans l'onglet Entraînement : type, explication pédagogique, biais de maîtrise.
- Caption mémoire post-correction : rappel du biais actif.
- Explication "Pourquoi prioritaire ?" dans la card prioritaire du Dashboard.
- Onglet Moteur IA : pipeline 7 étapes, 6 types de questions, répétition espacée, adaptation cognitive.
- Lookup `get_chunk_mastery(chunk_ids[0])` au moment de la génération de question.

**Fichiers modifiés :** `app.py` uniquement. `ai_service.py`, `database.py`, `document_service.py` non modifiés.

**Invariants préservés :**
- Moteur critique intact. Fallback texte brut intact. Pipeline RAG intact.
- `get_chunk_mastery` déjà présent dans `database.py` (TASK-011) — aucune modification.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8515 → OK

**Commit :** `479d0c0`

---

## 2026-05-13 — TASK-016 : UX Premium / Densification visuelle / Finition produit

**Milestone :** FRONTEND/UX — éliminer la sensation prototype Streamlit brut, poser les bases d'un dashboard IA métier premium.

**Actions :**
- CSS global injecté après `st.set_page_config` : padding `block-container` 1rem, `hr` fins `#e2e8f0`, alerts compacts, tabs `font-weight 600`, metric labels `text-transform uppercase font-size 11px`, containers `border-radius 8px`, captions `font-size 12px`.
- Header HTML refait : titre bold-900 + tagline + 7 pipeline pills avec séparateurs `›`.
- Helper `_kpi_card(icon, label, value, accent) -> str` : fond `#f8fafc`, border, radius 10px, icône 22px, valeur 26px bold-800, label 11px uppercase.
- Dashboard KPI : 4 `_kpi_card()` en colonnes avec accents couleur (vert maîtrise, rouge retard).
- Onglet Moteur IA : pipeline en grille HTML 2 colonnes (7 étapes), 6 types en grille 3 colonnes, répétition espacée + adaptation cognitive en 2 colonnes `st.columns`.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Moteur critique intact. Session state intact. Toute logique existante conservée.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8525 → OK

**Commit :** `dd70b0b`

---

## 2026-05-13 — TASK-017 : Branding premium / Identité produit / Profondeur visuelle — SYNPZ OPS

**Milestone :** BRANDING — faire passer SYNPZ OPS du registre bon MVP Streamlit à véritable produit IA métier identifiable.

**Actions :**
- `page_title` → "SYNPZ OPS", `page_icon` → 🧠.
- CSS enrichi : `.stApp {background-color:#f5f6fa}`, cards `box-shadow 0 1px 3px rgba(0,0,0,.08)`, expanders `border #e2e8f0 background #fff`, bloc info `border-left 3px solid #4f46e5`.
- Header HTML reconstruit : barre accent indigo `4px #4f46e5` à gauche, "SYNPZ OPS" bold-800 36px, badge "Adaptive Learning Intelligence" fond `#eef2ff` texte `#4f46e5`, pills pipeline blanches ombragées, dernière pill fond `#4f46e5` texte blanc.
- `_kpi_card()` upgradé : fond blanc, `box-shadow 0 2px 8px rgba(0,0,0,.07)`, valeur 30px letter-spacing `.02em`, label 10px spacing `.08em`.
- Dashboard : subheader styled HTML uppercase tracking, titres sections 12px uppercase.
- Graphiques compactés : line chart 210px, bar charts `max(200, n*44)`.
- Palette cohérente : `#16a34a` vert, `#d97706` orange, `#dc2626` rouge, `#6366f1` violet erreurs.
- Zone analyse moteur condensée en 1 ligne `st.caption`.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Moteur critique intact. Aucune nouvelle dépendance. Fallback intact.

**Décision :** Nom produit "SYNPZ OPS" adopté définitivement. Palette indigo `#4f46e5` comme accent primaire.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8535 → OK

**Commit :** `5baef8e`

---

## 2026-05-13 — TASK-018 : Intelligence pédagogique adaptative / Expérience utilisateur cognitive — SYNPZ OPS

**Milestone :** FRONTEND/UX — rendre l'intelligence du moteur adaptative explicite et lisible dans chaque zone de l'interface.

**Actions :**
- `_mastery_state(row) -> tuple[str, str, str]` : 8 états dynamiques combinant `mastery_class` + `trend` + `days_until_review`. Retourne (icône, label, couleur) pour chaque chunk. Exemple : "Maîtrisé + Amélioration" → 🏆 vert foncé ; "Fragile + Dégradation + retard" → 🔥 rouge.
- `_build_recommendations(df_chunks, df_errors) -> list[tuple[str,str]]` : moteur de recommandations, max 5 items, 4 types (urgent/warning/success/info) selon : chunks en retard, chunks Fragile, erreur dominante, performance globale, sections maîtrisées.
- `df_errors = get_error_frequency()` remonté en tête de bloc Dashboard (avant les métriques) pour alimenter les recommandations.
- Expander "Pourquoi cette question ?" enrichi : trend (📈/📉/—), review_status (⏰ si retard, 📅 sinon), dominant_error (🔍 si présent).
- Dashboard restructuré : KPI → recommandations → priority card → section cards avec `_mastery_state()` + erreur dominante → évolution scores → analytics 2-col → mini-timeline → analyse dynamique → export.
- Mini-timeline : 8 derniers `attempts` (score desc created_at) affichés comme pills colorées (vert ≥0.8, orange ≥0.6, rouge <0.6) + label "N%" en HTML inline.
- Analyse pédagogique dynamique : 4 profils (excellent ≥0.8 avg, consolidation ≥0.6, fragile <0.6 avec historique, démarrage sans données) → texte adaptatif dans `st.info`.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur). Correction du doublon `df_errors` (assignation redondante supprimée dans Zone 4c).

**Invariants préservés :**
- Moteur critique (`database.py`, `ai_service.py`, `document_service.py`) non modifié.
- Toutes les données exploitées via `classify_mastery()` existant — aucune nouvelle requête DB.
- Fallback intact. Pipeline RAG intact. Session state intact.

**Validation :**
- `py_compile app.py` → OK
- Streamlit → OK

**Commit :** `4cd3868`

**Prochaine étape :**
- À définir selon priorités.

---
