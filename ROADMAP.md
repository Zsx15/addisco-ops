# ROADMAP — Projet IA Révision / RAG / Adaptatif

## Phase 0 — Point de départ

Objectif : obtenir un prototype simple qui fonctionne.

Livrables :
- app Streamlit fonctionnelle ;
- génération de question ;
- correction IA ;
- score ;
- historique SQLite.

Critère de réussite :
- l’utilisateur peut coller un texte, répondre à une question et voir une correction enregistrée.

---

## Phase 1 — Stabilisation du prototype

Objectif : rendre le code propre et maintenable.

Tâches :
- créer `database.py` ;
- créer `ai_service.py` ;
- créer `utils.py` ;
- isoler la logique IA ;
- isoler la logique base de données ;
- ajouter `requirements.txt` ;
- ajouter `.env.example` ;
- améliorer README.

Critère de réussite :
- `app.py` devient plus lisible ;
- les fonctions principales sont séparées ;
- l’application se lance sans erreur.

---

## Phase 2 — Historique enrichi

Objectif : rendre les données exploitables.

Ajouter aux tentatives :
- question ;
- réponse utilisateur ;
- correction ;
- score ;
- date ;
- notion ;
- type d’erreur ;
- temps de réponse ;
- mode pédagogique utilisé.

Critère de réussite :
- l’historique permet de repérer les erreurs fréquentes.

---

## Phase 3 — Analyse des erreurs

Objectif : passer de “score” à “diagnostic pédagogique léger”.

Types d’erreurs :
- oubli d’étape ;
- confusion de notion ;
- réponse trop vague ;
- erreur d’ordre ;
- erreur d’exception ;
- mauvaise priorité ;
- réponse hors sujet.

Critère de réussite :
- chaque correction stocke un type d’erreur exploitable.

---

## Phase 4 — Import documentaire

Objectif : ne plus dépendre uniquement du copier-coller.

Fonctions :
- importer PDF ;
- importer DOCX ;
- extraire texte ;
- nettoyer texte ;
- stocker document en base.

Critère de réussite :
- un document importé peut servir de source aux questions.

---

## Phase 5 — Découpage documentaire

Objectif : préparer le RAG.

Découpage :
- par titre ;
- par paragraphe ;
- par section logique ;
- par procédure ;
- par règles / exceptions.

Critère de réussite :
- le document est découpé en chunks propres et réutilisables.

---

## Phase 6 — Embeddings et base vectorielle

Objectif : ajouter la recherche sémantique.

Fonctions :
- créer embeddings ;
- stocker chunks + vecteurs ;
- rechercher les passages proches d’une question.

Base vectorielle possible :
- Qdrant local ;
- Chroma pour prototype ;
- Milvus pour version avancée.

Critère de réussite :
- une question retrouve les passages pertinents du document.

---

## Phase 7 — RAG complet

Objectif : générer questions et corrections depuis les passages retrouvés.

Pipeline :
1. question ou objectif ;
2. recherche sémantique ;
3. récupération des chunks ;
4. génération de réponse contextualisée ;
5. correction avec source.

Critère de réussite :
- la réponse IA est ancrée dans le document.

---

## Phase 8 — Apprentissage adaptatif

Objectif : adapter la pédagogie selon les résultats.

Données observées :
- scores ;
- erreurs ;
- temps de réponse ;
- réussite après reformulation ;
- mode pédagogique utilisé.

Modes pédagogiques :
- logique ;
- procédural ;
- narratif ;
- analogique ;
- synthétique ;
- schématique.

Critère de réussite :
- le système change de forme d’explication si l’utilisateur bloque.

---

## Phase 9 — Répétition espacée

Objectif : mieux mémoriser.

Fonctions :
- détecter notion fragile ;
- programmer révision ;
- prioriser les erreurs récurrentes ;
- espacer les rappels selon la réussite.

Critère de réussite :
- l’utilisateur révise davantage ce qu’il oublie.

---

## Phase 10 — Industrialisation

Objectif : préparer une version entreprise.

Fonctions :
- authentification ;
- multi-utilisateur ;
- dashboard formateur ;
- exports ;
- logs ;
- sécurité ;
- Docker ;
- tests automatisés ;
- monitoring.

Critère de réussite :
- le projet peut être présenté comme base industrielle.
