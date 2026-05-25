# ADDISCO OPS — Document de Référence Complet
### Pour le néophyte, l'expert SI, le RH, et moi-même

> Version : Phase 20 complète — 2026-05-25
> Auteur du projet : Guilhem Marcelino
> Stack : Python · Streamlit · SQLite · OpenAI · Railway

---

# PARTIE 1 — C'EST QUOI ADDISCO OPS ?

## Explication pour quelqu'un qui ne connaît rien à l'informatique

Imagine que tu travailles dans une entreprise et que tu dois apprendre un nouveau logiciel, une nouvelle procédure, ou un nouveau règlement interne.
Normalement tu reçois un PDF de 80 pages et tu te débrouilles.

**ADDISCO OPS fait exactement l'inverse.**

Tu charges ton document dans l'application. Elle le lit, le comprend, et te pose des questions dessus — comme un professeur qui t'interroge. Elle corrige tes réponses, note tes erreurs, et te repose les questions sur lesquelles tu te plantes, plus souvent et de façon différente, jusqu'à ce que tu aies vraiment retenu l'information.

Ce n'est pas un quiz statique. Le système s'adapte à toi : si tu bloques sur un concept, il change sa façon de te l'expliquer. Si tu maîtrises une notion, il passe à la suivante et revient vérifier plus tard que tu n'as pas oublié.

**En une phrase :** ADDISCO OPS transforme n'importe quel document professionnel en un coach d'apprentissage intelligent et personnalisé.

---

## Explication pour quelqu'un qui comprend l'informatique

ADDISCO OPS est une application web SaaS pédagogique B2B construite autour de trois piliers techniques :

**1. RAG (Retrieval-Augmented Generation)**
Le document est découpé en fragments (chunks), chaque fragment est converti en vecteur sémantique (embedding 1 536 dimensions via OpenAI `text-embedding-3-small`). À la génération d'une question, la requête est également vectorisée, et les fragments les plus proches sémantiquement sont récupérés (cosinus, top-K) pour servir de contexte au LLM (`gpt-4o-mini`).

**2. Moteur adaptatif à mémoire longue**
Chaque réponse est tracée avec son type d'erreur, son chunk source, son type pédagogique, et son score. Le moteur calcule en temps réel : niveau de maîtrise par chunk, intervalles de révision espacée, profil pédagogique utilisateur, momentum et vélocité d'apprentissage. Les décisions du moteur sont entièrement déterministes et auditables.

**3. Infrastructure production-ready**
Authentification bcrypt, gestion des rôles (apprenant / formateur / admin), SQLite en local / PostgreSQL-ready, déployé sur Railway, CI/CD GitHub Actions, monitoring Sentry, rate limiting per-user, 262 tests automatisés, score d'audit global 99/100.

---

# PARTIE 2 — ARCHITECTURE DÉTAILLÉE

## Vue schématique globale

```
UTILISATEUR (navigateur web)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                     app.py                          │
│   Point d'entrée Streamlit — Routeur principal      │
│   Auth → Session → Navigation → Onglets             │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┼─────────────────────┐
    ▼            ▼                     ▼
 tabs/        services/            engine/
 ─────        ─────────            ───────
 Interface    Logique métier       Cerveau adaptatif
 utilisateur  et données           (pur, sans DB)
```

---

## CHAQUE DOSSIER ET FICHIER — POURQUOI IL EST LÀ

---

### `app.py` — Le chef d'orchestre

**Pour le néophyte :** C'est la porte d'entrée de l'application. Il gère la connexion, décide ce que tu vois selon ton rôle, et distribue le travail aux autres fichiers.

**Pour l'expert :** Routeur Streamlit < 150 lignes. Gère `session_state`, l'authentification, et dispatche vers les onglets. Contient la liste de nettoyage complète au logout (règle UX-01) pour éviter les fuites de state entre sessions.

**Pourquoi là et pas ailleurs :** Centraliser le routing dans un seul fichier maintient le reste modulaire. Si une feature d'UI change, `app.py` est l'unique point à modifier.

---

### `tabs/` — L'interface utilisateur (6 onglets)

**Pour le néophyte :** Chaque fichier correspond à un onglet visible dans l'application.

| Fichier | Ce que l'utilisateur voit |
|---|---|
| `tab_training.py` | L'onglet d'entraînement — les questions, les réponses, le feedback |
| `tab_dashboard.py` | Ton tableau de bord personnel — scores, progression, profil |
| `tab_documents.py` | Upload et gestion des documents |
| `tab_history.py` | L'historique de toutes tes tentatives |
| `tab_admin.py` | La gestion des utilisateurs (admin uniquement) |
| `tab_engine.py` | Le moteur pédagogique visible — parcours, compétences, graphe Bloom connecté aux données réelles |
| `tab_trainer.py` | La vue formateur — suivi de cohorte |

**Pour l'expert :** Ces fichiers ne contiennent QUE de la logique UI (widgets Streamlit, rendu HTML, appels aux services). Aucune logique métier. La frontière est protégée par une règle de gouvernance explicite dans CLAUDE.md. Cela permet de modifier l'UX sans risquer de casser le moteur pédagogique.

---

### `ai_service.py` — Le cerveau LLM

**Pour le néophyte :** C'est le fichier qui parle à l'intelligence artificielle (OpenAI). Il génère les questions, corrige tes réponses, et calcule ton score.

**Pour l'expert :**
- Embeddings : `text-embedding-3-small`, 1 536 dimensions, stockés en BLOB float32 Little Endian dans SQLite
- Questions : `gpt-4o-mini` avec prompt structuré + contexte RAG (top-K chunks)
- Correction : JSON structuré `{score, correction, error_type, topic, confidence_score}`
- Timeout : 30 secondes sur tous les appels LLM
- Fallback : si RAG ou API échoue → génération depuis `source_text` brut
- Rate limiting : sliding window per-user/per-type (Phase 17)

**Pourquoi `gpt-4o-mini` et pas GPT-4o ?** Rapport qualité/coût optimal pour des questions pédagogiques contextualisées. Le modèle est suffisant pour le type de raisonnement requis ; GPT-4o n'apporterait pas de valeur mesurable pour ce cas d'usage.

**Pourquoi `text-embedding-3-small` ?** 1 536 dimensions = précision sémantique suffisante pour des documents métier. Le modèle large (3 072 dims) doublerait les coûts de stockage et de calcul sans amélioration perceptible sur ce corpus.

---

### `database.py` — La mémoire de l'application

**Pour le néophyte :** C'est le fichier qui lit et écrit dans la base de données. Il stocke tout : les documents, les questions, les réponses, les profils utilisateurs.

**Pour l'expert :** Couche d'accès SQLite (`sqlite3` stdlib). Organisé en 5 groupes fonctionnels :
1. Infrastructure (`init_db`, migrations douces `ALTER TABLE IF NOT EXISTS`)
2. Tentatives et analytics
3. Documents et chunks
4. Profil d'apprentissage
5. Administration des utilisateurs

Re-exports transparents depuis `adaptive_engine` pour compatibilité ascendante.

**Pourquoi SQLite et pas PostgreSQL ?** SQLite = zéro configuration, déploiement instantané, suffisant jusqu'à ~100 utilisateurs actifs simultanés pour ce type d'usage (lectures prédominantes). PostgreSQL est prévu (Phase 13 différée) dès qu'une `DATABASE_URL` de production est disponible.

**Règle critique — Stabilité des IDs :** On ne fait JAMAIS de DELETE+INSERT sur les chunks et les tentatives. Toujours des UPDATE. Raison : les identifiants `chunk_id` sont la clé étrangère de toute la mémoire pédagogique. Les supprimer reviendrait à effacer l'historique d'apprentissage d'un utilisateur.

---

### `engine/` — Le cerveau pédagogique (module pur)

**Pour le néophyte :** C'est la partie la plus complexe et la plus importante. C'est elle qui décide quoi te faire réviser, quand, et comment. Elle n'a aucun accès à internet ni à la base de données — elle travaille uniquement avec les données qu'on lui donne.

**Pour l'expert :** Contrainte architecturale critique : **zéro import projet** dans ce répertoire. Chaque module est testable de façon isolée, sans Streamlit, sans SQLite, sans OpenAI. Cette pureté garantit que le moteur est toujours portable et testable en CI sans infrastructure.

| Fichier | Rôle |
|---|---|
| `thresholds.py` | Source unique de vérité pour tous les seuils numériques |
| `spaced_rep.py` | Répétition espacée — classify_mastery, intervalles |
| `adaptive_difficulty.py` | Sélection adaptative du type de question (V2) |
| `question_type.py` | Définition des 6 types pédagogiques |
| `skill_engine.py` | Moteur de compétences — scoring par skill |
| `skill_graph.py` | Graphe de compétences Bloom (5 niveaux) |
| `session_plan.py` | Plan de session adaptatif ordonné par priorité |
| `retention.py` | Métriques de rétention J+1 / J+7 / J+30 |
| `profile_metrics.py` | Momentum, vélocité, consistance |

---

### `engine/thresholds.py` — Pourquoi ces valeurs précisément ?

C'est le fichier le plus important de toute la pédagogie. Chaque constante a été **calibrée par harness de simulation** (Phase 18C) sur 5 séquences de données réelles et simulées.

```python
MASTERY_FRAGILE      = 0.60   # En dessous de 60% → notion fragile
MASTERY_MASTERED     = 0.80   # Au-dessus de 80% → notion acquise
MASTERY_MIN_ATTEMPTS = 5      # Minimum 5 tentatives pour valider l'acquisition
ADAPTIVE_FORCE_EASY  = 0.40   # En dessous de 40% récent → on force les questions faciles
ADAPTIVE_ALLOW_HARD  = 0.65   # Au-dessus de 65% récent → on autorise les questions difficiles
REVIEW_INTERVALS     = Fragile:1j / En consolidation:3j / Maîtrisé:7j
```

**Pourquoi 0.60 comme seuil "Fragile" ?**
Un score moyen < 60% sur plusieurs tentatives indique une incompréhension structurelle, pas une erreur ponctuelle. En dessous, le système force des questions simples (vrai/faux, question directe) pour reconstruire la base.

**Pourquoi 0.80 pour "Maîtrisé" ?**
80% est le seuil standard en psychologie cognitive pour considérer qu'un apprentissage est consolidé (issu des travaux de Bloom et des courbes d'oubli d'Ebbinghaus). En dessous, il reste des zones d'ombre.

**Pourquoi 5 tentatives minimum ?**
Un seul score de 80% peut être de la chance. 5 tentatives permettent de confirmer que la performance est stable et reproductible. Cette valeur a été validée par le calibration harness (SEQ-C, commit `897824d`) — 3 tentatives produisaient trop de faux positifs "Maîtrisé".

**Pourquoi 1j / 3j / 7j pour la répétition espacée ?**
Ces intervalles sont issus de la recherche en mémoire (Leitner, Ebbinghaus). L'intervalle court (1 jour) pour les notions fragiles assure une répétition avant que l'oubli ne s'installe. L'intervalle de 7 jours pour les notions maîtrisées exploite la "spacing effect" : réviser trop tôt est du temps perdu.

---

### `rag_service.py` — Le chercheur sémantique

**Pour le néophyte :** Quand le système a besoin de générer une question sur un sujet précis, ce fichier va chercher dans le document les passages les plus pertinents — pas par mots-clés, mais par sens.

**Pour l'expert :**
- Recherche vectorielle cosinus : `cos(A, B) = (A·B) / (|A| × |B|)`
- Implémentée en numpy pur (pas de base vectorielle externe)
- BLOB float32 décodé à la volée depuis SQLite
- `search_similar_chunks(query_vector, document_id, top_k=3)`
- Supporte le mode corpus (`search_similar_chunks_multi` — cross-documents)
- Fallback garanti si aucun embedding disponible

**Pourquoi pas Chroma / Qdrant / Milvus ?** Pour un MVP à < 50 documents, la recherche cosinus numpy sur 500-2000 chunks est sous 50ms. L'overhead d'un service vectoriel externe (réseau, maintenance, coût) n'est pas justifié. La migration vers pgvector est préparée en Phase 13.

---

### `auth_service.py` — La sécurité des comptes

**Pour le néophyte :** Ce fichier gère les comptes utilisateurs — inscription, connexion, et les niveaux d'accès.

**Pour l'expert :**
- Hash bcrypt (facteur de coût par défaut : 12 rounds)
- Rôles : `apprenant` / `formateur` / `admin`
- `promote_user()` pour le bootstrap initial admin
- Seed auto : si aucun admin en base au démarrage, un compte démo admin/formateur est créé
- Fonctions pures testables sans Streamlit

**Pourquoi bcrypt et pas SHA-256 ?** bcrypt est conçu pour être intentionnellement lent à calculer. SHA-256 est trop rapide et vulnérable aux attaques par force brute / rainbow tables. bcrypt est le standard de l'industrie pour les mots de passe.

---

### `document_service.py` — Le lecteur de documents

**Pour le néophyte :** C'est le fichier qui sait lire les PDF, les fichiers texte et les DOCX. Il les découpe ensuite en petits morceaux pour que l'IA puisse les comprendre.

**Pour l'expert :**
- Extraction PDF : `pdfplumber`
- Extraction DOCX : `python-docx`
- Chunking : par section logique (~500 caractères), avec titre de section préservé
- Nettoyage : espaces multiples, caractères spéciaux, normalisation Unicode
- Seed démo : documents d'exemple injectés automatiquement si corpus vide

**Pourquoi ~500 caractères par chunk ?** C'est la taille optimale pour les embeddings OpenAI : assez long pour avoir du sens sémantique, assez court pour rester sous les limites de tokens du LLM (4096 tokens de contexte pour `gpt-4o-mini`). Un chunk trop long dilue le signal sémantique. Un chunk trop court perd le contexte.

---

### `db/` — Les modules base de données segmentés

Segmentation de `database.py` en modules ciblés (Phase 15+) :

| Fichier | Responsabilité |
|---|---|
| `db/corpus.py` | Gestion des corpus personnalisés multi-documents |
| `db/sessions.py` | Tracking des sessions et événements |
| `db/runtime_metrics.py` | Métriques d'observabilité LLM |
| `db/chunks.py` | Accès aux chunks et embeddings |

---

### `ai_gateway/` — La passerelle LLM instrumentée

**Pour l'expert :** Wrapper autour des appels OpenAI qui instrumente automatiquement : latence, tokens consommés, coût estimé, type d'appel, fallback activé. Stocke dans `runtime_metrics` pour le dashboard admin.

---

### `observability/` — L'observabilité applicative

**Pour l'expert :**
- `metrics.py` : compteurs et gauges applicatifs
- `error_tracker.py` : intégration Sentry (logging + exceptions)
- CLI analytique : 5 sections, verdict OK / WARNING / CRITICAL

---

### `tools/` — La boîte à outils de développement

Outils CLI non liés à l'application en production :

| Sous-dossier | Contenu |
|---|---|
| `tools/testing/` | Suite runner, simulation adaptative, calibration harness |
| `tools/qa/` | Tests de robustesse 100 questions, screenshots |
| `tools/admin/` | Création d'admin CLI, reset de mot de passe |
| `tools/observability/` | Skill graph observer, correction map, audit skills |
| `tools/guardrails/` | Vérification d'architecture automatisée |

---

### `frontend/` — Composants UI réutilisables

Dashboard formateur modulaire (composants Streamlit isolés) :
- `stat_card.py` — carte KPI
- `learner_card.py` — fiche apprenant
- `progress_chart.py` — graphique de progression
- `recommendation_panel.py` — recommandations pédagogiques

---

### `architecture_guard/` — Le gardien de l'architecture

**Pour l'expert :** Système de règles automatisées qui vérifient que les contraintes architecturales ne sont pas violées (ex : `adaptive_engine.py` ne doit pas importer de modules projet). Exécuté en CI/CD.

---

### `backups/` — Les sauvegardes de stabilité

Snapshots du code aux jalons clés (Phase 14, pre-Phase 15). Permettent un rollback instantané si une migration casse la production.

---

# PARTIE 3 — LE PIPELINE EN ACTION (de bout en bout)

## Ce qui se passe quand tu charges un document

```
1. Tu uploads un PDF dans l'onglet Documents
        │
        ▼
2. document_service.py extrait le texte
   → nettoyage, normalisation
        │
        ▼
3. Chunking en segments ~500 chars avec titre de section
   → 10 à 100 chunks selon la taille du document
        │
        ▼
4. ai_service.generate_embedding() sur chaque chunk
   → appel OpenAI text-embedding-3-small
   → vecteur float32 [1536 dimensions]
   → stocké en BLOB dans chunks.embedding
        │
        ▼
5. Document prêt — disponible pour l'entraînement
```

## Ce qui se passe quand tu réponds à une question

```
1. Tu cliques sur "Nouvelle question"
        │
        ▼
2. engine : classify_mastery() pour chaque chunk
   → quel chunk nécessite révision le plus urgement ?
        │
        ▼
3. engine : choose_adaptive_question_type()
   → quel type de question selon profil + mastery + erreurs ?
   → vrai_faux / question_directe / reformulation /
      cas_pratique / consequence / question_piege
        │
        ▼
4. ai_service : vectorise le topic/chunk
   → rag_service : top-K chunks similaires (cosinus)
        │
        ▼
5. ai_service.generate_question(context=chunks, type=X)
   → appel gpt-4o-mini avec contexte RAG
   → question retournée
        │
        ▼
6. Tu réponds
        │
        ▼
7. ai_service.correct_answer()
   → appel gpt-4o-mini avec ta réponse + réponse attendue
   → JSON : {score, correction, error_type, topic, confidence}
        │
        ▼
8. database.save_attempt() → tentative enregistrée
        │
        ▼
9. database.compute_and_save_learning_profile()
   → profil mis à jour : mastery, momentum, velocity
        │
        ▼
10. Tab Training affiche feedback + prochaine révision suggérée
```

---

# PARTIE 4 — LES 6 TYPES DE QUESTIONS ET LEUR LOGIQUE

| Type | Description | Quand utilisé |
|---|---|---|
| `vrai_faux` | Affirmation à valider ou réfuter | Notion fragile, confusion de concept |
| `question_directe` | Question frontale sur un fait | Premier contact avec une notion |
| `reformulation` | "Explique avec tes mots" | Réponse vague détectée |
| `cas_pratique` | Mise en situation réelle | Notion en consolidation |
| `consequence` | "Que se passe-t-il si..." | Notion maîtrisée, test de raisonnement |
| `question_piege` | Fausse évidence à démonter | Expert — solidité de la maîtrise |

**La progression pédagogique est délibérée :** On ne pose pas de question piège à quelqu'un qui est encore fragile sur la notion. Le moteur bloque physiquement l'accès aux types "hard" si le score récent est < 40%.

---

# PARTIE 5 — LES 20 QUESTIONS D'UN EXPERT SI

---

**Q1 — Quelle est la stack technique complète ?**

Python 3.11+, Streamlit (framework UI web), SQLite (base de données locale), OpenAI API (embeddings + LLM), numpy (calcul vectoriel), pandas (dataframes analytiques), bcrypt (hachage mots de passe), pdfplumber (extraction PDF), python-docx (extraction DOCX), Sentry (monitoring), Docker (conteneurisation), Railway (PaaS déploiement), GitHub Actions (CI/CD).

---

**Q2 — Pourquoi Streamlit et pas FastAPI + React ?**

Pour un MVP de démonstration développé seul, Streamlit permet d'avoir une UI fonctionnelle et testable en quelques heures sans gérer un frontend séparé. La migration vers FastAPI + React est prévue si le produit passe en mode SaaS multi-tenant avec des besoins UI complexes. La logique métier est déjà isolée dans des modules purs, ce qui rend cette migration non destructive.

---

**Q3 — Comment garantissez-vous la sécurité des données ?**

- Mots de passe hashés bcrypt (12 rounds, non réversibles)
- Aucune donnée sensible en clair en base
- Ségrégation des rôles (apprenant / formateur / admin) avec vérification à chaque route
- Rate limiting sliding window per-user sur les appels API
- Variables d'environnement pour les clés API (jamais commitées)
- Monitoring Sentry avec scrubbing des données personnelles
- Docker avec utilisateur non-root en production

---

**Q4 — Quelle est la capacité de montée en charge actuelle ?**

SQLite supporte confortablement 50-100 utilisateurs actifs simultanés pour ce type de workload (lectures prédominantes, écriture à la soumission de réponse). Au-delà, la migration vers PostgreSQL est architecturalement préparée (Phase 13) : les signatures de fonctions ne changent pas, seule l'implémentation interne de `database.py` évolue. pgvector remplace alors la recherche cosinus numpy.

---

**Q5 — Comment fonctionne la recherche sémantique ?**

Similarité cosinus : `cos(θ) = (A·B) / (|A|×|B|)` calculée en numpy sur les vecteurs float32 (1 536 dimensions) stockés en BLOB dans SQLite. À la génération d'une question, le topic est vectorisé, et les top-K chunks les plus proches sémantiquement sont récupérés comme contexte. Un chunk qui parle de "procédure de validation" ressemblera sémantiquement à "comment valider une étape", même si les mots sont différents.

---

**Q6 — Comment avez-vous calibré les seuils du moteur adaptatif ?**

Par simulation contrôlée (Phase 18C). Un harness de calibration injecte des séquences de tentatives synthétiques en base temporaire, fait tourner le moteur, et vérifie que les décisions sont cohérentes avec les attentes pédagogiques. 5 séquences distinctes ont été testées : progression linéaire, plateau, régression, alternance, expert rapide. Chaque seuil a été validé par ce harness avant d'être fixé dans `engine/thresholds.py`.

---

**Q7 — Qu'est-ce que le "module pur" et pourquoi est-ce important ?**

`engine/` n'importe aucun module projet (pas de Streamlit, pas de SQLite, pas d'OpenAI). Cela signifie que tout le cerveau pédagogique est testable en millisecondes sans infrastructure. En CI/CD, les 262 tests passent en quelques secondes. Cela garantit aussi que le moteur est portable : il peut être branché sur n'importe quel frontend ou backend sans modification.

---

**Q8 — Comment fonctionne la CI/CD ?**

GitHub Actions déclenche au push : `py_compile` exhaustif sur les 100+ fichiers Python, suite de tests pytest (262 tests), vérification des imports, déploiement automatique sur Railway si tous les checks passent. Le score d'audit global (`global_system_auditor.py`) valide 10 sections de l'architecture en lecture seule.

---

**Q9 — Quelle est votre stratégie de fallback si OpenAI est indisponible ?**

Trois niveaux de fallback :
1. Si l'embedding échoue → recherche cosinus sautée, question générée depuis le texte brut du chunk
2. Si la génération échoue → réponse défensive `_CORRECT_FALLBACK` retournée, aucune tentative sauvegardée
3. Si le rate limiting est atteint → message utilisateur explicite, aucun crash

La règle architecturale est : "l'application doit toujours rester launchable, testable, démontrable."

---

**Q10 — Comment gérez-vous les migrations de base de données ?**

Migrations douces : toutes les colonnes ajoutées en cours de projet utilisent `ALTER TABLE IF NOT EXISTS`. La base ne casse jamais au démarrage même si le schéma a évolué. Les migrations Alembic versionnées sont prévues pour la migration vers PostgreSQL (Phase 13).

---

**Q11 — Quel est le modèle de coût OpenAI estimé ?**

`text-embedding-3-small` : $0.02 / 1M tokens. Un document de 50 pages ≈ 50 chunks ≈ 50 appels d'embedding ≈ 25 000 tokens ≈ $0.0005 par document.
`gpt-4o-mini` : ~$0.15 / 1M input tokens, ~$0.60 / 1M output tokens. Une session de 10 questions ≈ $0.01-0.02 par utilisateur.
Le rate limiting (Phase 17) protège contre les abus.

---

**Q12 — Comment le système détecte-t-il les réponses hors sujet ?**

Le LLM de correction classe la réponse avec un type `non_evaluable` si elle est hors sujet, vide, ou incompréhensible. Ce type est filtré par le moteur : il n'influence pas le calcul de mastery et génère un feedback spécifique à l'utilisateur ("Hors sujet — reformulez votre réponse").

---

**Q13 — Quelle est la stratégie de tests ?**

262 tests en 3 niveaux :
- Tests unitaires : `adaptive_engine`, `auth_service`, `rag_service`, `engine/*` — modules purs
- Tests d'intégration : pipeline complet avec SQLite en mémoire (24 cas end-to-end)
- Tests de robustesse : simulation 500 requêtes mock (score robustesse 93/100)
- Suite runner orchestré : simulation adaptative → calibration → régression → verdict GO/WARNING/FAILED

---

**Q14 — Comment avez-vous géré le déploiement sur Railway ?**

Dockerfile `python:3.12-slim`, bind mount du volume `/app/data` pour la persistance SQLite, `railway.toml` avec healthcheck HTTP, variables d'environnement Railway pour `OPENAI_API_KEY` et `APP_PASSWORD`. Problèmes résolus : whitespace trailing dans les variables d'env, mode démo qui s'affichait alors qu'il y avait des utilisateurs en base, chemins SQLite relatifs vs absolus.

---

**Q15 — Comment garantissez-vous l'explicabilité des décisions du moteur ?**

Chaque décision du moteur est exposée à l'utilisateur :
- Pourquoi cette question ? → "Ce chunk a un score moyen de 0.45 (Fragile), révision urgente"
- Pourquoi ce type ? → `explain_type_choice()` retourne un texte lisible
- Quand revenir ? → `review_status` : "Dans 3 jours" / "En retard"
- Profil pédagogique : radar chart des 4 dimensions + momentum + velocity
- Source RAG : les chunks utilisés pour générer la question sont affichés

---

**Q16 — Qu'est-ce que le Skill Graph et le modèle de Bloom ?**

Le Skill Graph (Phase 16) mappe les chunks sur un graphe de compétences avec 5 niveaux de la taxonomie de Bloom : Mémorisation → Compréhension → Application → Analyse → Synthèse. Cela permet de bloquer l'accès aux types de questions "hard" (conséquence, question piège) si la compétence n'est pas encore à un niveau suffisant dans le graphe. `tab_engine` visualise ce graphe en données réelles : chaque compétence affiche le score de maîtrise calculé depuis les tentatives de l'utilisateur (`user_skill_mastery`), avec badge coloré vert/orange/rouge selon le niveau atteint.

---

**Q17 — Comment fonctionne le suivi de session ?**

Tables `learning_sessions` + `session_events` (Phase 20). Chaque session est tracée avec début, fin, nombre de questions, score moyen. Les événements intra-session (question générée, réponse soumise, feedback affiché) sont horodatés. Cela permet le calcul du heat map d'activité (8 semaines) et des KPIs de régularité.

---

**Q18 — Quelle est votre approche de la qualité des chunks ?**

`Chunk Quality Analyzer` (Phase 16, TASK-054) évalue chaque chunk sur :
- Longueur (trop court = pas de sens, trop long = dilution sémantique)
- Présence d'un titre de section identifiable
- Densité informationnelle (ratio mots-clés / mots courants)
- Score RAG overlap (chevauchement sémantique avec les chunks voisins)
- Heuristique TRUNC (chunks tronqués en milieu de phrase)

---

**Q19 — Comment assurez-vous la non-régression entre les phases ?**

Tripwires dans `test_regression.py` : tests qui échouent si un seuil critique est modifié sans mise à jour du harness de calibration. Par exemple, `TestReviewIntervalsCoherence` détecte toute divergence entre les constantes `REVIEW_INTERVALS` et la logique SQL correspondante. Ces tripwires ont détecté 3 régressions silencieuses durant le développement.

---

**Q20 — Quelle est la roadmap technique pour passer en production SaaS multi-tenant ?**

1. **Phase 13** : Migration SQLite → PostgreSQL via SQLAlchemy Core + Alembic (préparée)
2. **Phase 21** : Isolation des données par `tenant_id` dans toutes les tables
3. **Phase 22** : API REST (FastAPI) exposant le moteur pédagogique
4. **Phase 23** : Frontend React découplé, API consommée
5. **Phase 24** : pgvector pour la recherche cosinus native à l'échelle
6. **Phase 25** : Kubernetes / auto-scaling si > 10k utilisateurs actifs

Le moteur adaptatif en Python pur (aucun import projet) est déjà isolé et réutilisable tel quel dans cette architecture cible.

---

# PARTIE 6 — LES 20 QUESTIONS D'UN RH / DRH

---

**Q1 — C'est quoi concrètement, ADDISCO OPS ?**

C'est une application qui prend n'importe quel document professionnel (manuel de procédures, fiche technique, règlement intérieur, guide produit) et le transforme en un coach d'apprentissage intelligent. Au lieu de demander à un employé de lire un PDF et d'espérer qu'il retienne l'information, ADDISCO OPS lui pose des questions progressives, corrige ses réponses, et répète les notions difficiles jusqu'à ce qu'elles soient réellement maîtrisées.

---

**Q2 — À qui s'adresse cette application ?**

Trois profils d'utilisateurs :
- **L'apprenant** : tout employé qui doit maîtriser un contenu documentaire. Il travaille à son rythme, depuis n'importe quel appareil.
- **Le formateur** : référent RH ou manager qui suit la progression de ses équipes, identifie les notions bloquantes, exporte des rapports pédagogiques.
- **L'administrateur** : gestionnaire de la plateforme, qui gère les accès, importe les documents, et consulte les statistiques globales.

---

**Q3 — Quels types de documents peut-on utiliser ?**

PDF, Word (DOCX), fichiers texte (TXT). Typiquement : manuels de procédures, fiches de poste, référentiels qualité, guides produits, règlements internes, supports de formation, notes de service.

---

**Q4 — Est-ce que l'application remplace un formateur humain ?**

Non. Elle complète et libère le formateur. Le formateur importe les contenus et consulte les tableaux de bord. L'application fait le travail répétitif de l'interrogation et de la correction. Le formateur peut alors se concentrer sur les échanges à valeur ajoutée : débriefing, accompagnement, cas complexes.

---

**Q5 — Comment l'application s'adapte-t-elle à chaque employé ?**

Elle observe en permanence : quelles notions posent problème ? Quel style de question fonctionne le mieux pour cet employé ? A-t-il besoin d'exemples concrets (cas pratique) ou de définitions claires (question directe) ? Est-il en progression ou en régression sur la dernière semaine ? Et elle adapte en conséquence le type de question et la fréquence de révision.

---

**Q6 — Peut-on suivre la progression de plusieurs employés en même temps ?**

Oui. Le dashboard formateur affiche les KPIs de cohorte : score moyen, notions fragiles communes, progression sur la période, alertes sur les apprenants en difficulté. Des rapports HTML / PDF sont générables en un clic par apprenant ou par groupe.

---

**Q7 — Les données des employés sont-elles confidentielles ?**

Oui. Les données restent dans l'environnement de l'entreprise (auto-hébergement possible via Docker) ou sur un serveur Railway dédié avec isolation des données. Les mots de passe sont cryptés et non récupérables. Aucune donnée n'est partagée avec des tiers. La donnée sensible n'est jamais stockée en clair.

---

**Q8 — Combien de temps faut-il pour former un employé sur un document ?**

Cela dépend du document et de l'employé, mais le système fournit des estimations : "Plan de session : 8 chunks à réviser, durée estimée 25 minutes." Il propose aussi des métriques de rétention à J+1, J+7 et J+30 pour valider que l'apprentissage est durable et pas seulement momentané.

---

**Q9 — Est-ce que ça marche pour des formations réglementaires (RGPD, sécurité, etc.) ?**

Oui, c'est même le cas d'usage le plus adapté. Pour des formations réglementaires avec des notions précises à maîtriser (et à prouver maîtrisées), ADDISCO OPS offre un historique complet et auditable de chaque tentative, avec date, score, et type d'erreur. Ce log est exportable.

---

**Q10 — Peut-on savoir si un employé a vraiment appris ou s'il a juste "fait le quiz" ?**

Oui. Le système requiert un minimum de 5 tentatives sur une notion avant de la classer "Maîtrisée". Un score unique de 80% n'est pas suffisant. De plus, la répétition espacée revient tester la notion après 7 jours : si l'employé a oublié entre-temps, le score chute et la notion repasse en "Fragile". C'est la mesure de rétention réelle, pas de performance ponctuelle.

---

**Q11 — Comment intégrer un nouveau document de formation ?**

En quelques minutes : charger le document → l'application le découpe automatiquement → génère les embeddings sémantiques → le document est disponible pour la formation. Aucune intervention technique nécessaire de la part du RH ou du formateur.

---

**Q12 — Peut-on personnaliser les questions posées ?**

Les questions sont générées automatiquement par l'IA à partir du contenu du document. Il n'est pas nécessaire (ni possible) de les saisir manuellement — c'est précisément ce qui fait gagner du temps. En revanche, un formateur peut commenter les questions jugées "non pertinentes" via le système de feedback qualitatif intégré, ce qui améliore le moteur dans le temps.

---

**Q13 — Est-ce utilisable sur mobile ?**

L'interface est responsive et a été optimisée pour tablette (Phase 16, TASK-063). Sur mobile, certains graphiques sont limités, mais le flux d'entraînement (question → réponse → feedback) est entièrement fonctionnel.

---

**Q14 — Combien de documents peut-on charger ?**

Il n'y a pas de limite stricte applicative. Techniquement, la performance reste optimale jusqu'à ~50 documents par corpus sur la configuration actuelle (SQLite). Au-delà, le passage à PostgreSQL (prévu) permet de monter à plusieurs milliers de documents sans dégradation.

---

**Q15 — Comment savoir si un employé est "prêt" sur un sujet ?**

Le système fournit un statut par notion : Fragile / En consolidation / Maîtrisé. "Maîtrisé" signifie : score moyen ≥ 80%, validé sur au minimum 5 tentatives, confirmé par une révision à J+7. Le formateur peut fixer un seuil de validation (ex : "80% des notions du document doivent être Maîtrisées avant habilitation").

---

**Q16 — Peut-on utiliser l'application pour de l'onboarding ?**

C'est l'un des cas d'usage les plus naturels. Un nouvel arrivant charge le corpus onboarding (règlement, procédures, valeurs, outils), s'entraîne à son rythme, et le RH suit sa progression en temps réel. Plus besoin d'organiser des sessions de contrôle : le système fait ce travail automatiquement.

---

**Q17 — Comment l'application gère-t-elle les mises à jour de documents ?**

Si une procédure change, on importe la nouvelle version. Le système garde l'historique de l'ancienne version et commence à générer des questions depuis la nouvelle. Les employés continuent leur progression ; les notions communes entre les deux versions bénéficient de l'historique existant.

---

**Q18 — Peut-on exporter les résultats pour un audit ou une certification ?**

Oui. Des rapports HTML et PDF sont générables par apprenant (7 sections : profil, scores, notions maîtrisées, fragiles, historique, recommandations, métriques de rétention). Ces rapports sont datés, signés par le système, et contiennent l'horodatage de chaque tentative.

---

**Q19 — Quel est le coût de déploiement ?**

- Auto-hébergé (Docker) : coût serveur uniquement (~15-30€/mois pour une instance Railway ou DigitalOcean)
- Coût OpenAI : ~$0.01-0.02 par session de 10 questions par apprenant
- Pour 50 employés utilisant 3 sessions/semaine : ~$6-15/mois en coûts API
- Zéro licence logicielle — le code est entièrement propriétaire

---

**Q20 — Est-ce que l'IA peut générer de fausses informations sur nos documents ?**

Le système est conçu pour rester ancré dans le document source (principe RAG). Les questions sont générées à partir des passages réels du document. Des garde-fous détectent les réponses "hors sujet" et les rejettent. Cependant, comme tout LLM, une erreur est possible ; c'est pourquoi le contexte source (le chunk utilisé) est toujours affiché à l'utilisateur pour vérification. La recommandation est de valider les premiers documents importants avec un expert métier.

---

# PARTIE 7 — VISION SCALABILITÉ : AU-DELÀ DES DOCUMENTS

## Le moteur est plus universel qu'il n'y paraît

ADDISCO OPS a été construit sur des documents, mais son moteur pédagogique est **agnostique au type de données**. Il fonctionne sur tout ce qui peut être découpé en chunks sémantiques et évalué par un LLM.

---

## Cas d'usage potentiels

### 1. Formation sur données procédurales (BPMN, workflows)
Au lieu de charger un PDF, on charge une description de processus métier. Le moteur pose des questions sur les étapes, les exceptions, les règles de gestion. **Modification requise :** Parser BPMN/XML → texte structuré (nouveau `document_service` adapter).

### 2. Formation sur données produits (ERP, CRM, catalogue)
Charger un export CSV / JSON de produits. Chaque produit = un chunk. L'IA pose des questions commerciales. **Modification requise :** Chunk loader JSON/CSV + prompt adapté à la nature commerciale.

### 3. Formation réglementaire et juridique (codes, normes, lois)
Idéal pour ISO, RGPD, normes AFNOR, code du travail. Le contenu est stable, précis, et critique. **Modification requise :** Aucune — c'est déjà le cas d'usage documentaire standard.

### 4. Aide décisionnelle — Diagnostic assisté
Le formateur pose une problématique métier. Le système retrouve les chunks pertinents du corpus et propose des éléments de réponse sourcés. **Ce n'est plus de la formation, c'est de la recherche augmentée.** L'interface change, le moteur RAG est identique. **Modification requise :** Nouvel onglet "Diagnostic" avec mode Q&A (pas d'évaluation, juste retrieval + réponse).

### 5. Aide décisionnelle — Checklist intelligente
Pour des métiers à procédures (qualité, audit, maintenance), le système génère une checklist adaptative à partir du corpus procédural et pose des questions de vérification. **Modification requise :** Nouveau type de question `checklist_item` + interface dédiée.

### 6. Onboarding produit client (SaaS)
Un éditeur logiciel importe sa documentation et permet à ses clients de se former sur l'outil. Moteur identique, personas différents. **Modification requise :** Interface multi-tenant (tenant_id dans toutes les tables — Phase 21 roadmap).

### 7. Base de connaissances conversationnelle
Le corpus documentaire devient une base interrogeable en langage naturel. Un agent conversation branché sur le même RAG peut répondre aux questions des employés en temps réel. **Modification requise :** Ajout d'un mode "Agent Q&A" avec historique de conversation (pas d'évaluation). Compatible avec l'architecture existante.

### 8. Simulation de décision (aide à la décision RH / opérationnelle)
Le système analyse des scénarios (ex : "Mon employé fait X, quelle est la procédure ?") contre le corpus procédural et retourne la réponse sourcée + niveau de confiance. **Modification requise :** Nouveau prompt de type `decision_support` + interface dédiée.

---

## Modifications techniques requises pour l'aide décisionnelle

### Ce qui existe déjà et est réutilisable à 100%
- Pipeline RAG complet (chunking, embeddings, recherche cosinus) ✓
- Stockage et gestion des documents ✓
- Authentification et gestion des rôles ✓
- Infrastructure (Docker, Railway, monitoring) ✓
- Interface multi-rôles ✓

### Ce qu'il faudrait ajouter (par ordre de priorité et simplicité)

**1. Mode Q&A non-évaluatif (2-3 jours de développement)**
```
Nouvel onglet "Recherche" :
- Champ texte libre : "Quelle est la procédure pour X ?"
- RAG retrouve les top-5 chunks pertinents
- LLM synthétise une réponse sourcée
- Sources affichées avec numéro de chunk et extrait
```
Fichiers impactés : `tabs/tab_search.py` (nouveau), `ai_service.py` (nouvelle fonction `answer_question()`), `app.py` (routing).

**2. Checklist procédurale interactive (1 semaine)**
```
Lecture d'un corpus procédural
→ Extraction des étapes clés (nouveau chunker "étape")
→ Génération d'une checklist cliquable
→ Tracking de complétion (table checklist_completions)
```

**3. Dashboard décisionnel formateur enrichi (3-5 jours)**
```
Ajout dans tab_trainer.py :
- Heatmap des notions fragiles par équipe
- Recommandation automatique de sessions de formation
- Export vers SIRH (CSV normalisé)
```

**4. Multi-tenant (2-3 semaines — Phase 21)**
```
Ajout de tenant_id dans : users, documents, chunks, attempts, corpus
Isolation des données par tenant
Interface d'administration globale
```

### Architecture cible pour l'aide décisionnelle

```
ADDISCO OPS (formation)          ADDISCO DECIDE (aide décisionnelle)
──────────────────────           ──────────────────────────────────
Mêmes documents                  Même corpus
Même RAG                         Même RAG
Questions → Évaluation           Questions → Réponses sourcées
Profil apprenant                 Log décisionnel
Répétition espacée               Recherche contextuelle
```

Le pivot est minimal : le corpus, le RAG, et l'infrastructure sont communs. Seul le "mode" change (évaluation vs. réponse).

---

# PARTIE 8 — GLOSSAIRE TECHNIQUE

| Terme | Explication simple |
|---|---|
| **RAG** | Retrieval-Augmented Generation — l'IA va chercher les passages pertinents avant de répondre |
| **Embedding** | Représentation mathématique du sens d'un texte (vecteur de 1 536 nombres) |
| **Chunk** | Fragment de document (~500 caractères) — l'unité de base du système |
| **Cosinus** | Mesure de similarité entre deux vecteurs — proche de 1 = très similaires |
| **Maîtrise** | Niveau d'acquisition d'une notion : Fragile / En consolidation / Maîtrisé |
| **Répétition espacée** | Technique de mémorisation : réviser au bon moment, pas trop tôt, pas trop tard |
| **Momentum** | Vitesse de progression sur les 7 derniers jours |
| **Velocity** | Delta de score moyen entre sessions |
| **Bloom** | Taxonomie des niveaux d'apprentissage : Mémorisation → Synthèse |
| **SQLite** | Base de données légère stockée dans un fichier — parfaite pour un MVP |
| **bcrypt** | Algorithme de hachage pour les mots de passe (non réversible) |
| **fallback** | Mode dégradé garanti — l'application continue de fonctionner même si l'IA est indisponible |
| **CI/CD** | Intégration et déploiement continus — les tests tournent automatiquement à chaque modification |
| **Docker** | Conteneur standardisé — l'application fonctionne de façon identique partout |

---

# PARTIE 9 — ÉTAT ACTUEL ET PROCHAINES ÉTAPES

## Ce qui est opérationnel aujourd'hui (Phase 20 — 2026-05-25)

- Application déployée sur Railway (production)
- 262 tests automatisés (pytest)
- Score d'audit global : 99/100
- Score de robustesse : 93/100 (500 requêtes mock)
- 6 types de questions pédagogiques
- Répétition espacée calibrée (5 tentatives minimum, intervalles 1/3/7 jours)
- Profil utilisateur : 4 dimensions pédagogiques + momentum + velocity + consistency
- Corpus multi-documents avec recherche sémantique cross-documents
- Feedback qualitatif des questions (pertinent / non pertinent)
- Tracking de sessions complet (heatmap, KPIs, insights)
- Dashboard dark premium apprenant + formateur + admin
- Rapports HTML/PDF exportables
- Monitoring Sentry + rate limiting per-user

## Ce qui est prévu et architecturalement préparé

| Phase | Objet | Complexité |
|---|---|---|
| Phase 21 | Multi-tenant (tenant_id) | Moyenne |
| Phase 13 | PostgreSQL + pgvector | Faible (préparée) |
| Phase 22 | API REST FastAPI | Moyenne |
| Phase 23 | Frontend React découplé | Haute |
| Phase 24 | Mode Q&A décisionnel | Faible |
| Phase 25 | Kubernetes / auto-scaling | Haute (si > 10k users) |

---

*Document généré le 2026-05-25 — ADDISCO OPS Phase 20*
*Pour toute question : marcelino.guilhem@gmail.com*
