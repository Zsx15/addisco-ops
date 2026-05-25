# tools/admin — Gouvernance des comptes administrateurs

Scripts CLI de gestion admin. Jamais exposés dans l'UI publique. Exécuter depuis la racine du projet.

## Scripts disponibles

### create_or_promote_user.py ⭐ script principal

Crée ou met à jour un utilisateur. **Remplace create_admin.py pour tous les nouveaux usages.**

```bash
# Créer un admin
python tools/admin/create_or_promote_user.py --username admin --password "xxx" --role admin

# Créer un formateur
python tools/admin/create_or_promote_user.py --username formateur --password "xxx" --role formateur

# Promouvoir un utilisateur existant (sans changer le mdp)
python tools/admin/create_or_promote_user.py --username alice --role admin

# Changer rôle + mot de passe en une commande
python tools/admin/create_or_promote_user.py --username alice --role formateur --password "nouveau"

# Cibler la DB Railway ou staging
python tools/admin/create_or_promote_user.py --username admin --role admin --password "xxx" --db /app/data/database.db
```

**Comportement :**
- Absent → crée (--password obligatoire)
- Présent → met à jour le rôle et/ou le mot de passe si fourni
- Idempotent : aucun changement si déjà dans l'état cible
- Vérification bcrypt immédiate après chaque modification
- Le mot de passe n'est jamais affiché en clair

**Rôles autorisés :** `admin`, `formateur`, `apprenant`

---

### create_admin.py

Crée un compte avec `role='admin'`. Erreur si le compte existe déjà.

```bash
python tools/admin/create_admin.py --username <nom> --password <mdp>
python tools/admin/create_admin.py --username newadmin --password securepass --db /path/to/db
```

### reset_password.py

Réinitialise le mot de passe d'un utilisateur existant (UPDATE ciblé — jamais DELETE+INSERT).

```bash
python tools/admin/reset_password.py --username <nom> --new-password <mdp>
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

## Usage Railway (via CLI Railway)

```bash
railway run python tools/admin/create_or_promote_user.py --username admin --password "xxx" --role admin
```

## Règles

- Création/promotion admin : CLI uniquement.
- Inscription publique (`app.py`) : limitée à `apprenant`.
- Promotion de rôle via UI : `auth_service.promote_user()`, admin authentifié uniquement.
- Aucune suppression sans validation explicite.
