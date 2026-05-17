\# PRD — AI Révision Métier



\## Description produit



AI Révision Métier est une application IA permettant :

\- l’import de documents métier ;

\- la génération de questions ;

\- la correction IA ;

\- le suivi des erreurs ;

\- et l’évolution vers un moteur pédagogique adaptatif.



Le système repose sur un pipeline RAG avec embeddings sémantiques.



\---



\# Fonctionnalités actuelles



\## Import documentaire



Formats supportés :

\- TXT

\- PDF



Fonctions :

\- extraction texte ;

\- prévisualisation ;

\- stockage SQLite.



\---



\## Chunking



Les documents sont automatiquement découpés en chunks textuels afin de :

\- limiter les tokens ;

\- améliorer la recherche sémantique ;

\- préparer le RAG.



\---



\## Embeddings



Chaque chunk reçoit un embedding sémantique via :

\- OpenAI text-embedding-3-small.



Les embeddings sont stockés dans SQLite sous forme binaire (BLOB float32).



\---



\## Retrieval sémantique



Lors de la génération :

1\. une requête embedding est créée ;

2\. les chunks proches sont recherchés ;

3\. top-k résultats retournés ;

4\. contexte envoyé au LLM.



\---



\## Génération de questions



Le système peut :

\- générer des questions métier ;

\- contextualisées ;

\- basées sur les chunks pertinents.



Fallback :

si retrieval indisponible → texte brut.



\---



\## Correction IA



Le système :

\- analyse la réponse ;

\- attribue un score ;

\- génère une explication ;

\- stocke l’historique.



\---



\## Historique



Chaque tentative stocke :

\- question ;

\- réponse ;

\- correction ;

\- score ;

\- timestamp.



\---



\## Dashboard



Le dashboard permet :

\- suivi des scores ;

\- historique ;

\- visualisation de progression.



\---



\## Réindexation



Les documents peuvent être réindexés.



Le système :

\- détecte les chunks sans embedding ;

\- génère uniquement les embeddings manquants ;

\- effectue uniquement des UPDATE SQL ;

\- conserve les IDs stables.



\---



\# Architecture actuelle



\## Base de données



SQLite :

\- documents

\- chunks

\- attempts



\---



\## Services principaux



\### app.py

UI Streamlit.



\### ai\_service.py

LLM + embeddings + génération.



\### document\_service.py

Import + chunking + réindexation.



\### database.py

Accès SQL.



\---



\# Contraintes techniques



Le projet doit :

\- rester modulaire ;

\- éviter les dépendances inutiles ;

\- préserver le fallback ;

\- éviter les régressions ;

\- supporter une montée en charge progressive.



\---



\# Fonctionnalités futures prioritaires



\## attempts.chunk\_id



Objectif :

lier chaque tentative au chunk source utilisé.



Permettra :

\- mémoire pédagogique ;

\- suivi des notions faibles ;

\- révision ciblée.



\---



\## Mémoire des erreurs



Stocker :

\- erreurs fréquentes ;

\- chunks difficiles ;

\- notions fragiles ;

\- stabilité mémoire.



\---



\## Répétition espacée



Adapter les révisions selon :

\- score ;

\- temps ;

\- fréquence erreurs ;

\- stabilité mémoire.



\---



\## Adaptation pédagogique



Adapter :

\- difficulté ;

\- reformulation ;

\- style de question ;

\- niveau d’explication.



\---



\## Embeddings pédagogiques



Créer des embeddings spécifiques aux :

\- erreurs ;

\- reformulations ;

\- profils d’apprentissage.



\---



\## Vector Database future



Si besoin futur :

\- Qdrant ;

\- Milvus ;

\- PGVector.



Non prioritaire actuellement.



\---



\# Priorités produit



\## Priorité absolue actuelle



Stabiliser :

\- pipeline RAG ;

\- tracking pédagogique ;

\- structure projet ;

\- gouvernance.



\---



\# Philosophie produit



Le système doit :

\- rester compréhensible ;

\- évoluer progressivement ;

\- conserver une forte explicabilité ;

\- privilégier robustesse avant complexité.

