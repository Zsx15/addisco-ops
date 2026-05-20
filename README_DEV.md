# README_DEV — Développement, test et outils internes

Ce fichier documente les comptes de développement, l'arborescence des outils internes, et les règles de gouvernance.
**Ne jamais versionner de mots de passe réels en production.**

---

## Arborescence tools/

```
tools/
├── admin/          — Gouvernance des comptes administrateurs (CLI uniquement)
│   ├── create_admin.py
│   ├── reset_password.py
│   └── README.md
├── qa/             — Tests de robustesse pédagogique
│   ├── test_robustesse_100q.py
│   └── README.md
└── observability/  — Audit et analyse read-only
    ├── audit_skills_empirique.py
    └── README.md
```

**Séparation runtime / tooling :**
- `app.py`, `database.py`, `ai_service.py`, `auth_service.py` : runtime applicatif — ne pas modifier sans validation
- `tools/` : scripts CLI internes uniquement — jamais importés par le runtime

---

## Comptes en base (database.db locale)

| Username    | Rôle       | Mot de passe  | Usage                              |
|-------------|------------|---------------|------------------------------------|
| `admin`     | admin      | `admin123`    | Compte admin principal — démo      |
| `G`         | admin      | `ggg`         | Compte admin secondaire            |
| `formateur` | formateur  | (non testé)   | Compte formateur de test           |
| `test`      | apprenant  | `test123`     | Compte apprenant de test           |
| `Guilhem`   | apprenant  | (non testé)   | Compte apprenant nominal           |
| `Romain`    | apprenant  | (non testé)   | Compte apprenant de test           |

---

## Commandes d'usage

### Admin

```bash
# Créer un compte admin
python tools/admin/create_admin.py --username <nom> --password <mdp>

# Réinitialiser un mot de passe
python tools/admin/reset_password.py --username <nom> --new-password <mdp>
```

### QA

```bash
# Test robustesse 100 questions — mode rapide (0 API, < 5 s)
python tools/qa/test_robustesse_100q.py --mock --no-confirm

# Mode corpus complet
python tools/qa/test_robustesse_100q.py --mock --scope corpus --n 300 --no-confirm

# Nettoyage données test
python tools/qa/test_robustesse_100q.py --cleanup
```

### Observability

```bash
# Audit empirique des skills
python tools/observability/audit_skills_empirique.py --username test
```

---

## Outils CLI admin

### Créer un compte admin

```bash
python tools/admin/create_admin.py --username <nom> --password <mdp>
```

- Crée un compte avec `role='admin'`.
- Erreur si le compte existe déjà (protection contre l'écrasement).
- Option `--db <chemin>` pour cibler une base différente (tests, staging).

### Réinitialiser un mot de passe

```bash
python tools/admin/reset_password.py --username <nom> --new-password <mdp>
```

- UPDATE ciblé — préserve `user_id`, `role`, `created_at`, et toutes les données liées.
- Vérifie le nouveau hash bcrypt immédiatement après la mise à jour.

### Vérifier l'existence d'un admin (code)

```python
from db.admin import admin_exists
print(admin_exists())  # True si au moins un admin en base
```

---

## Règles de gouvernance admin

- La création admin est **CLI uniquement** — jamais dans l'UI publique.
- L'inscription publique via `app.py` est limitée au rôle `apprenant`.
- La promotion de rôle passe par `auth_service.promote_user()`, appelée uniquement par un admin authentifié.
- Aucune suppression de compte sans validation explicite.

---

## Vérification rapide de santé

```bash
python -c "
import database; database.init_db()
from db.admin import admin_exists, count_admins
print('Admins en base:', count_admins())
print('Au moins un admin:', admin_exists())
"
```
