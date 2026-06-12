# ADDISCO OPS — Pitch Investisseur
### 5 slides · Format 15 minutes

---

## SLIDE 1 — LE PROBLÈME

**Titre :** La formation professionnelle mesure la conformité, pas la compétence.

---

**Chiffre d'accroche :**
> 70% des connaissances acquises en formation sont oubliées dans les 24 heures.
> *(Courbe d'Ebbinghaus — principe validé en sciences cognitives)*

**Le vrai problème :**
- Les entreprises forment avec des PDFs, des QCMs, des e-learnings statiques.
- L'évaluation mesure "a-t-il lu ?" — pas "sait-il faire ?".
- Résultat : un agent validé en formation peut être en échec face à une situation réelle.

**Ce qui manque :**
Un système qui s'adapte à ce que l'apprenant **ne maîtrise pas encore**.

---
---

## SLIDE 2 — LA SOLUTION

**Titre :** Un moteur pédagogique adaptatif sur vos documents métier.

---

**Pipeline en 5 étapes :**

```
Document métier (PDF, TXT)
        ↓
  Découpage sémantique (RAG)
        ↓
  Génération de question contextualisée
        ↓
  Correction IA + diagnostic d'erreur
        ↓
  Moteur de maîtrise adaptatif
```

**Ce que le moteur fait :**
- Génère 6 types de questions (définition, procédure, cas pratique, comparaison, exception, synthèse)
- Diagnostique le type d'erreur (oubli, confusion, imprécision, hors-sujet)
- Adapte la difficulté selon le niveau de maîtrise réel
- Planifie la révision avec espacements cognitifs (J+1 / J+3 / J+7)

**Ce que l'utilisateur voit :**
Une interface simple. Il importe son document. Il répond. Il progresse.

---
---

## SLIDE 3 — LA DÉMONSTRATION

**Titre :** Le système en production — démonstration live.

---

**Séquence de démo (3 minutes) :**

1. Import d'un document métier réel (procédure / réglementation)
2. Génération automatique d'une question contextualisée
3. Réponse de l'apprenant → correction IA avec explication
4. Dashboard de maîtrise : score, chunks fragiles, prochaine révision

**Ce qu'on montre :**
- La question est ancrée dans le document — pas générique.
- La correction explique *pourquoi*, pas juste le score.
- Le moteur sait quelles notions sont fragiles, lesquelles sont maîtrisées.

> *"Ce n'est pas ChatGPT. C'est un système pédagogique construit autour d'un document spécifique."*

---
---

## SLIDE 4 — LES CHIFFRES

**Titre :** Un système validé, en production, prêt à scaler.

---

**Chiffres techniques :**

| Indicateur | Valeur |
|------------|--------|
| Phases de développement | 20 |
| Tests automatisés | 262 / 262 OK |
| Score de robustesse (500 sessions simulées) | **93 / 100** |
| Crash rate | 0% |
| Fallback involontaire | 0% |
| Types de questions | 6 |
| Seuils moteur calibrés | 6 paramètres validés |

**Infrastructure :**
- Déployé sur Railway (production)
- Stack : Python · Streamlit · SQLite · OpenAI Embeddings · RAG
- Migration PostgreSQL planifiée dès 20 utilisateurs concurrents

**Ce que ça signifie :**
Le moteur tourne. Il ne s'effondre pas sous charge. Il est prêt pour les premiers clients réels.

---
---

*ADDISCO OPS · marcelino.guilhem@gmail.com*
