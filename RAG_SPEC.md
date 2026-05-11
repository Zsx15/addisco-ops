# Spécification RAG — Version Progressive

## 1. Objectif

Permettre à l’IA de répondre depuis les documents du projet plutôt qu’avec une mémoire générale.

## 2. Pipeline

```text
Document
↓
Extraction texte
↓
Nettoyage
↓
Découpage
↓
Embeddings
↓
Stockage vectoriel
↓
Recherche sémantique
↓
Contexte
↓
Question ou correction IA
```

## 3. Découpage

### V1
Découpage par paragraphes.

### V2
Découpage par titres et sous-titres.

### V3
Découpage intelligent :
- règle ;
- exception ;
- condition ;
- procédure ;
- exemple.

## 4. Métadonnées chunk

Chaque chunk doit stocker :
- document_id ;
- chunk_id ;
- texte ;
- titre section ;
- index ;
- source ;
- date ingestion.

## 5. Recherche

Commencer simple :
- top_k = 3 à 5 chunks ;
- recherche vectorielle ;
- injection dans prompt.

Évolution :
- recherche hybride ;
- BM25 ;
- re-ranking.

## 6. Règles de réponse

L’IA doit :
- répondre uniquement avec le contexte fourni si demandé ;
- signaler si le contexte est insuffisant ;
- éviter d’inventer ;
- citer le passage ou la section utilisée si possible.

## 7. Prompt RAG type

```text
Tu réponds uniquement à partir du contexte fourni.

Contexte :
{retrieved_chunks}

Question :
{question}

Réponds clairement.
Si le contexte ne permet pas de répondre, dis-le.
```
