# Sécurité, limites et règles éthiques

## 1. Secrets

Ne jamais écrire de clé API dans le code.

Utiliser :
- `.env`
- `.env.example`
- variables d’environnement.

## 2. Données personnelles

Ne stocker que les données nécessaires.
Prévoir à terme :
- suppression utilisateur ;
- export ;
- anonymisation ;
- limitation d’accès.

## 3. IA et pédagogie

Le système ne doit pas prétendre diagnostiquer :
- TDAH ;
- trouble cognitif ;
- pathologie ;
- niveau intellectuel.

Formulation autorisée :
- “Cette forme d’explication semble mieux fonctionner.”
- “L’utilisateur réussit davantage avec un format procédural.”

Formulation interdite :
- “L’utilisateur est dyslexique.”
- “L’utilisateur a une déficience de mémoire.”
- “L’utilisateur souffre de...”

## 4. Hallucinations

Pour les réponses basées sur documents :
- utiliser RAG ;
- citer le contexte ;
- signaler si l’information manque.

## 5. Production entreprise

Avant industrialisation :
- validation DSI ;
- sécurité ;
- conformité RGPD ;
- hébergement validé ;
- logs ;
- droits utilisateurs ;
- sauvegardes.
