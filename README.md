# Projet IA Révision Métier — Prototype vers RAG Adaptatif

## Objectif

Application IA permettant de transformer des documents métier en entraînement actif :
- questions ;
- corrections ;
- scoring ;
- historique ;
- analyse des erreurs ;
- adaptation pédagogique future.

## Lancement local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Variables d’environnement

Créer un fichier `.env` :

```env
OPENAI_API_KEY=ta_cle_api
```

## Architecture initiale recommandée

```text
app.py
database.py
ai_service.py
adaptive_engine.py
document_service.py
rag_service.py
requirements.txt
.env.example
README.md
CLAUDE.md
ROADMAP.md
TASKS.md
ARCHITECTURE.md
```

## Philosophie

Le projet doit avancer par petites étapes testables.
Chaque étape doit améliorer le produit sans casser l’existant.
