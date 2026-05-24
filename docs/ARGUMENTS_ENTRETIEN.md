# Arguments entretien — ADDISCO OPS

Document de préparation personnelle. Pas pour montrer — pour intégrer.

---

## CE QUI EST RÉELLEMENT FORT

### 1. Discipline de gouvernance sur 20 phases

**L'argument :** J'ai tenu une architecture cohérente sur 84 tâches et 20 phases, seul,
sans dette technique incontrôlée. CLAUDE.md, ROADMAP incrémentale, DEVLOG chronologique,
commits isolés et réversibles — c'est une discipline que beaucoup d'équipes n'ont pas.

**Ce que ça prouve :** capacité à travailler sur un projet long sans se noyer,
à décomposer la complexité, à ne pas casser ce qui fonctionne.

---

### 2. Architecture modulaire maintenue sous pression d'ajout de features

**L'argument :** À chaque phase, j'aurais pu tout mettre dans `app.py`. J'ai au contraire
extrait `rag_service.py`, `adaptive_engine.py`, `auth_service.py`, `db/`, `engine/`, `tabs/`.
Le routeur `app.py` est resté sous 150 lignes.

**Ce que ça prouve :** compréhension réelle des responsabilités de couche,
pas juste du code qui fonctionne.

---

### 3. Pipeline RAG complet et instrumenté

**L'argument :** Import document → chunking → embeddings → stockage SQLite →
retrieval sémantique → génération contextualisée → correction → scoring → mémoire.
Chaque étape est traçable. Fallback texte brut si l'API échoue.

**Ce que ça prouve :** je comprends comment fonctionne un pipeline RAG de bout en bout,
pas seulement l'appel API.

---

### 4. Moteur adaptatif avec seuils explicites et calibrés

**L'argument :** Les 6 seuils du moteur (MASTERY_FRAGILE, MASTERY_MASTERED,
MASTERY_MIN_ATTEMPTS, ADAPTIVE_FORCE_EASY, ADAPTIVE_ALLOW_HARD, REVIEW_INTERVALS)
sont dans un fichier dédié `engine/thresholds.py`, documentés, testés par harness isolé,
et validés contre des séquences déterministes.

**Ce que ça prouve :** je ne code pas des constantes magiques — je les raisonne,
je les rends auditables, et je prépare leur évolution.

---

### 5. Tests : 262 cas, dont calibration isolée

**L'argument :** 262 tests, DB temporaire pour chaque test, patch mémoire pour les
calibrations — le moteur est testable sans toucher les données de production.
Le harness de calibration valide les invariants comportementaux, pas seulement la syntaxe.

**Ce que ça prouve :** les tests sont là pour attraper des régressions réelles,
pas pour afficher un compteur.

---

### 6. Déploiement Railway opérationnel

**L'argument :** L'application tourne en production. Dockerfile, railway.toml,
healthcheck, volume mount SQLite, APP_PASSWORD, Sentry. Ce n'est pas un projet
"qui marche en local".

**Ce que ça prouve :** je sais aller jusqu'au bout — dev → test → prod.

---

### 7. RAG et chunking mesurés, pas juste "fonctionnels"

**L'argument :** `compute_retrieval_overlap()` calcule le recouvrement lexical entre
la question générée et les chunks retrieval. Stocké en DB à chaque tentative.
Le `chunk_quality_analyzer` détecte les chunks tronqués (TRUNC), bruités (NOISY),
orphelins (ORPHAN), trop courts/longs — avec verdict global GO SAFE / WARNING / FAILED.

Résultat sur le corpus réel : 255/391 chunks tronqués sur les décrets — découpage
à taille fixe qui coupe les articles de loi au milieu. Cause identifiée, correction
possible (revoir le chunker sur ce type de document).

**Ce que ça prouve :** je ne me contente pas de dire "le RAG fonctionne" —
je l'instrumente pour savoir *à quel point* il fonctionne et *pourquoi* il échoue.

---

### 8. Arrêt volontaire au bon moment

**L'argument :** J'ai arrêté de builder quand le moteur était stable, déployé,
et la baseline établie. Continuer sans données utilisateurs réelles aurait été
de l'over-engineering. Les seuils sont posés pour être recalibrés par les données —
pas pour être définitifs.

**Ce que ça prouve :** maturité produit. Savoir quand s'arrêter est aussi important
que savoir construire.

---

## CE QUI EST LIMITÉ — ET COMMENT LE DIRE

### SQLite en production

**La réalité :** SQLite tient pour 5-10 utilisateurs légers en WAL mode.
Au-delà, risque de lock concurrents.

**Comment le formuler :** "SQLite est le choix MVP délibéré. La migration PostgreSQL
est documentée en Phase 13, différée jusqu'à avoir une vraie charge à mesurer.
Je ne voulais pas introduire une infrastructure lourde avant d'en avoir besoin."

---

### Seuils calibrés sur simulation, pas sur données réelles

**La réalité :** MASTERY_FRAGILE=0.60 et les autres sont validés contre des séquences
que j'ai construites moi-même. Sans 30+ jours d'usage humain, on ne peut pas
savoir si ces valeurs sont pédagogiquement optimales.

**Comment le formuler :** "J'ai établi une baseline raisonnée et traçable.
L'objectif n'était pas de trouver les valeurs définitives — c'était de créer
l'outillage pour les affiner sur des données réelles. Le harness de calibration
existe précisément pour ça."

---

### Qualité RAG et chunking — maintenant mesurés

**Ce qui a été fait :** `compute_retrieval_overlap()` dans `rag_service.py` mesure
le recouvrement lexical entre la question générée et les chunks retrieval (0.0–1.0),
stocké en DB à chaque tentative. Le `chunk_quality_analyzer` détecte désormais les
chunks tronqués (heuristique TRUNC : début minuscule = coupe milieu de phrase,
fin sans ponctuation = suite tronquée).

**Résultat concret :** 255/391 chunks TRUNC détectés sur le corpus de décrets.
Cause identifiée : découpage à taille fixe (1000 chars) qui coupe les articles de
loi au milieu. Donnée actionnable — le chunker doit être revu sur ce type de document.

**Comment le formuler :** "Mon analyzer détecte 65% de chunks tronqués sur le corpus
de décrets, ce qui explique les scores RAG plus faibles sur ce document. J'ai aussi
instrumenté un overlap score stocké à chaque tentative — quand j'aurai 30 jours de
données, je pourrai corréler overlap faible et mauvaises corrections pour identifier
les documents à re-chunker en priorité."

---

### Streamlit comme framework

**La réalité :** Session_state perdu au redémarrage, routing limité, pas de vrai mobile.
Pas adapté à un SaaS B2B au-delà du POC.

**Comment le formuler :** "Streamlit m'a permis de construire vite et de me concentrer
sur la logique métier. Pour une version SaaS réelle, la couche UI serait à refaire
en FastAPI + React. C'est un choix de vélocité POC, pas d'architecture finale."

---

### "AI orchestration" — ne pas surjouer le terme

**La réalité :** Le projet est un wrapper OpenAI bien structuré avec un moteur adaptatif.
Ce n'est pas de l'orchestration multi-agents au sens LangGraph/DSPy.

**Comment le formuler :** "J'ai construit un pipeline RAG instrumenté avec un moteur
adaptatif. Je ne prétends pas avoir fait de l'orchestration complexe — j'ai fait
de l'ingénierie solide autour d'une API LLM, ce qui est ce que la majorité des
projets production font réellement."

---

## LA POSTURE GLOBALE

Ne pas vendre le projet comme un produit fini.
Le vendre comme une preuve de méthode :

> "J'ai pris un problème réel, je l'ai décomposé en étapes maîtrisées,
> j'ai maintenu la stabilité à chaque itération, j'ai déployé, et j'ai su
> m'arrêter au bon moment pour laisser les données guider la suite.
> C'est ça que je saurais faire dans une équipe."

C'est l'argument le plus honnête — et le plus fort.
