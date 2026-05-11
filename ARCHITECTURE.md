# ARCHITECTURE — Produit IA Révision / RAG / Apprentissage Adaptatif

## 1. Architecture prototype

```text
Utilisateur
  ↓
Streamlit
  ↓
Texte source
  ↓
Service IA
  ↓
Question
  ↓
Réponse utilisateur
  ↓
Correction IA
  ↓
Score
  ↓
SQLite
```

## 2. Architecture modulaire recommandée

```text
app.py
  ↓
ai_service.py
  ↓
database.py
  ↓
adaptive_engine.py
  ↓
document_service.py
  ↓
rag_service.py
```

## 3. Responsabilités des modules

### app.py
- interface Streamlit ;
- boutons ;
- affichage ;
- navigation.

### ai_service.py
- appels API IA ;
- génération de questions ;
- correction ;
- reformulation.

### database.py
- création base ;
- insertion historique ;
- lecture statistiques ;
- requêtes SQL.

### document_service.py
- import documents ;
- extraction texte ;
- nettoyage ;
- stockage.

### rag_service.py
- découpage ;
- embeddings ;
- recherche vectorielle ;
- récupération contexte.

### adaptive_engine.py
- analyse des erreurs ;
- choix pédagogique ;
- suivi progression ;
- règles adaptatives.

## 4. Architecture RAG cible

```text
Documents bruts
  ↓
Extraction texte
  ↓
Nettoyage
  ↓
Découpage intelligent
  ↓
Embeddings
  ↓
Base vectorielle
  ↓
Recherche sémantique
  ↓
Passages pertinents
  ↓
Prompt IA
  ↓
Réponse contextualisée
```

## 5. Architecture adaptative cible

```text
Question
  ↓
Réponse utilisateur
  ↓
Correction
  ↓
Type d’erreur
  ↓
Historique utilisateur
  ↓
Détection pattern
  ↓
Choix pédagogie
  ↓
Nouvelle explication
  ↓
Mesure efficacité
```

## 6. Données principales

### Table attempts
- id
- user_id
- document_id
- question
- user_answer
- expected_answer
- correction
- score
- error_type
- topic
- pedagogy_type
- response_time
- created_at

### Table documents
- id
- title
- source_type
- raw_text
- cleaned_text
- created_at

### Table chunks
- id
- document_id
- chunk_text
- chunk_index
- section_title
- embedding_id

### Table user_learning_profile
- user_id
- preferred_pedagogy
- logical_score
- procedural_score
- narrative_score
- analogy_score
- average_score
- fragile_topics
- updated_at
