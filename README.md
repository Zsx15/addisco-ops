# IA Révision Métier

Application de révision active basée sur l'IA, conçue pour transformer des documents métier en entraînement pédagogique adaptatif.

---

## Fonctionnalités

- **Import de documents** (TXT, PDF) — découpage automatique en sections avec détection des titres
- **Génération de questions** par l'IA à partir du contenu — 6 types de questions en rotation (directe, cas pratique, vrai/faux, piège, reformulation, conséquence)
- **Correction automatique** avec score, type d'erreur et réponse attendue
- **RAG** (Retrieval-Augmented Generation) — les questions sont générées à partir des sections les plus pertinentes du document
- **Répétition espacée** — chaque section a une date de prochaine révision calculée selon son niveau de maîtrise
- **Dashboard pédagogique** — progression par section (Fragile / En consolidation / Maîtrisé), tendance, statut de révision
- **Suggestion de révision** — la section prioritaire à réviser est proposée automatiquement dans l'onglet Entraînement
- **Document de démonstration préchargé** — l'application est opérationnelle dès le premier lancement, sans import préalable

---

## Prérequis

- Python 3.11 ou supérieur
- Clé API OpenAI (recommandé — voir ci-dessous)

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

Créer un fichier `.env` à la racine :

```env
OPENAI_API_KEY=votre_cle_api_openai
```

**Mode sans clé API (fallback) :** si `.env` est absent ou si la clé est invalide, l'application fonctionne en mode texte brut — les questions et corrections sont générées sans RAG ni embeddings. Les fonctionnalités pédagogiques (dashboard, répétition espacée, suggestion) restent actives sur les tentatives accumulées. Ce mode garantit que l'application ne plante jamais en cas d'indisponibilité de l'API.

---

## Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur. Un document de démonstration est automatiquement chargé si la base est vide.

---

## Architecture

```
app.py               — Interface Streamlit (4 onglets : Entraînement, Historique, Dashboard, Documents)
database.py          — Accès SQLite : tentatives, documents, chunks, analytics, répétition espacée
ai_service.py        — Appels OpenAI : génération de questions, correction, embeddings
document_service.py  — Ingestion, découpage en sections, seed de démonstration
.env                 — Clé API (non versionnée)
database.db          — Base SQLite locale (créée automatiquement au premier lancement)
requirements.txt     — Dépendances Python
```

Aucune base de données externe. Aucun serveur tiers. SQLite + OpenAI uniquement.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Streamlit |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Base de données | SQLite (stdlib) |
| Similarité vectorielle | Python pur (cosine similarity, float32 BLOB) |
| PDF | pypdf |

---

## Réinitialiser la base

```bash
# Supprimer la base locale — elle sera recréée et re-seedée au prochain lancement
del database.db       # Windows
rm database.db        # macOS / Linux
streamlit run app.py
```
