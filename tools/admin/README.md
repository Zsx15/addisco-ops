# tools/admin — Gouvernance des comptes administrateurs

Scripts CLI de gestion admin. Jamais exposés dans l'UI publique. Exécuter depuis la racine du projet.

## Scripts disponibles

### create_admin.py

Crée un compte avec `role='admin'`. Erreur si le compte existe déjà.

```bash
python tools/admin/create_admin.py --username <nom> --password <mdp>

# Cibler une base spécifique (tests, staging)
python tools/admin/create_admin.py --username newadmin --password securepass --db /path/to/db
```

### reset_password.py

Réinitialise le mot de passe d'un utilisateur existant (UPDATE ciblé — jamais DELETE+INSERT).

```bash
python tools/admin/reset_password.py --username <nom> --new-password <mdp>

# Récupérer le compte G (mdp inconnu)
python tools/admin/reset_password.py --username G --new-password <nouveau_mdp>
```

## Vérification rapide

```bash
python -c "
import database; database.init_db()
from db.admin import admin_exists, count_admins
print('Admins en base:', count_admins())
print('Au moins un admin:', admin_exists())
"
```

## Règles

- Création admin : CLI uniquement.
- Inscription publique (`app.py`) : limitée à `apprenant`.
- Promotion de rôle : via `auth_service.promote_user()`, admin authentifié uniquement.
- Aucune suppression sans validation explicite.
