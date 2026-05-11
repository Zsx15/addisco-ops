# Premier prompt à donner à Claude Code

Copie-colle ce prompt dans Claude Code après avoir placé tous les fichiers du pack à la racine du projet.

```text
Tu es mon assistant développeur senior pour ce projet.

Lis d’abord les fichiers :
- CLAUDE.md
- README.md
- ROADMAP.md
- ARCHITECTURE.md
- TASKS.md
- ADAPTIVE_LEARNING_SPEC.md
- RAG_SPEC.md
- SECURITY_AND_LIMITS.md
- DATABASE_SCHEMA.md

Important :
- ne modifie aucun fichier pour l’instant ;
- ne crée aucun fichier ;
- ne lance aucun refactor.

Analyse le projet actuel et donne-moi :
1. l’architecture détectée ;
2. les fonctionnalités déjà présentes ;
3. les fichiers importants ;
4. les dépendances ;
5. les écarts par rapport à la roadmap ;
6. les risques techniques ;
7. la prochaine tâche prioritaire ;
8. un plan d’implémentation précis pour cette tâche ;
9. les fichiers qui seraient modifiés ;
10. les tests à effectuer ensuite.

Attends ma validation avant toute modification.
```
