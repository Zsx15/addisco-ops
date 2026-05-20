# tools/observability — Audit et observabilité

Scripts d'analyse read-only du système. Aucune écriture SQL. Exécuter depuis la racine du projet.

## Scripts disponibles

### audit_skills_empirique.py

Analyse empirique des skills : couverture, mastery, discrimination, patterns émergents.

```bash
python tools/observability/audit_skills_empirique.py --username test
python tools/observability/audit_skills_empirique.py --username Guilhem
```

**Mode :** read-only strict — aucune écriture SQL, aucun appel API, aucun remap.

**Sections du rapport :**
1. Skills vivants (avec tentatives)
2. Skills morts (aucune détection ou tentative)
3. Skills discriminants (delta mastery significatif)
4. Skills polluants (couverture trop large)
5. Patterns émergents (co-occurrences, étroits, concentration doc)
6. Tableau récapitulatif
7. Verdict par skill : `KEEP` | `WATCH` | `REFINE` | `REMOVE/REWORK`
