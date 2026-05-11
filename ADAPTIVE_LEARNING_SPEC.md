# Spécification — Couche d’Apprentissage Adaptatif

## 1. Objectif

Créer une couche capable d’adapter la pédagogie en fonction des résultats observés.

Important :
Le système ne fait aucun diagnostic médical.
Il mesure uniquement l’efficacité pédagogique.

## 2. Données à observer

Pour chaque tentative :
- score ;
- type d’erreur ;
- notion ;
- temps de réponse ;
- mode pédagogique utilisé ;
- réussite après reformulation ;
- nombre d’échecs sur la notion.

## 3. Modes pédagogiques

### Logique
Structure :
- règle ;
- condition ;
- exception ;
- conséquence.

### Procédural
Structure :
- étape 1 ;
- étape 2 ;
- étape 3 ;
- checklist.

### Narratif
Structure :
- mise en situation ;
- contexte ;
- action ;
- conséquence.

### Analogique
Structure :
- comparaison ;
- métaphore ;
- transposition.

### Synthétique
Structure :
- résumé court ;
- points clés ;
- rappel essentiel.

## 4. Règles heuristiques initiales

### Règle 1
Si l’utilisateur échoue deux fois sur la même notion :
- ne pas répéter la même explication ;
- changer de mode pédagogique.

### Règle 2
Si l’erreur est un oubli d’étape :
- utiliser mode procédural.

### Règle 3
Si l’erreur est une confusion conceptuelle :
- utiliser mode logique.

### Règle 4
Si l’utilisateur réussit après une analogie :
- augmenter le score du mode analogique.

### Règle 5
Si le temps de réponse est très long avec score faible :
- réduire la taille des explications ;
- découper en petites étapes.

## 5. Profil dynamique utilisateur

Exemple :

```json
{
  "logical_efficiency": 0.72,
  "procedural_efficiency": 0.58,
  "narrative_efficiency": 0.64,
  "analogy_efficiency": 0.81,
  "preferred_mode": "analogique",
  "fragile_topics": ["procédure d’alerte", "ordre des priorités"]
}
```

## 6. Sortie attendue du moteur

Le moteur doit retourner :
- mode pédagogique recommandé ;
- raison du choix ;
- niveau de détail recommandé ;
- type de prochaine question.

Exemple :

```json
{
  "recommended_pedagogy": "procedural",
  "reason": "L’utilisateur oublie régulièrement une étape dans cette procédure.",
  "detail_level": "short",
  "next_question_type": "mise_en_application"
}
```
