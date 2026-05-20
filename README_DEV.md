# README_DEV — Comptes de développement et test

Ce fichier documente les comptes créés pour le développement, les tests locaux, et la démonstration.
**Ne jamais versionner de mots de passe réels en production.**

---

## Comptes en base (database.db locale)

| Username    | Rôle       | Mot de passe  | Usage                              |
|-------------|------------|---------------|------------------------------------|
| `admin`     | admin      | `admin123`    | Compte admin principal — démo      |
| `G`         | admin      | inconnu       | Ancien compte admin — mdp perdu    |
| `formateur` | formateur  | (non testé)   | Compte formateur de test           |
| `test`      | apprenant  | `test123`     | Compte apprenant de test           |
| `Guilhem`   | apprenant  | (non testé)   | Compte apprenant nominal           |
| `Romain`    | apprenant  | (non testé)   | Compte apprenant de test           |

> Pour réinitialiser le mdp du compte `G` :
> ```
> python tools/admin/reset_password.py --username G --new-password <nouveau_mdp>
> ```

---

## Outils CLI admin

Ces scripts sont dans `tools/admin/` et ne sont jamais exposés dans l'UI publique.

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
- Fonctionne pour tout rôle (admin, formateur, apprenant).

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
