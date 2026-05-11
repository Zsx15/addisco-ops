# CLAUDE.md — Projet IA Révision / RAG / Apprentissage Adaptatif

## 1. Objectif du projet

Ce projet vise à construire une application IA capable de :
- ingérer des textes métier, procédures, documents PDF/DOCX ;
- générer des questions pertinentes ;
- corriger les réponses utilisateur ;
- attribuer un score ;
- mémoriser les erreurs ;
- suivre la progression ;
- intégrer progressivement un RAG avec embeddings ;
- adapter la pédagogie selon les difficultés observées ;
- évoluer vers une plateforme d’apprentissage métier intelligente.

Le produit ne doit pas être un simple quiz IA.
Il doit devenir un système de transmission métier adaptatif.

---

## 2. Règle de travail absolue

Ne jamais modifier massivement le projet sans validation.

Pour chaque demande :
1. analyser le besoin ;
2. identifier les fichiers concernés ;
3. proposer un plan ;
4. attendre validation si la modification est importante ;
5. modifier uniquement ce qui est nécessaire ;
6. expliquer les changements ;
7. donner la commande de test.

---

## 3. Stack actuelle attendue pour prototype

- Python
- Streamlit
- SQLite
- OpenAI API ou autre API IA
- python-dotenv
- pandas

---

## 4. Stack cible future

- Frontend : React / Next.js / TailwindCSS
- Backend : FastAPI
- Base relationnelle : PostgreSQL
- Base vectorielle : Qdrant, Milvus ou Weaviate
- RAG : chunking + embeddings + retrieval + re-ranking
- Déploiement : Docker
- Tests : pytest

---

## 5. Fonctionnalités de départ

Le prototype doit permettre :
- coller un texte ;
- générer une question ;
- répondre à la question ;
- corriger automatiquement ;
- donner un score ;
- enregistrer l’historique ;
- afficher les tentatives passées.

---

## 6. Fonctionnalités à ajouter progressivement

### Phase 1 — Stabilisation
- refactor du code ;
- séparation interface / logique métier ;
- meilleure gestion des erreurs ;
- README clair ;
- fichier requirements.txt ;
- .env.example.

### Phase 2 — Historique avancé
- type d’erreur ;
- notion concernée ;
- temps de réponse ;
- score moyen ;
- progression.

### Phase 3 — Import documentaire
- import PDF ;
- import DOCX ;
- extraction texte ;
- nettoyage texte ;
- stockage documents.

### Phase 4 — RAG
- découpage intelligent ;
- embeddings ;
- base vectorielle ;
- recherche sémantique ;
- récupération de passages utiles.

### Phase 5 — Apprentissage adaptatif
- suivi des formes pédagogiques ;
- détection des blocages ;
- reformulation adaptée ;
- répétition espacée ;
- révision ciblée.

### Phase 6 — Industrialisation
- multi-utilisateur ;
- dashboard ;
- analytics ;
- sécurité ;
- monitoring ;
- Docker ;
- documentation complète.

---

## 7. Principes produit

Toujours privilégier :
- simplicité ;
- robustesse ;
- progression étape par étape ;
- lisibilité du code ;
- logique métier ;
- données exploitables ;
- évolutivité.

Ne pas chercher à tout développer d’un coup.

---

## 8. Interdictions

Ne jamais :
- exposer une clé API ;
- supprimer une fonctionnalité existante sans accord ;
- refactoriser tout le projet d’un coup ;
- inventer une dépendance inutile ;
- créer une architecture trop complexe trop tôt ;
- faire du diagnostic médical ou psychologique de l’utilisateur.

Le système peut seulement dire :
“Cette forme pédagogique semble plus efficace pour cet utilisateur.”
